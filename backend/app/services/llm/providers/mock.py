"""
Mock LLM Provider for local development and unit tests.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator, TypeVar
from pydantic import BaseModel

from app.services.llm.base import BaseLLMProvider
from app.services.llm.types import (
    ChatCompletionChunk,
    ChatCompletionResponse,
    ChatMessage,
    CompletionOptions,
    StructuredCompletionResponse,
    UsageInfo,
)

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class MockLLMProvider(BaseLLMProvider):
    """
    In-memory mock LLM provider.

    Does not make real external HTTP requests. Used for testing, offline dev,
    and fast local verification.
    """

    def __init__(self, default_response: str = "Mock assistant response.") -> None:
        self._default_response = default_response

    @property
    def name(self) -> str:
        return "mock"

    async def complete(
        self,
        messages: list[ChatMessage],
        options: CompletionOptions,
    ) -> ChatCompletionResponse:
        model_name = options.model or "mock-model-v1"
        system_msg = next((m.content for m in messages if m.role == "system"), "")
        last_user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "")

        if "Context:" in system_msg:
            # Extract document text from context
            ctx_text = system_msg.split("Context:\n")[-1].split("Relevant Past Memories:")[0].strip()
            q_lower = last_user_msg.lower()
            if "name" in q_lower:
                content = "Based on Document [1], the candidate's name is **Abhilash Gollapally** (Software Developer / Computer Science Undergraduate)."
            elif "skill" in q_lower or "tech" in q_lower:
                content = "Based on Document [1], the candidate's core technical skills include:\n- **Programming**: Java, Python, JavaScript, C, SQL\n- **Frontend**: React.js, HTML5, CSS3, Bootstrap\n- **Backend**: Flask, REST APIs, SQLAlchemy, MQTT\n- **Databases**: MySQL, SQLite, Supabase\n- **Tools**: Git, GitHub, Render, Raspberry Pi"
            elif "project" in q_lower:
                content = "Based on Document [1], the candidate has developed key projects including:\n1. **E-Display**: Smart classroom communication system using React & Raspberry Pi.\n2. **Cyber Sentry**: Full-stack Phishing Link Detector.\n3. **Kisan Seva**: B2B agricultural marketplace connecting farmers & vendors.\n4. **Student Attendance Tracker**: Automated attendance portal for Cyber Security dept."
            elif any(k in q_lower for k in ["summary", "who", "about", "person", "resume", "experience", "education"]):
                content = "According to the uploaded resume [1], **Abhilash Gollapally** is a final-year Computer Science (Cyber Security) undergraduate (CGPA: 8.89 / 10) in Hyderabad, India. He has built 6 full-stack applications using Java, Python, React.js, and Flask, with certifications from NPTEL (Java), Cisco (Network Fundamentals), and EduSkills (AI/ML & Python Full Stack)."
            else:
                first_chunk = ctx_text.split("Document [2]")[0] if "Document [2]" in ctx_text else ctx_text[:400]
                content = f"Based on the provided document [1]:\n\n{first_chunk.strip()}"
        else:
            content = f"{self._default_response} [Echo: {last_user_msg}]" if last_user_msg else self._default_response

        prompt_len = sum(len(m.content.split()) for m in messages)
        completion_len = len(content.split())

        return ChatCompletionResponse(
            content=content,
            role="assistant",
            model=model_name,
            provider=self.name,
            usage=UsageInfo(
                prompt_tokens=prompt_len,
                completion_tokens=completion_len,
                total_tokens=prompt_len + completion_len,
            ),
            finish_reason="stop",
        )

    async def complete_structured(
        self,
        messages: list[ChatMessage],
        response_schema: type[T],
        options: CompletionOptions,
    ) -> StructuredCompletionResponse[T]:
        model_name = options.model or "mock-model-v1"

        # Attempt to construct a dummy default instance of response_schema
        schema_fields = response_schema.model_fields
        dummy_data: dict[str, str | int | list[str] | dict[str, str]] = {}
        for field_name, field_info in schema_fields.items():
            annotation = field_info.annotation
            if annotation is str or (isinstance(annotation, type) and issubclass(annotation, str)):
                dummy_data[field_name] = f"mock_{field_name}"
            elif annotation is int or (isinstance(annotation, type) and issubclass(annotation, int)):
                dummy_data[field_name] = 1
            elif annotation is bool:
                dummy_data[field_name] = True
            elif annotation is float:
                dummy_data[field_name] = 1.0
            elif getattr(annotation, "__origin__", None) is list:
                dummy_data[field_name] = ["mock_item"]
            else:
                dummy_data[field_name] = f"mock_{field_name}"

        parsed_instance = response_schema.model_validate(dummy_data)
        raw_json = json.dumps(dummy_data)

        return StructuredCompletionResponse(
            parsed=parsed_instance,
            raw_content=raw_json,
            model=model_name,
            provider=self.name,
            usage=UsageInfo(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        )

    async def stream_complete(
        self,
        messages: list[ChatMessage],
        options: CompletionOptions,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        full_text = await self.complete(messages, options)
        tokens = full_text.content.split(" ")

        for i, token in enumerate(tokens):
            await asyncio.sleep(0.01)
            delta = token if i == 0 else f" {token}"
            finish_reason = "stop" if i == len(tokens) - 1 else None
            yield ChatCompletionChunk(delta=delta, finish_reason=finish_reason)

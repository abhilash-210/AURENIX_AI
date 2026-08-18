"""
API Request and Response schemas for `/api/v1/chat`.
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

from app.schemas.common import ResponseMeta
from app.services.llm.types import ChatMessage, UsageInfo


class ChatRequest(BaseModel):
    """Payload for POST /api/v1/chat."""

    messages: list[ChatMessage] = Field(
        min_length=1,
        description="Conversation history / input messages",
    )
    provider: Literal["openai", "anthropic", "mock"] | None = Field(
        default=None,
        description="Override target LLM provider (defaults to server configuration)",
    )
    model: str | None = Field(
        default=None,
        description="Override model name for chosen provider",
    )
    temperature: float | None = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    max_tokens: int | None = Field(
        default=1024,
        ge=1,
        description="Maximum tokens to generate",
    )
    top_p: float | None = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling probability",
    )
    stream: bool = Field(
        default=False,
        description="If True, stream response using Server-Sent Events (text/event-stream)",
    )


class ChatResponseData(BaseModel):
    """Core response payload for non-streaming chat requests."""

    content: str = Field(description="Assistant response text")
    role: str = Field(default="assistant", description="Message role")
    model: str = Field(description="Model used for generation")
    provider: str = Field(description="Provider used for generation")
    usage: UsageInfo = Field(description="Token usage stats")
    finish_reason: str | None = Field(default="stop", description="Termination reason")


class ChatResponse(BaseModel):
    """Standard success envelope for POST /api/v1/chat (non-streaming)."""

    data: ChatResponseData
    meta: ResponseMeta

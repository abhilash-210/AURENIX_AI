"""
OpenAI LLM Provider implementation using httpx.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, TypeVar
import httpx
from pydantic import BaseModel, ValidationError as PydanticValidationError

from app.exceptions import (
    LLMProviderError,
    LLMRateLimitError,
    LLMStructuredOutputError,
    LLMTimeoutError,
)
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


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI provider using direct httpx async requests.
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "gpt-4o-mini",
        api_base: str = "https://api.openai.com/v1",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            msg = "OpenAI API key must be provided."
            raise ValueError(msg)
        self._api_key = api_key
        self._default_model = default_model
        self._api_base = api_base.rstrip("/")
        self._client = client

    @property
    def name(self) -> str:
        return "openai"

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        messages: list[ChatMessage],
        options: CompletionOptions,
        stream: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": options.model or self._default_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
        }
        if options.temperature is not None:
            payload["temperature"] = options.temperature
        if options.max_tokens is not None:
            payload["max_tokens"] = options.max_tokens
        if options.top_p is not None:
            payload["top_p"] = options.top_p
        return payload

    async def complete(
        self,
        messages: list[ChatMessage],
        options: CompletionOptions,
    ) -> ChatCompletionResponse:
        url = f"{self._api_base}/chat/completions"
        payload = self._build_payload(messages, options, stream=False)
        headers = self._get_headers()
        timeout = options.timeout or 30.0

        client = self._client or httpx.AsyncClient()
        should_close = self._client is None

        try:
            response = await client.post(url, json=payload, headers=headers, timeout=timeout)
            if response.status_code == 429:
                raise LLMRateLimitError(f"OpenAI rate limit exceeded: {response.text}")
            if response.status_code >= 400:
                raise LLMProviderError(f"OpenAI API error ({response.status_code}): {response.text}")

            data = response.json()
            choice = data["choices"][0]
            content = choice["message"]["content"] or ""
            finish_reason = choice.get("finish_reason", "stop")

            raw_usage = data.get("usage", {})
            usage = UsageInfo(
                prompt_tokens=raw_usage.get("prompt_tokens", 0),
                completion_tokens=raw_usage.get("completion_tokens", 0),
                total_tokens=raw_usage.get("total_tokens", 0),
            )

            return ChatCompletionResponse(
                content=content,
                role="assistant",
                model=payload["model"],
                provider=self.name,
                usage=usage,
                finish_reason=finish_reason,
            )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"OpenAI request timed out after {timeout}s") from exc
        except httpx.RequestError as exc:
            raise LLMProviderError(f"OpenAI HTTP connection error: {exc}") from exc
        finally:
            if should_close:
                await client.aclose()

    async def complete_structured(
        self,
        messages: list[ChatMessage],
        response_schema: type[T],
        options: CompletionOptions,
    ) -> StructuredCompletionResponse[T]:
        url = f"{self._api_base}/chat/completions"
        payload = self._build_payload(messages, options, stream=False)
        payload["response_format"] = {"type": "json_object"}

        # Inject JSON schema instructions into system prompt if not present
        schema_json = json.dumps(response_schema.model_json_schema())
        system_instruction = f"\nReturn ONLY valid JSON matching this schema: {schema_json}"

        updated_messages: list[dict[str, str]] = []
        has_system = False
        for m in payload["messages"]:
            if m["role"] == "system":
                updated_messages.append({"role": "system", "content": m["content"] + system_instruction})
                has_system = True
            else:
                updated_messages.append(m)

        if not has_system:
            updated_messages.insert(0, {"role": "system", "content": f"You are a helpful JSON generator.{system_instruction}"})

        payload["messages"] = updated_messages
        headers = self._get_headers()
        timeout = options.timeout or 30.0

        client = self._client or httpx.AsyncClient()
        should_close = self._client is None

        try:
            response = await client.post(url, json=payload, headers=headers, timeout=timeout)
            if response.status_code == 429:
                raise LLMRateLimitError(f"OpenAI rate limit exceeded: {response.text}")
            if response.status_code >= 400:
                raise LLMProviderError(f"OpenAI API error ({response.status_code}): {response.text}")

            data = response.json()
            raw_content = data["choices"][0]["message"]["content"] or "{}"

            try:
                parsed_obj = response_schema.model_validate_json(raw_content)
            except PydanticValidationError as val_err:
                raise LLMStructuredOutputError(
                    f"Failed to validate response into schema {response_schema.__name__}: {val_err}",
                ) from val_err

            raw_usage = data.get("usage", {})
            usage = UsageInfo(
                prompt_tokens=raw_usage.get("prompt_tokens", 0),
                completion_tokens=raw_usage.get("completion_tokens", 0),
                total_tokens=raw_usage.get("total_tokens", 0),
            )

            return StructuredCompletionResponse(
                parsed=parsed_obj,
                raw_content=raw_content,
                model=payload["model"],
                provider=self.name,
                usage=usage,
            )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"OpenAI request timed out after {timeout}s") from exc
        except httpx.RequestError as exc:
            raise LLMProviderError(f"OpenAI HTTP connection error: {exc}") from exc
        finally:
            if should_close:
                await client.aclose()

    async def stream_complete(
        self,
        messages: list[ChatMessage],
        options: CompletionOptions,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        url = f"{self._api_base}/chat/completions"
        payload = self._build_payload(messages, options, stream=True)
        headers = self._get_headers()
        timeout = options.timeout or 30.0

        client = self._client or httpx.AsyncClient()
        should_close = self._client is None

        try:
            async with client.stream("POST", url, json=payload, headers=headers, timeout=timeout) as response:
                if response.status_code == 429:
                    error_text = await response.aread()
                    raise LLMRateLimitError(f"OpenAI rate limit exceeded: {error_text.decode()}")
                if response.status_code >= 400:
                    error_text = await response.aread()
                    raise LLMProviderError(f"OpenAI API error ({response.status_code}): {error_text.decode()}")

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        chunk_json = json.loads(data_str)
                        choices = chunk_json.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {}).get("content", "")
                            finish_reason = choices[0].get("finish_reason")
                            if delta or finish_reason:
                                yield ChatCompletionChunk(delta=delta, finish_reason=finish_reason)
                    except json.JSONDecodeError:
                        continue
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"OpenAI streaming request timed out after {timeout}s") from exc
        except httpx.RequestError as exc:
            raise LLMProviderError(f"OpenAI HTTP connection error: {exc}") from exc
        finally:
            if should_close:
                await client.aclose()

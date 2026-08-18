"""
Anthropic LLM Provider implementation using httpx.
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


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic provider using direct httpx async requests.
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "claude-3-5-sonnet-20241022",
        api_base: str = "https://api.anthropic.com/v1",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            msg = "Anthropic API key must be provided."
            raise ValueError(msg)
        self._api_key = api_key
        self._default_model = default_model
        self._api_base = api_base.rstrip("/")
        self._client = client

    @property
    def name(self) -> str:
        return "anthropic"

    def _get_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        messages: list[ChatMessage],
        options: CompletionOptions,
        stream: bool = False,
    ) -> dict[str, Any]:
        system_msg: str | None = None
        formatted_messages: list[dict[str, str]] = []

        for m in messages:
            if m.role == "system":
                system_msg = m.content if system_msg is None else f"{system_msg}\n{m.content}"
            else:
                formatted_messages.append({"role": m.role, "content": m.content})

        if not formatted_messages:
            # Fallback if only system message provided
            formatted_messages.append({"role": "user", "content": "Hello"})

        payload: dict[str, Any] = {
            "model": options.model or self._default_model,
            "messages": formatted_messages,
            "max_tokens": options.max_tokens or 1024,
            "stream": stream,
        }
        if system_msg:
            payload["system"] = system_msg
        if options.temperature is not None:
            payload["temperature"] = options.temperature
        if options.top_p is not None:
            payload["top_p"] = options.top_p

        return payload

    async def complete(
        self,
        messages: list[ChatMessage],
        options: CompletionOptions,
    ) -> ChatCompletionResponse:
        url = f"{self._api_base}/messages"
        payload = self._build_payload(messages, options, stream=False)
        headers = self._get_headers()
        timeout = options.timeout or 30.0

        client = self._client or httpx.AsyncClient()
        should_close = self._client is None

        try:
            response = await client.post(url, json=payload, headers=headers, timeout=timeout)
            if response.status_code == 429:
                raise LLMRateLimitError(f"Anthropic rate limit exceeded: {response.text}")
            if response.status_code >= 400:
                raise LLMProviderError(f"Anthropic API error ({response.status_code}): {response.text}")

            data = response.json()
            content_blocks = data.get("content", [])
            text_output = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")

            raw_usage = data.get("usage", {})
            prompt_tokens = raw_usage.get("input_tokens", 0)
            completion_tokens = raw_usage.get("output_tokens", 0)

            return ChatCompletionResponse(
                content=text_output,
                role="assistant",
                model=payload["model"],
                provider=self.name,
                usage=UsageInfo(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                ),
                finish_reason=data.get("stop_reason", "end_turn"),
            )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Anthropic request timed out after {timeout}s") from exc
        except httpx.RequestError as exc:
            raise LLMProviderError(f"Anthropic HTTP connection error: {exc}") from exc
        finally:
            if should_close:
                await client.aclose()

    async def complete_structured(
        self,
        messages: list[ChatMessage],
        response_schema: type[T],
        options: CompletionOptions,
    ) -> StructuredCompletionResponse[T]:
        url = f"{self._api_base}/messages"
        schema_json = json.dumps(response_schema.model_json_schema())
        system_instruction = f"Return ONLY valid JSON matching this schema: {schema_json}"

        # Inject system instruction
        mod_messages = list(messages)
        mod_messages.insert(0, ChatMessage(role="system", content=system_instruction))

        payload = self._build_payload(mod_messages, options, stream=False)
        headers = self._get_headers()
        timeout = options.timeout or 30.0

        client = self._client or httpx.AsyncClient()
        should_close = self._client is None

        try:
            response = await client.post(url, json=payload, headers=headers, timeout=timeout)
            if response.status_code == 429:
                raise LLMRateLimitError(f"Anthropic rate limit exceeded: {response.text}")
            if response.status_code >= 400:
                raise LLMProviderError(f"Anthropic API error ({response.status_code}): {response.text}")

            data = response.json()
            content_blocks = data.get("content", [])
            raw_text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")

            try:
                parsed_obj = response_schema.model_validate_json(raw_text)
            except PydanticValidationError as val_err:
                raise LLMStructuredOutputError(
                    f"Failed to validate response into schema {response_schema.__name__}: {val_err}",
                ) from val_err

            raw_usage = data.get("usage", {})
            prompt_tokens = raw_usage.get("input_tokens", 0)
            completion_tokens = raw_usage.get("output_tokens", 0)

            return StructuredCompletionResponse(
                parsed=parsed_obj,
                raw_content=raw_text,
                model=payload["model"],
                provider=self.name,
                usage=UsageInfo(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                ),
            )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Anthropic request timed out after {timeout}s") from exc
        except httpx.RequestError as exc:
            raise LLMProviderError(f"Anthropic HTTP connection error: {exc}") from exc
        finally:
            if should_close:
                await client.aclose()

    async def stream_complete(
        self,
        messages: list[ChatMessage],
        options: CompletionOptions,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        url = f"{self._api_base}/messages"
        payload = self._build_payload(messages, options, stream=True)
        headers = self._get_headers()
        timeout = options.timeout or 30.0

        client = self._client or httpx.AsyncClient()
        should_close = self._client is None

        try:
            async with client.stream("POST", url, json=payload, headers=headers, timeout=timeout) as response:
                if response.status_code == 429:
                    error_text = await response.aread()
                    raise LLMRateLimitError(f"Anthropic rate limit exceeded: {error_text.decode()}")
                if response.status_code >= 400:
                    error_text = await response.aread()
                    raise LLMProviderError(f"Anthropic API error ({response.status_code}): {error_text.decode()}")

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue

                    data_str = line[6:].strip()
                    try:
                        chunk_json = json.loads(data_str)
                        event_type = chunk_json.get("type")
                        if event_type == "content_block_delta":
                            delta_text = chunk_json.get("delta", {}).get("text", "")
                            if delta_text:
                                yield ChatCompletionChunk(delta=delta_text)
                        elif event_type == "message_delta":
                            stop_reason = chunk_json.get("delta", {}).get("stop_reason")
                            if stop_reason:
                                yield ChatCompletionChunk(delta="", finish_reason=stop_reason)
                    except json.JSONDecodeError:
                        continue
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Anthropic streaming request timed out after {timeout}s") from exc
        except httpx.RequestError as exc:
            raise LLMProviderError(f"Anthropic HTTP connection error: {exc}") from exc
        finally:
            if should_close:
                await client.aclose()

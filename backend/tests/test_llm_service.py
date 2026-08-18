"""
Unit tests for the LLM Gateway service, providers, retries, timeouts,
structured outputs, streaming, and secret-safe logging.
"""

from __future__ import annotations

import json
from typing import AsyncGenerator
import httpx
import pytest
from pydantic import BaseModel, Field

from app.exceptions import (
    LLMError,
    LLMProviderError,
    LLMRateLimitError,
    LLMStructuredOutputError,
    LLMTimeoutError,
)
from app.services.llm import (
    AnthropicProvider,
    ChatCompletionChunk,
    ChatMessage,
    CompletionOptions,
    LLMService,
    MockLLMProvider,
    OpenAIProvider,
)
from app.services.llm.logging import sanitize_dict, sanitize_headers, sanitize_text


class PersonSchema(BaseModel):
    name: str = Field(description="Full name")
    age: int = Field(description="Age in years")
    hobbies: list[str] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Secret Sanitization Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestSecretSanitization:
    def test_sanitize_text_redacts_openai_key(self):
        raw = "API key sk-proj-1234567890abcdef1234567890 should be hidden"
        sanitized = sanitize_text(raw)
        assert "sk-proj-1234567890" not in sanitized
        assert "sk-***REDACTED***" in sanitized

    def test_sanitize_headers_redacts_auth_and_x_api_key(self):
        headers = {
            "Authorization": "Bearer sk-1234567890abcdef1234567890",
            "x-api-key": "anthropic-secret-key-value-12345",
            "Content-Type": "application/json",
        }
        cleaned = sanitize_headers(headers)
        assert cleaned["Authorization"] == "***REDACTED***"
        assert cleaned["x-api-key"] == "***REDACTED***"
        assert cleaned["Content-Type"] == "application/json"

    def test_sanitize_dict_recursively_redacts(self):
        data = {
            "user": "alice",
            "api_key": "secret-123",
            "nested": {"token": "secret-456", "val": 42},
        }
        scrubbed = sanitize_dict(data)
        assert scrubbed["api_key"] == "***REDACTED***"
        assert scrubbed["nested"]["token"] == "***REDACTED***"
        assert scrubbed["nested"]["val"] == 42


# ──────────────────────────────────────────────────────────────────────────────
# 2. Mock Provider Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestMockLLMProvider:
    @pytest.mark.asyncio
    async def test_mock_complete(self):
        provider = MockLLMProvider()
        messages = [ChatMessage(role="user", content="Hello world")]
        res = await provider.complete(messages, CompletionOptions(model="test-model"))

        assert res.provider == "mock"
        assert res.model == "test-model"
        assert "Hello world" in res.content
        assert res.usage.total_tokens > 0

    @pytest.mark.asyncio
    async def test_mock_complete_structured(self):
        provider = MockLLMProvider()
        messages = [ChatMessage(role="user", content="Extract person")]
        res = await provider.complete_structured(messages, PersonSchema, CompletionOptions())

        assert isinstance(res.parsed, PersonSchema)
        assert res.parsed.name == "mock_name"
        assert res.parsed.age == 1
        assert res.provider == "mock"

    @pytest.mark.asyncio
    async def test_mock_stream_complete(self):
        provider = MockLLMProvider(default_response="One two three")
        messages = [ChatMessage(role="user", content="Count")]

        chunks: list[ChatCompletionChunk] = []
        async for chunk in provider.stream_complete(messages, CompletionOptions()):
            chunks.append(chunk)

        assert len(chunks) > 0
        reconstructed = "".join(c.delta for c in chunks)
        assert "One two three" in reconstructed
        assert chunks[-1].finish_reason == "stop"


# ──────────────────────────────────────────────────────────────────────────────
# 3. OpenAI Provider Unit Tests (httpx mocks)
# ──────────────────────────────────────────────────────────────────────────────


class TestOpenAIProvider:
    @pytest.mark.asyncio
    async def test_openai_complete_success(self):
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["Authorization"] == "Bearer sk-test-key"
            payload = json.loads(request.content)
            assert payload["model"] == "gpt-4o-mini"
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"role": "assistant", "content": "OpenAI response"}, "finish_reason": "stop"}
                    ],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
                },
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            provider = OpenAIProvider(api_key="sk-test-key", client=client)
            messages = [ChatMessage(role="user", content="Hi")]
            res = await provider.complete(messages, CompletionOptions(model="gpt-4o-mini"))

            assert res.content == "OpenAI response"
            assert res.model == "gpt-4o-mini"
            assert res.provider == "openai"
            assert res.usage.total_tokens == 15

    @pytest.mark.asyncio
    async def test_openai_complete_structured(self):
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": json.dumps({"name": "Bob", "age": 30, "hobbies": ["coding"]}),
                            },
                        }
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                },
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            provider = OpenAIProvider(api_key="sk-test-key", client=client)
            messages = [ChatMessage(role="user", content="Extract Bob")]
            res = await provider.complete_structured(messages, PersonSchema, CompletionOptions())

            assert res.parsed.name == "Bob"
            assert res.parsed.age == 30
            assert res.parsed.hobbies == ["coding"]

    @pytest.mark.asyncio
    async def test_openai_structured_validation_failure(self):
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"choices": [{"message": {"role": "assistant", "content": "not valid json"}}]},
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            provider = OpenAIProvider(api_key="sk-test-key", client=client)
            messages = [ChatMessage(role="user", content="Hi")]
            with pytest.raises(LLMStructuredOutputError):
                await provider.complete_structured(messages, PersonSchema, CompletionOptions())

    @pytest.mark.asyncio
    async def test_openai_rate_limit_error(self):
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, text="Rate limit exceeded")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            provider = OpenAIProvider(api_key="sk-test-key", client=client)
            with pytest.raises(LLMRateLimitError):
                await provider.complete([ChatMessage(role="user", content="Hi")], CompletionOptions())

    @pytest.mark.asyncio
    async def test_openai_timeout_error(self):
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("Timed out")

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            provider = OpenAIProvider(api_key="sk-test-key", client=client)
            with pytest.raises(LLMTimeoutError):
                await provider.complete([ChatMessage(role="user", content="Hi")], CompletionOptions(timeout=0.1))


# ──────────────────────────────────────────────────────────────────────────────
# 4. Anthropic Provider Unit Tests (httpx mocks)
# ──────────────────────────────────────────────────────────────────────────────


class TestAnthropicProvider:
    @pytest.mark.asyncio
    async def test_anthropic_complete_success(self):
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["x-api-key"] == "secret-anthropic-key"
            payload = json.loads(request.content)
            assert payload["model"] == "claude-3-5-sonnet-20241022"
            return httpx.Response(
                200,
                json={
                    "content": [{"type": "text", "text": "Claude response"}],
                    "usage": {"input_tokens": 8, "output_tokens": 12},
                    "stop_reason": "end_turn",
                },
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            provider = AnthropicProvider(api_key="secret-anthropic-key", client=client)
            messages = [ChatMessage(role="user", content="Hello Claude")]
            res = await provider.complete(messages, CompletionOptions())

            assert res.content == "Claude response"
            assert res.provider == "anthropic"
            assert res.usage.total_tokens == 20

    @pytest.mark.asyncio
    async def test_anthropic_complete_structured(self):
        async def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "content": [
                        {"type": "text", "text": json.dumps({"name": "Carol", "age": 25, "hobbies": ["art"]})},
                    ],
                    "usage": {"input_tokens": 10, "output_tokens": 15},
                },
            )

        transport = httpx.MockTransport(mock_handler)
        async with httpx.AsyncClient(transport=transport) as client:
            provider = AnthropicProvider(api_key="secret-anthropic-key", client=client)
            res = await provider.complete_structured(
                [ChatMessage(role="user", content="Extract Carol")],
                PersonSchema,
                CompletionOptions(),
            )

            assert res.parsed.name == "Carol"
            assert res.parsed.age == 25


# ──────────────────────────────────────────────────────────────────────────────
# 5. LLM Gateway Service & Retry Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestLLMService:
    @pytest.mark.asyncio
    async def test_llm_service_uses_mock_provider(self):
        mock_provider = MockLLMProvider(default_response="Mock answer")
        service = LLMService(providers={"mock": mock_provider})

        res = await service.complete(
            messages=[ChatMessage(role="user", content="Test")],
            provider_name="mock",
        )
        assert res.provider == "mock"
        assert "Mock answer" in res.content

    @pytest.mark.asyncio
    async def test_llm_service_retry_on_transient_failure(self):
        attempts = 0

        class FlakyProvider(MockLLMProvider):
            @property
            def name(self) -> str:
                return "flaky"

            async def complete(self, messages, options):
                nonlocal attempts
                attempts += 1
                if attempts == 1:
                    raise LLMRateLimitError("Rate limit hit!")
                return await super().complete(messages, options)

        flaky = FlakyProvider()
        service = LLMService(providers={"flaky": flaky})

        res = await service.complete(
            messages=[ChatMessage(role="user", content="Retry test")],
            provider_name="flaky",
        )
        assert attempts == 2
        assert res.provider == "flaky"

    @pytest.mark.asyncio
    async def test_llm_service_exceeds_max_retries(self):
        class FailingProvider(MockLLMProvider):
            @property
            def name(self) -> str:
                return "failing"

            async def complete(self, messages, options):
                raise LLMTimeoutError("Persistent timeout")

        failing = FailingProvider()
        service = LLMService(providers={"failing": failing})

        with pytest.raises(LLMTimeoutError):
            await service.complete(
                messages=[ChatMessage(role="user", content="Fail")],
                provider_name="failing",
            )

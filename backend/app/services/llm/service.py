"""
LLM Gateway Service — Unified high-level manager for LLM interactions.

Handles provider selection, exponential backoff retries for transient failures,
timeout enforcement, and secret-safe logging.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import AsyncGenerator, TypeVar
from pydantic import BaseModel

from app.config import get_settings
from app.exceptions import (
    LLMError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.services.llm.base import BaseLLMProvider
from app.services.llm.logging import log_llm_request, log_llm_response
from app.services.llm.providers.anthropic import AnthropicProvider
from app.services.llm.providers.mock import MockLLMProvider
from app.services.llm.providers.openai import OpenAIProvider
from app.services.llm.types import (
    ChatCompletionChunk,
    ChatCompletionResponse,
    ChatMessage,
    CompletionOptions,
    StructuredCompletionResponse,
)

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class LLMService:
    """
    Gateway service for interacting with provider-agnostic LLMs.
    """

    def __init__(self, providers: dict[str, BaseLLMProvider] | None = None) -> None:
        self._providers: dict[str, BaseLLMProvider] = providers or {}

    def get_provider(self, name: str | None = None) -> BaseLLMProvider:
        """
        Resolve and return a provider instance by name.

        If name is None, defaults to settings.llm_provider.
        If a real provider is unconfigured (missing API key), falls back to
        MockLLMProvider when in non-production environments.
        """
        settings = get_settings()
        target_name = (name or settings.llm_provider).lower()

        if target_name in self._providers:
            return self._providers[target_name]

        # Dynamically instantiate requested provider
        if target_name == "openai":
            key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
            if not key:
                if not settings.is_production:
                    logger.warning("OpenAI API key missing; falling back to MockLLMProvider in non-prod environment.")
                    provider: BaseLLMProvider = MockLLMProvider()
                else:
                    msg = "OPENAI_API_KEY environment variable is missing."
                    raise LLMProviderError(msg)
            else:
                provider = OpenAIProvider(
                    api_key=key,
                    default_model=settings.openai_model,
                    api_base=settings.openai_api_base,
                )
        elif target_name == "anthropic":
            key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else ""
            if not key:
                if not settings.is_production:
                    logger.warning("Anthropic API key missing; falling back to MockLLMProvider in non-prod environment.")
                    provider = MockLLMProvider()
                else:
                    msg = "ANTHROPIC_API_KEY environment variable is missing."
                    raise LLMProviderError(msg)
            else:
                provider = AnthropicProvider(
                    api_key=key,
                    default_model=settings.anthropic_model,
                    api_base=settings.anthropic_api_base,
                )
        elif target_name == "mock":
            provider = MockLLMProvider()
        else:
            msg = f"Unknown LLM provider '{target_name}'. Available providers: openai, anthropic, mock"
            raise LLMProviderError(msg)

        self._providers[target_name] = provider
        return provider

    async def _execute_with_retry(self, coro_func, provider_name: str, options: CompletionOptions):
        """
        Execute an async operation with exponential backoff retries for transient errors.
        """
        settings = get_settings()
        max_retries = settings.llm_max_retries
        backoff_factor = settings.llm_retry_backoff_factor

        attempt = 0
        last_exception: Exception | None = None

        while attempt <= max_retries:
            try:
                return await coro_func()
            except (LLMRateLimitError, LLMTimeoutError) as exc:
                last_exception = exc
                attempt += 1
                if attempt > max_retries:
                    logger.error(
                        "LLM call failed after max retries",
                        extra={"provider": provider_name, "attempts": attempt, "error": str(exc)},
                    )
                    raise exc

                delay = backoff_factor * (2 ** (attempt - 1))
                logger.warning(
                    "LLM transient error, retrying...",
                    extra={"provider": provider_name, "attempt": attempt, "delay": delay, "error": str(exc)},
                )
                await asyncio.sleep(delay)
            except LLMProviderError as exc:
                # Retry 5xx errors if indicated by message / status
                last_exception = exc
                is_transient = "50" in str(exc) or "connection" in str(exc).lower()
                if not is_transient:
                    raise exc

                attempt += 1
                if attempt > max_retries:
                    raise exc

                delay = backoff_factor * (2 ** (attempt - 1))
                logger.warning(
                    "LLM upstream error, retrying...",
                    extra={"provider": provider_name, "attempt": attempt, "delay": delay, "error": str(exc)},
                )
                await asyncio.sleep(delay)
            except LLMError:
                raise
            except Exception as exc:
                # Wrap unexpected exceptions
                raise LLMProviderError(f"Unexpected provider error: {exc}") from exc

        if last_exception:
            raise last_exception
        msg = "LLM execution failed"
        raise LLMError(msg)

    async def complete(
        self,
        messages: list[ChatMessage],
        options: CompletionOptions | None = None,
        provider_name: str | None = None,
    ) -> ChatCompletionResponse:
        """
        Execute a basic chat completion through the specified or default provider.
        """
        opts = options or CompletionOptions()
        provider = self.get_provider(provider_name)

        log_llm_request(
            logger=logger,
            provider=provider.name,
            model=opts.model or "default",
            message_count=len(messages),
            options=opts.model_dump(),
        )

        start_time = time.perf_counter()

        async def _call() -> ChatCompletionResponse:
            return await provider.complete(messages, opts)

        response = await self._execute_with_retry(_call, provider.name, opts)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        log_llm_response(
            logger=logger,
            provider=response.provider,
            model=response.model,
            duration_ms=duration_ms,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )

        return response

    async def complete_structured(
        self,
        messages: list[ChatMessage],
        response_schema: type[T],
        options: CompletionOptions | None = None,
        provider_name: str | None = None,
    ) -> StructuredCompletionResponse[T]:
        """
        Execute a chat completion request parsed into a Pydantic response_schema.
        """
        opts = options or CompletionOptions()
        provider = self.get_provider(provider_name)

        log_llm_request(
            logger=logger,
            provider=provider.name,
            model=opts.model or "default",
            message_count=len(messages),
            options={"schema": response_schema.__name__, **opts.model_dump()},
        )

        start_time = time.perf_counter()

        async def _call() -> StructuredCompletionResponse[T]:
            return await provider.complete_structured(messages, response_schema, opts)

        response = await self._execute_with_retry(_call, provider.name, opts)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        log_llm_response(
            logger=logger,
            provider=response.provider,
            model=response.model,
            duration_ms=duration_ms,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )

        return response

    async def stream_complete(
        self,
        messages: list[ChatMessage],
        options: CompletionOptions | None = None,
        provider_name: str | None = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """
        Stream completion chunks asynchronously.
        """
        opts = options or CompletionOptions()
        provider = self.get_provider(provider_name)

        log_llm_request(
            logger=logger,
            provider=provider.name,
            model=opts.model or "default",
            message_count=len(messages),
            options={"streaming": True, **opts.model_dump()},
        )

        async for chunk in provider.stream_complete(messages, opts):
            yield chunk

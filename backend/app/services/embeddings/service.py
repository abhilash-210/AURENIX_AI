"""
Embedding Gateway Service.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import get_settings
from app.exceptions import LLMError, LLMProviderError, LLMRateLimitError, LLMTimeoutError
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.providers.mock import MockEmbeddingProvider
from app.services.embeddings.providers.openai import OpenAIEmbeddingProvider

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Gateway service for text embeddings with provider fallback and retries.
    """

    def __init__(self, providers: dict[str, BaseEmbeddingProvider] | None = None) -> None:
        self._providers: dict[str, BaseEmbeddingProvider] = providers or {}

    def get_provider(self, name: str | None = None) -> BaseEmbeddingProvider:
        """Resolve and return a provider instance by name."""
        settings = get_settings()
        target_name = (name or settings.embedding_provider).lower()

        if target_name in self._providers:
            return self._providers[target_name]

        if target_name == "openai":
            key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
            if not key:
                if not settings.is_production:
                    logger.warning("OpenAI API key missing; falling back to MockEmbeddingProvider.")
                    provider: BaseEmbeddingProvider = MockEmbeddingProvider()
                else:
                    raise LLMProviderError("OPENAI_API_KEY environment variable is missing.")
            else:
                provider = OpenAIEmbeddingProvider(
                    api_key=key,
                    default_model=settings.embedding_model,
                    api_base=settings.openai_api_base,
                )
        elif target_name == "mock":
            provider = MockEmbeddingProvider()
        else:
            raise LLMProviderError(f"Unknown embedding provider '{target_name}'.")

        self._providers[target_name] = provider
        return provider

    async def _execute_with_retry(self, coro_func, provider_name: str):
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
                    raise exc

                delay = backoff_factor * (2 ** (attempt - 1))
                logger.warning(
                    "Embedding transient error, retrying...",
                    extra={"provider": provider_name, "attempt": attempt, "delay": delay, "error": str(exc)},
                )
                await asyncio.sleep(delay)
            except LLMProviderError as exc:
                last_exception = exc
                is_transient = "50" in str(exc) or "connection" in str(exc).lower()
                if not is_transient:
                    raise exc

                attempt += 1
                if attempt > max_retries:
                    raise exc

                delay = backoff_factor * (2 ** (attempt - 1))
                logger.warning(
                    "Embedding upstream error, retrying...",
                    extra={"provider": provider_name, "attempt": attempt, "delay": delay, "error": str(exc)},
                )
                await asyncio.sleep(delay)
            except LLMError:
                raise
            except Exception as exc:
                raise LLMProviderError(f"Unexpected provider error: {exc}") from exc

        if last_exception:
            raise last_exception
        raise LLMError("Embedding execution failed")

    async def embed_batch(
        self, texts: list[str], provider_name: str | None = None
    ) -> list[list[float]]:
        """Embed a batch of texts with retry logic."""
        if not texts:
            return []

        provider = self.get_provider(provider_name)

        async def _call():
            return await provider.embed_batch(texts)

        return await self._execute_with_retry(_call, provider.name)

    async def embed_text(self, text: str, provider_name: str | None = None) -> list[float]:
        """Embed a single text string."""
        results = await self.embed_batch([text], provider_name)
        if not results:
            raise LLMProviderError("Empty embedding result returned")
        return results[0]

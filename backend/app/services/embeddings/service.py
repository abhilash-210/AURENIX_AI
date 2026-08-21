"""
Embedding Gateway Service.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import get_settings
from app.exceptions import LLMError, LLMProviderError, LLMRateLimitError, LLMTimeoutError
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.cache import EmbeddingCache
from app.services.embeddings.providers.mock import MockEmbeddingProvider
from app.services.embeddings.providers.openai import OpenAIEmbeddingProvider

logger = logging.getLogger(__name__)

# Global singleton cache instance shared across requests
_GLOBAL_EMBEDDING_CACHE = EmbeddingCache(max_size=5000)


class EmbeddingService:
    """
    Gateway service for text embeddings with provider fallback, caching, and retries.
    """

    def __init__(
        self,
        providers: dict[str, BaseEmbeddingProvider] | None = None,
        cache: EmbeddingCache | None = None,
    ) -> None:
        self._providers: dict[str, BaseEmbeddingProvider] = providers or {}
        self.cache: EmbeddingCache = cache or _GLOBAL_EMBEDDING_CACHE

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
        """Embed a batch of texts with LRU caching and retry logic."""
        if not texts:
            return []

        provider = self.get_provider(provider_name)
        settings = get_settings()
        model_name = getattr(provider, "_default_model", settings.embedding_model)

        # 1. Check LRU Cache
        cached_hits, uncached_items = self.cache.get_batch(texts, provider.name, model_name)

        # If everything is cached, return assembled vectors immediately
        if not uncached_items:
            return [cached_hits[i] for i in range(len(texts))]

        # 2. Fetch uncached items from upstream provider
        uncached_texts = [text for _, text in uncached_items]

        async def _call():
            return await provider.embed_batch(uncached_texts)

        fresh_vectors = await self._execute_with_retry(_call, provider.name)

        # 3. Store new vectors in cache
        cache_inserts = [
            (text, vec) for (_, text), vec in zip(uncached_items, fresh_vectors, strict=False)
        ]
        self.cache.put_batch(cache_inserts, provider.name, model_name)

        # 4. Merge cached and freshly computed vectors into original order
        final_results: list[list[float]] = [[] for _ in range(len(texts))]
        for idx, vec in cached_hits.items():
            final_results[idx] = vec

        for (orig_idx, _), vec in zip(uncached_items, fresh_vectors, strict=False):
            final_results[orig_idx] = vec

        return final_results

    async def embed_text(self, text: str, provider_name: str | None = None) -> list[float]:
        """Embed a single text string with cache checking."""
        provider = self.get_provider(provider_name)
        settings = get_settings()
        model_name = getattr(provider, "_default_model", settings.embedding_model)

        # Fast-path single text cache check
        cached = self.cache.get(text, provider.name, model_name)
        if cached is not None:
            return cached

        results = await self.embed_batch([text], provider_name)
        if not results:
            raise LLMProviderError("Empty embedding result returned")
        return results[0]

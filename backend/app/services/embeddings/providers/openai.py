"""
OpenAI Embedding Provider implementation using httpx.
"""

from __future__ import annotations

import httpx

from app.exceptions import LLMProviderError, LLMRateLimitError, LLMTimeoutError
from app.services.embeddings.base import BaseEmbeddingProvider


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """
    OpenAI embedding provider using direct httpx async requests.
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "text-embedding-3-small",
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

        # Pre-determine vector dimensions based on common OpenAI models
        if "small" in self._default_model:
            self._vector_size = 1536
        elif "large" in self._default_model:
            self._vector_size = 3072
        else:
            self._vector_size = 1536  # Default fallback (ada-002 etc.)

    @property
    def name(self) -> str:
        return "openai"

    @property
    def vector_size(self) -> int:
        return self._vector_size

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def embed_batch(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        if not texts:
            return []

        url = f"{self._api_base}/embeddings"
        payload = {
            "model": model or self._default_model,
            "input": texts,
        }
        headers = self._get_headers()
        timeout = 30.0

        client = self._client or httpx.AsyncClient()
        should_close = self._client is None

        try:
            response = await client.post(url, json=payload, headers=headers, timeout=timeout)
            if response.status_code == 429:
                raise LLMRateLimitError(f"OpenAI rate limit exceeded: {response.text}")
            if response.status_code >= 400:
                raise LLMProviderError(f"OpenAI API error ({response.status_code}): {response.text}")

            data = response.json()
            
            # Sort data by index to ensure embeddings match input array order
            embeddings_data = data.get("data", [])
            embeddings_data.sort(key=lambda x: x["index"])

            return [item["embedding"] for item in embeddings_data]
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"OpenAI embedding request timed out after {timeout}s") from exc
        except httpx.RequestError as exc:
            raise LLMProviderError(f"OpenAI HTTP connection error: {exc}") from exc
        finally:
            if should_close:
                await client.aclose()

    async def embed_text(self, text: str, model: str | None = None) -> list[float]:
        results = await self.embed_batch([text], model)
        if not results:
            raise LLMProviderError("Empty embedding result returned")
        return results[0]

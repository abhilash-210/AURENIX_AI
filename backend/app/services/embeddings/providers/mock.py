"""
Mock embedding provider for unit tests.
"""

import hashlib
import random

from app.services.embeddings.base import BaseEmbeddingProvider


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Mock provider that generates deterministic random embeddings based on text hashes.
    """

    def __init__(self, vector_size: int = 1536) -> None:
        self._vector_size = vector_size

    @property
    def name(self) -> str:
        return "mock"

    @property
    def vector_size(self) -> int:
        return self._vector_size

    async def embed_text(self, text: str, model: str | None = None) -> list[float]:
        # Generate a deterministic pseudo-random vector based on text content
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)
        rng = random.Random(seed)
        return [rng.uniform(-1.0, 1.0) for _ in range(self._vector_size)]

    async def embed_batch(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        return [await self.embed_text(text, model) for text in texts]

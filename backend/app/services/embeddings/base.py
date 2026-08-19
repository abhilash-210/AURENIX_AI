"""
Abstract base class for embedding providers.
"""

from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """
    Interface for text embedding providers.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name identifier."""
        pass

    @property
    @abstractmethod
    def vector_size(self) -> int:
        """Return the dimensionality of the generated vectors."""
        pass

    @abstractmethod
    async def embed_text(self, text: str, model: str | None = None) -> list[float]:
        """
        Embed a single text string.
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """
        Embed a list of text strings.
        """
        pass

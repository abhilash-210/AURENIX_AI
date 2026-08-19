"""
Abstract base class for vector storage.
"""

from abc import ABC, abstractmethod
from typing import Any


class SearchResult:
    """Represents a single matching vector from a similarity search."""
    def __init__(
        self,
        id: str,
        score: float,
        payload: dict[str, Any],
    ) -> None:
        self.id = id
        self.score = score
        self.payload = payload


class BaseVectorStore(ABC):
    """
    Interface for vector database operations.
    """

    @abstractmethod
    async def ensure_collection_exists(self, vector_size: int) -> None:
        """Ensure the underlying collection or index exists and is configured."""
        pass

    @abstractmethod
    async def upsert_vectors(self, vectors: list[list[float]], payloads: list[dict[str, Any]], ids: list[str]) -> None:
        """Insert or update vectors with their associated payloads."""
        pass

    @abstractmethod
    async def delete_document_vectors(self, workspace_id: str, document_id: str) -> None:
        """Delete all vectors associated with a specific document within a workspace."""
        pass

    @abstractmethod
    async def search_similar(
        self,
        workspace_id: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.0,
    ) -> list[SearchResult]:
        """Perform a similarity search restricted to a specific workspace."""
        pass

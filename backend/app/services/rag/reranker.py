"""
Reranking abstractions for RAG pipeline.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseReranker(ABC):
    """
    Interface for reranking retrieved documents.
    """

    @abstractmethod
    async def rerank(self, query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Rerank a list of vector search results based on the query.
        """
        pass


class DummyReranker(BaseReranker):
    """
    A pass-through reranker that does nothing.
    Satisfies the architectural abstraction without adding heavy ML dependencies.
    """

    async def rerank(self, query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # In a real implementation, we would score each result against the query
        # and re-sort them. Here, we just rely on the vector similarity score.
        return results

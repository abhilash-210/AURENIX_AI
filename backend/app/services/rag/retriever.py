"""
Retriever component for RAG pipeline.
"""

from typing import Any

from app.services.vector_store.service import VectorStoreService


class Retriever:
    """
    Wraps vector store logic to enforce workspace isolation and format results.
    """

    def __init__(self) -> None:
        self.vector_store = VectorStoreService()

    async def retrieve(
        self,
        workspace_id: str,
        query: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant chunks from Qdrant, strictly bounded to the workspace.
        """
        # We rely on VectorStoreService.search which already enforces workspace isolation
        # via the Qdrant filter condition.
        results = await self.vector_store.search(
            workspace_id=workspace_id,
            query=query,
            limit=top_k,
        )

        # Apply any additional in-memory filters if specified (or we could pass them to Qdrant)
        if filters:
            filtered_results = []
            for res in results:
                payload = res["payload"]
                match = True
                for k, v in filters.items():
                    if payload.get(k) != v:
                        match = False
                        break
                if match:
                    filtered_results.append(res)
            return filtered_results

        return results

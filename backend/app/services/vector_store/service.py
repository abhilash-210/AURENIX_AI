"""
High-level document indexing and retrieval service.
"""

import uuid
from typing import Any

from app.exceptions import AurenixError
from app.services.embeddings.service import EmbeddingService
from app.services.vector_store.qdrant import QdrantVectorStore


class IndexingError(AurenixError):
    error_code = "INDEXING_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message=message)


class VectorStoreService:
    """
    Coordinates embedding generation and vector storage.
    """

    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()
        self.vector_store = QdrantVectorStore()

    async def initialize(self) -> None:
        """Ensure collections exist based on the active embedding provider's vector size."""
        provider = self.embedding_service.get_provider()
        await self.vector_store.ensure_collection_exists(vector_size=provider.vector_size)

    async def index_document(
        self,
        workspace_id: str,
        document_id: str,
        chunks: list[dict[str, Any]],
        source_filename: str,
    ) -> None:
        """
        Embed and index a list of chunks for a document.
        chunks should be a list of dictionaries containing 'id', 'content', and optionally 'page_number'.
        """
        if not chunks:
            return

        texts = [chunk["content"] for chunk in chunks]
        
        try:
            embeddings = await self.embedding_service.embed_batch(texts)
        except Exception as exc:
            raise IndexingError(f"Failed to generate embeddings: {exc}") from exc

        payloads = []
        ids = []
        
        for idx, chunk in enumerate(chunks):
            payload = {
                "workspace_id": workspace_id,
                "document_id": document_id,
                "chunk_id": str(chunk.get("id", uuid.uuid4())),
                "source_filename": source_filename,
                "chunk_text": chunk["content"],
            }
            if "page_number" in chunk and chunk["page_number"] is not None:
                payload["page_number"] = chunk["page_number"]
                
            payloads.append(payload)
            ids.append(str(uuid.uuid4()))

        try:
            await self.vector_store.upsert_vectors(
                vectors=embeddings,
                payloads=payloads,
                ids=ids,
            )
        except Exception as exc:
            raise IndexingError(f"Failed to upsert vectors to database: {exc}") from exc

    async def reindex_document(
        self,
        workspace_id: str,
        document_id: str,
        chunks: list[dict[str, Any]],
        source_filename: str,
    ) -> None:
        """Delete existing vectors for a document and index the new chunks."""
        await self.delete_document_vectors(workspace_id, document_id)
        await self.index_document(workspace_id, document_id, chunks, source_filename)

    async def delete_document_vectors(self, workspace_id: str, document_id: str) -> None:
        """Remove all vectors associated with a document."""
        await self.vector_store.delete_document_vectors(workspace_id, document_id)

    async def search(
        self,
        workspace_id: str,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search for similar document chunks using a text query."""
        try:
            query_vector = await self.embedding_service.embed_text(query)
        except Exception as exc:
            raise IndexingError(f"Failed to embed query: {exc}") from exc

        results = await self.vector_store.search_similar(
            workspace_id=workspace_id,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
        )
        
        return [
            {
                "id": res.id,
                "score": res.score,
                "payload": res.payload,
            }
            for res in results
        ]

    async def delete_workspace_vectors(self, workspace_id: str) -> None:
        """Remove ALL vectors associated with a workspace (used during workspace deletion)."""
        try:
            await self.vector_store.delete_workspace_vectors(workspace_id)
        except Exception:
            pass  # Best-effort; Qdrant may be offline in dev

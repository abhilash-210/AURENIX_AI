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
        if filters and results:
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
            results = filtered_results

        # Fallback to database chunks if vector search returns empty (e.g. offline dev mode)
        if not results:
            try:
                import uuid
                import logging
                from sqlalchemy import select
                from app.database import AsyncSessionLocal
                from app.models.document import Document, DocumentChunk
                
                ws_uuid = uuid.UUID(str(workspace_id))
                async with AsyncSessionLocal() as session:
                    stmt = (
                        select(DocumentChunk, Document)
                        .join(Document, Document.id == DocumentChunk.document_id)
                        .where(Document.workspace_id == ws_uuid)
                        .order_by(DocumentChunk.chunk_index.asc())
                        .limit(top_k)
                    )
                    db_res = await session.execute(stmt)
                    rows = db_res.all()
                    
                    fallback_results = []
                    for chunk, doc in rows:
                        fallback_results.append({
                            "id": str(chunk.id),
                            "score": 0.85,
                            "payload": {
                                "workspace_id": str(workspace_id),
                                "document_id": str(doc.id),
                                "chunk_id": str(chunk.id),
                                "source_filename": doc.filename,
                                "chunk_text": chunk.content,
                                "page_number": chunk.page_number,
                            }
                        })
                    if fallback_results:
                        return fallback_results
            except Exception as exc:
                logging.getLogger(__name__).warning(f"Retriever DB fallback failed: {exc}")

        return results

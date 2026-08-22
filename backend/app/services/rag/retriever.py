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
                import re
                from sqlalchemy import select
                from app.database import AsyncSessionLocal
                from app.models.document import Document, DocumentChunk

                ws_uuid = uuid.UUID(str(workspace_id))
                async with AsyncSessionLocal() as session:
                    # Check if query requests a specific page number
                    page_match = re.search(r"\b(?:page|pg|p\.?)\s*#?\s*(\d+)\b", query.lower())
                    page_filter = int(page_match.group(1)) if page_match else None

                    if page_filter is not None:
                        # Targeted query to fetch exact chunks on the requested page number
                        stmt = (
                            select(DocumentChunk, Document)
                            .join(Document, Document.id == DocumentChunk.document_id)
                            .where(Document.workspace_id == ws_uuid)
                            .where(DocumentChunk.page_number == page_filter)
                            .order_by(DocumentChunk.chunk_index.asc())
                            .limit(top_k)
                        )
                    else:
                        # Fetch more rows than top_k so we can score and rank
                        stmt = (
                            select(DocumentChunk, Document)
                            .join(Document, Document.id == DocumentChunk.document_id)
                            .where(Document.workspace_id == ws_uuid)
                            .order_by(DocumentChunk.chunk_index.asc())
                            .limit(top_k * 10)  # over-fetch to allow ranking
                        )
                    db_res = await session.execute(stmt)
                    rows = db_res.all()

                    if page_filter is not None:
                        fallback_results = []
                        for chunk, doc in rows:
                            fallback_results.append({
                                "id": str(chunk.id),
                                "score": 1.0,
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

                    # Score each chunk by keyword overlap with the query
                    query_words = set(re.findall(r"\w+", query.lower()))
                    # Remove very common stop words from scoring
                    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                                  "have", "has", "had", "do", "does", "did", "will", "would", "could",
                                  "should", "may", "might", "shall", "can", "need", "dare", "used",
                                  "to", "of", "in", "for", "on", "with", "at", "by", "from", "up",
                                  "about", "into", "through", "during", "before", "after", "above",
                                  "below", "between", "out", "off", "over", "under", "again",
                                  "and", "but", "or", "nor", "so", "yet", "both", "either", "neither",
                                  "that", "this", "these", "those", "it", "its", "what", "which",
                                  "who", "whom", "give", "me", "tell", "show", "find", "get", "my"}
                    query_keywords = query_words - stop_words

                    scored = []
                    for chunk, doc in rows:
                        text = (chunk.content or "").strip()
                        # Filter out garbage chunks: too short or purely numeric
                        if len(text) < 15:
                            continue
                        if re.fullmatch(r"[\d\s\.\,\-\+\/\%\(\)]+", text):
                            continue  # skip purely numeric/symbol content
                        # Score by keyword overlap
                        chunk_words = set(re.findall(r"\w+", text.lower()))
                        overlap = len(query_keywords & chunk_words)
                        # Bonus for longer, more informative chunks
                        length_bonus = min(len(text) / 500, 1.0) * 0.3
                        score = overlap + length_bonus
                        scored.append((score, chunk, doc))

                    # Sort by score descending, take top_k
                    scored.sort(key=lambda x: -x[0])
                    top_scored = scored[:top_k]

                    # If keyword scoring found nothing useful, fall back to first non-garbage chunks
                    if not top_scored:
                        for chunk, doc in rows:
                            text = (chunk.content or "").strip()
                            if len(text) >= 15 and not re.fullmatch(r"[\d\s\.\,\-\+\/\%\(\)]+", text):
                                top_scored.append((0.5, chunk, doc))
                                if len(top_scored) >= top_k:
                                    break

                    fallback_results = []
                    for score, chunk, doc in top_scored:
                        fallback_results.append({
                            "id": str(chunk.id),
                            "score": round(score, 3),
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

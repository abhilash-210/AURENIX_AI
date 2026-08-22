"""
Qdrant Vector Database implementation.
"""

import logging
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from app.config import get_settings
from app.exceptions import AurenixError
from app.services.vector_store.base import BaseVectorStore, SearchResult

logger = logging.getLogger(__name__)


class QdrantError(AurenixError):
    """Error interacting with Qdrant."""
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message=message, code="QDRANT_ERROR", status_code=status_code)


class QdrantVectorStore(BaseVectorStore):
    """
    Manages vector storage and retrieval using Qdrant.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        
        # We assume qdrant-client can handle API key being None
        api_key = self.settings.qdrant_api_key.get_secret_value() if self.settings.qdrant_api_key else None
        
        self.client = AsyncQdrantClient(
            url=self.settings.qdrant_url,
            api_key=api_key,
        )
        self.collection_name = self.settings.qdrant_collection_name
        self.memory_collection_name = self.settings.qdrant_memory_collection_name

    async def ensure_collection_exists(self, vector_size: int) -> None:
        """
        Create the Qdrant collection if it doesn't exist.
        Configures it for Cosine distance.
        """
        try:
            collections = await self.client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)
            
            if not exists:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE,
                    ),
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
                
                # Create a payload index on workspace_id for faster tenant filtering
                await self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="workspace_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                
            memory_exists = any(c.name == self.memory_collection_name for c in collections.collections)
            if not memory_exists:
                await self.client.create_collection(
                    collection_name=self.memory_collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE,
                    ),
                )
                logger.info(f"Created Qdrant memory collection: {self.memory_collection_name}")
                
                await self.client.create_payload_index(
                    collection_name=self.memory_collection_name,
                    field_name="workspace_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                await self.client.create_payload_index(
                    collection_name=self.memory_collection_name,
                    field_name="user_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
        except Exception as exc:
            if not self.settings.is_production:
                logger.warning(f"Qdrant ensure_collection failed (dev mode): {exc}")
                return
            raise QdrantError(f"Failed to ensure Qdrant collection: {exc}") from exc

    async def upsert_vectors(
        self, vectors: list[list[float]], payloads: list[dict[str, Any]], ids: list[str]
    ) -> None:
        if not vectors:
            return

        if len(vectors) != len(payloads) or len(vectors) != len(ids):
            raise QdrantError("Mismatch in lengths of vectors, payloads, and ids.")

        points = [
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]

        try:
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )
        except Exception as exc:
            if not self.settings.is_production:
                logger.warning(f"Qdrant upsert_vectors failed (dev mode): {exc}")
                return
            raise QdrantError(f"Failed to upsert vectors to Qdrant: {exc}") from exc

    async def delete_document_vectors(self, workspace_id: str, document_id: str) -> None:
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="workspace_id",
                            match=models.MatchValue(value=workspace_id),
                        ),
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        ),
                    ]
                ),
            )
        except Exception as exc:
            if not self.settings.is_production:
                logger.warning(f"Qdrant delete_document_vectors failed (dev mode): {exc}")
                return
            raise QdrantError(f"Failed to delete document vectors: {exc}") from exc

    async def search_similar(
        self,
        workspace_id: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float = 0.0,
    ) -> list[SearchResult]:
        try:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="workspace_id",
                        match=models.MatchValue(value=workspace_id),
                    )
                ]
            )
            
            if hasattr(self.client, "query_points"):
                response = await self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=limit,
                    score_threshold=score_threshold if score_threshold > 0 else None,
                )
                results = getattr(response, "points", response)
            else:
                results = await self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    query_filter=query_filter,
                    limit=limit,
                    score_threshold=score_threshold if score_threshold > 0 else None,
                )
            
            return [
                SearchResult(
                    id=str(res.id),
                    score=res.score,
                    payload=res.payload or {},
                )
                for res in results
            ]
        except Exception as exc:
            if not self.settings.is_production:
                logger.warning(f"Qdrant vector search failed (using fallback): {exc}")
                return []
            raise QdrantError(f"Failed to search Qdrant: {exc}") from exc

    async def upsert_memory_vectors(
        self, vectors: list[list[float]], payloads: list[dict[str, Any]], ids: list[str]
    ) -> None:
        if not vectors:
            return

        points = [
            models.PointStruct(id=point_id, vector=vector, payload=payload)
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]

        try:
            await self.client.upsert(
                collection_name=self.memory_collection_name,
                points=points,
            )
        except Exception as exc:
            if not self.settings.is_production:
                logger.warning(f"Qdrant upsert memories failed (dev mode): {exc}")
                return
            raise QdrantError(f"Failed to upsert memory vectors: {exc}") from exc

    async def search_memories(
        self,
        workspace_id: str | None,
        user_id: str | None,
        query_vector: list[float],
        limit: int = 5,
        score_threshold: float = 0.0,
    ) -> list[SearchResult]:
        must_conditions = []
        if workspace_id:
            must_conditions.append(
                models.FieldCondition(
                    key="workspace_id",
                    match=models.MatchValue(value=workspace_id),
                )
            )
        if user_id:
            must_conditions.append(
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id),
                )
            )

        try:
            query_filter = models.Filter(must=must_conditions) if must_conditions else None
            if hasattr(self.client, "query_points"):
                response = await self.client.query_points(
                    collection_name=self.memory_collection_name,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=limit,
                    score_threshold=score_threshold if score_threshold > 0 else None,
                )
                results = getattr(response, "points", response)
            else:
                results = await self.client.search(
                    collection_name=self.memory_collection_name,
                    query_vector=query_vector,
                    query_filter=query_filter,
                    limit=limit,
                    score_threshold=score_threshold if score_threshold > 0 else None,
                )
            return [SearchResult(id=str(res.id), score=res.score, payload=res.payload or {}) for res in results]
        except Exception as exc:
            if not self.settings.is_production:
                logger.warning(f"Qdrant search memories failed (dev mode): {exc}")
                return []
            raise QdrantError(f"Failed to search memories: {exc}") from exc

    async def delete_memory_vector(self, memory_id: str) -> None:
        try:
            await self.client.delete(
                collection_name=self.memory_collection_name,
                points_selector=models.PointIdsList(points=[memory_id]),
            )
        except Exception as exc:
            raise QdrantError(f"Failed to delete memory vector: {exc}") from exc

    async def delete_workspace_vectors(self, workspace_id: str) -> None:
        """Delete ALL document and memory vectors for an entire workspace."""
        ws_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="workspace_id",
                    match=models.MatchValue(value=workspace_id),
                )
            ]
        )
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=ws_filter),
            )
            await self.client.delete(
                collection_name=self.memory_collection_name,
                points_selector=models.FilterSelector(filter=ws_filter),
            )
            logger.info(f"Deleted all vectors for workspace: {workspace_id}")
        except Exception as exc:
            if not self.settings.is_production:
                logger.warning(f"Qdrant workspace vector delete failed (dev mode): {exc}")
                return
            raise QdrantError(f"Failed to delete workspace vectors: {exc}") from exc

    async def delete_document_vectors(self, workspace_id: str, document_id: str) -> None:
        """Delete all vectors for a specific document."""
        doc_filter = models.Filter(
            must=[
                models.FieldCondition(key="workspace_id", match=models.MatchValue(value=workspace_id)),
                models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id)),
            ]
        )
        try:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=doc_filter),
            )
        except Exception as exc:
            if not self.settings.is_production:
                logger.warning(f"Qdrant document vector delete failed (dev mode): {exc}")
                return
            raise QdrantError(f"Failed to delete document vectors: {exc}") from exc

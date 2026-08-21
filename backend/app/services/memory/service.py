"""
Service wrapper for AI Memory system.
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models.memory import Memory, MemoryScope
from app.services.embeddings.service import EmbeddingService
from app.services.llm.service import LLMService
from app.services.llm.types import ChatMessage, CompletionOptions
from app.services.memory.schemas import MemoryCreate, MemoryExtractionResult
from app.services.vector_store.qdrant import QdrantVectorStore

logger = logging.getLogger(__name__)


class VectorStoreService:
    @staticmethod
    def get_instance() -> QdrantVectorStore:
        return QdrantVectorStore()


class MemoryService:
    """
    Manages semantic memory extraction, CRUD, and retrieval.
    """

    def __init__(
        self,
        db: AsyncSession,
        vector_store: QdrantVectorStore | None = None,
    ) -> None:
        self.db = db
        self.llm = LLMService()
        self.embedding_service = EmbeddingService()
        self.vector_store: QdrantVectorStore = vector_store or VectorStoreService.get_instance()

    async def get_memories(
        self,
        workspace_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None
    ) -> list[Memory]:
        stmt = select(Memory)
        
        # Enforce scoping
        if workspace_id:
            stmt = stmt.where(Memory.workspace_id == workspace_id)
        if user_id:
            stmt = stmt.where(Memory.user_id == user_id)
            
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_memory(self, memory_id: uuid.UUID, user_id: uuid.UUID) -> None:
        stmt = select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
        result = await self.db.execute(stmt)
        memory = result.scalar_one_or_none()
        
        if not memory:
            raise NotFoundError("Memory not found")
            
        await self.db.delete(memory)
        await self.db.commit()
        
        # Cascade to Qdrant
        await self.vector_store.delete_memory_vector(str(memory_id))

    async def extract_and_save_memories(
        self,
        messages_exchange: list[dict[str, str]],
        workspace_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
        conversation_id: uuid.UUID | None,
    ) -> None:
        """
        Background task to evaluate a conversation snippet and extract permanent memories.
        """
        try:
            conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages_exchange])
            
            system_prompt = (
                "You are an AI Memory Extraction agent. Your task is to extract permanent facts, "
                "user preferences, and context that should be remembered for future interactions.\n"
                "RULES:\n"
                "- Extract ONLY highly useful facts or preferences.\n"
                "- Do NOT store secrets, passwords, or temporary small talk.\n"
                "- Write each memory as a concise declarative sentence.\n"
                "- If nothing is worth remembering, return an empty list."
            )
            
            llm_messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=f"Conversation:\n{conversation_text}")
            ]
            
            response = await self.llm.complete_structured(
                messages=llm_messages,
                response_schema=MemoryExtractionResult,
                options=CompletionOptions(temperature=0.0)
            )
            
            extracted_facts = response.parsed.memories
            
            if not extracted_facts:
                return
                
            for fact in extracted_facts:
                memory = Memory(
                    scope=MemoryScope.USER if user_id else MemoryScope.WORKSPACE,
                    content=fact,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    conversation_id=conversation_id,
                )
                self.db.add(memory)
                await self.db.flush() # flush to get the UUID
                
                # Embed and save to Qdrant
                vector = await self.embedding_service.embed_text(fact)
                payload = {
                    "content": fact,
                    "workspace_id": str(workspace_id) if workspace_id else None,
                    "user_id": str(user_id) if user_id else None,
                    "scope": memory.scope.value,
                }
                await self.vector_store.upsert_memory_vectors(
                    vectors=[vector],
                    payloads=[payload],
                    ids=[str(memory.id)]
                )
                
            await self.db.commit()
            logger.info(f"Extracted and saved {len(extracted_facts)} memories.")
            
        except Exception as exc:
            logger.error(f"Failed to extract memory: {exc}")
            # Non-blocking, so we just catch and log

    async def get_relevant_memories(
        self,
        query: str,
        workspace_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
    ) -> list[str]:
        """
        Embeds query and fetches relevant memories from Qdrant.
        """
        try:
            vector = await self.embedding_service.embed_text(query)
            
            # Fetch workspace scoped
            ws_results = []
            if workspace_id:
                ws_results = await self.vector_store.search_memories(
                    workspace_id=str(workspace_id),
                    user_id=None,
                    query_vector=vector,
                    limit=3,
                )
                
            # Fetch user scoped
            user_results = []
            if user_id:
                user_results = await self.vector_store.search_memories(
                    workspace_id=None,
                    user_id=str(user_id),
                    query_vector=vector,
                    limit=3,
                )
                
            # Combine and deduplicate
            all_facts = []
            for res in ws_results + user_results:
                content = res.payload.get("content")
                if content and content not in all_facts:
                    all_facts.append(content)
                    
            return all_facts
        except Exception as exc:
            logger.error(f"Failed to retrieve memories: {exc}")
            return []

"""
Chat service for managing conversations, messages, and RAG streaming.
"""

import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ForbiddenError, NotFoundError
from app.models.chat import Conversation, Message
from app.schemas.conversation import ConversationCreate
from app.services.llm.service import LLMService
from app.services.llm.types import ChatMessage, CompletionOptions
from app.services.memory.service import MemoryService
from app.services.rag.context import CitationBuilder, ContextBuilder
from app.services.rag.processor import QueryProcessor
from app.services.rag.reranker import DummyReranker
from app.services.rag.retriever import Retriever

logger = logging.getLogger(__name__)


class ChatService:
    """
    Manages chat persistence and coordinates RAG streaming.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.processor = QueryProcessor()
        self.retriever = Retriever()
        self.reranker = DummyReranker()
        self.context_builder = ContextBuilder()
        self.citation_builder = CitationBuilder()
        self.llm_service = LLMService()
        self.memory_service = MemoryService(self.db)

    async def create_conversation(self, workspace_id: uuid.UUID, owner_id: uuid.UUID, data: ConversationCreate) -> Conversation:
        conversation = Conversation(
            workspace_id=workspace_id,
            owner_id=owner_id,
            title=data.title,
        )
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def get_conversation(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Conversation:
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise NotFoundError("Conversation not found")
            
        if str(conversation.owner_id) != str(user_id):
            raise ForbiddenError("You do not have access to this conversation")
            
        return conversation

    async def get_conversations(self, workspace_id: uuid.UUID, user_id: uuid.UUID, page: int = 1, size: int = 20) -> tuple[list[Conversation], int]:
        offset = (page - 1) * size
        
        # Get total
        count_stmt = select(func.count(Conversation.id)).where(
            Conversation.workspace_id == workspace_id,
            Conversation.owner_id == user_id
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()
        
        # Get items
        stmt = select(Conversation).where(
            Conversation.workspace_id == workspace_id,
            Conversation.owner_id == user_id
        ).order_by(Conversation.updated_at.desc()).offset(offset).limit(size)
        
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        
        return items, total

    async def delete_conversation(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> None:
        conversation = await self.get_conversation(conversation_id, user_id)
        # Explicitly delete messages first to ensure clean cascade
        from sqlalchemy import delete as sql_delete
        from app.models.chat import Message
        await self.db.execute(sql_delete(Message).where(Message.conversation_id == conversation_id))
        await self.db.delete(conversation)
        await self.db.commit()

    async def rename_conversation(self, conversation_id: uuid.UUID, user_id: uuid.UUID, new_title: str) -> "Conversation":
        conversation = await self.get_conversation(conversation_id, user_id)
        conversation.title = new_title
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def get_messages(self, conversation_id: uuid.UUID, user_id: uuid.UUID, page: int = 1, size: int = 50) -> tuple[list[Message], int]:
        # Enforce access
        await self.get_conversation(conversation_id, user_id)
        
        offset = (page - 1) * size
        
        count_stmt = select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()
        
        # Messages ordered sequentially by creation time
        stmt = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).offset(offset).limit(size)
        
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        
        return items, total

    async def stream_rag_chat(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
    ) -> AsyncGenerator[str, None]:
        """
        Execute RAG logic, stream response, and persist messages.
        """
        conversation = await self.get_conversation(conversation_id, user_id)
        workspace_id = str(conversation.workspace_id)

        # 1. Save user message immediately
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )
        self.db.add(user_msg)
        await self.db.commit()

        # 2. Get past history to build chat context
        # Limit to last 10 messages for context window
        hist_stmt = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).limit(10)
        hist_res = await self.db.execute(hist_stmt)
        history_msgs = reversed(list(hist_res.scalars().all()))

        messages_for_llm: list[ChatMessage] = []

        # 3. Perform RAG
        processed_query = self.processor.process(content)
        retrieved_results = await self.retriever.retrieve(
            workspace_id=workspace_id,
            query=processed_query,
            top_k=5,
        )

        citations_data = []
        
        if not retrieved_results:
            # No documents found, yield fallback response without hitting LLM
            fallback = "I couldn't find any relevant documents in this workspace to answer your question."
            
            # Save assistant message
            assistant_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=fallback,
                citations=[],
            )
            self.db.add(assistant_msg)
            await self.db.commit()
            
            chunk_data = {"delta": fallback, "finish_reason": "stop", "citations": []}
            yield f"data: {json.dumps(chunk_data)}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Rerank and build context
        reranked_results = await self.reranker.rerank(processed_query, retrieved_results)
        context_str = self.context_builder.build_context(reranked_results)
        
        # Build Citations for saving
        citations = self.citation_builder.build_citations(reranked_results)
        citations_data = [c.model_dump() for c in citations]

        # Fetch semantic memories
        memories = await self.memory_service.get_relevant_memories(
            query=content,
            workspace_id=conversation.workspace_id,
            user_id=conversation.owner_id
        )
        memory_str = "\n".join([f"- {m}" for m in memories]) if memories else "No relevant memories found."

        # 4. Construct System Prompt
        system_prompt = (
            "You are an AI assistant answering questions based strictly on the provided context.\n"
            "Use the provided Document [X] tags to cite your sources (e.g., 'As stated in [1]...').\n"
            "If the answer is not contained in the context, say 'I cannot answer this based on the provided documents.'\n"
            "Do not hallucinate or use outside knowledge.\n\n"
            "Context:\n"
            f"{context_str}\n\n"
            "Relevant Past Memories:\n"
            f"{memory_str}"
        )
        
        messages_for_llm.append(ChatMessage(role="system", content=system_prompt))
        
        # Append history
        for msg in history_msgs:
            # We already added the user message to DB, but we need to pass it to LLM
            messages_for_llm.append(ChatMessage(role=msg.role, content=msg.content))

        # 5. Stream from LLM
        full_response = ""
        try:
            options = CompletionOptions(temperature=0.0)
            async for chunk in self.llm_service.stream_complete(messages_for_llm, options):
                if chunk.delta:
                    full_response += chunk.delta
                    
                chunk_data = {
                    "delta": chunk.delta,
                    "finish_reason": chunk.finish_reason,
                    "citations": citations_data if chunk.finish_reason else []
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
            
            yield "data: [DONE]\n\n"
            
        except Exception as exc:
            logger.exception("Error during RAG streaming")
            err_payload = {"error": "An error occurred during generation."}
            yield f"data: {json.dumps(err_payload)}\n\n"
        finally:
            # Save the accumulated assistant message even if interrupted or failed
            if full_response:
                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_response,
                    citations=citations_data,
                )
                self.db.add(assistant_msg)
                
                # Update conversation timestamp
                conversation.updated_at = func.now()
                await self.db.commit()

                # Trigger asynchronous memory extraction
                extraction_exchange = [
                    {"role": "user", "content": content},
                    {"role": "assistant", "content": full_response}
                ]
                
                # Use a fresh DB session for the background task to avoid closed transaction issues
                from app.database import AsyncSessionLocal
                
                async def extract_task():
                    async with AsyncSessionLocal() as bg_db:
                        bg_memory_service = MemoryService(bg_db)
                        await bg_memory_service.extract_and_save_memories(
                            messages_exchange=extraction_exchange,
                            workspace_id=conversation.workspace_id,
                            user_id=conversation.owner_id,
                            conversation_id=conversation_id,
                        )
                
                asyncio.create_task(extract_task())

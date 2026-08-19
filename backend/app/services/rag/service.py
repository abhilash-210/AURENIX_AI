"""
RAG Orchestrator Service.
"""

import logging

from app.exceptions import LLMError
from app.services.llm.service import LLMService
from app.services.llm.types import ChatMessage, CompletionOptions
from app.services.rag.context import CitationBuilder, ContextBuilder
from app.services.rag.processor import QueryProcessor
from app.services.rag.reranker import DummyReranker
from app.services.rag.retriever import Retriever
from app.services.rag.schemas import RAGQuery, RAGResponse

logger = logging.getLogger(__name__)


class RAGService:
    """
    Coordinates the complete Retrieval-Augmented Generation pipeline.
    """

    def __init__(self) -> None:
        self.processor = QueryProcessor()
        self.retriever = Retriever()
        self.reranker = DummyReranker()
        self.context_builder = ContextBuilder()
        self.citation_builder = CitationBuilder()
        self.llm_service = LLMService()

    async def answer_question(self, workspace_id: str, query: RAGQuery) -> RAGResponse:
        """
        Execute the full RAG pipeline for a given query in a specific workspace.
        """
        # 1. Process Query
        processed_query = self.processor.process(query.query)
        logger.info(f"RAG query processed. workspace_id={workspace_id}")

        # 2. Retrieve Documents
        retrieved_results = await self.retriever.retrieve(
            workspace_id=workspace_id,
            query=processed_query,
            top_k=query.top_k,
            filters=query.filters,
        )

        if not retrieved_results:
            return RAGResponse(
                answer="I couldn't find any relevant documents in this workspace to answer your question.",
                citations=[],
            )

        # 3. Rerank (Currently a pass-through DummyReranker)
        reranked_results = await self.reranker.rerank(processed_query, retrieved_results)

        # 4. Build Context
        context_str = self.context_builder.build_context(reranked_results)

        # 5. Build System Prompt & Call LLM
        system_prompt = (
            "You are an AI assistant answering questions based strictly on the provided context.\n"
            "Use the provided Document [X] tags to cite your sources (e.g., 'As stated in [1]...').\n"
            "If the answer is not contained in the context, say 'I cannot answer this based on the provided documents.'\n"
            "Do not hallucinate or use outside knowledge.\n\n"
            "Context:\n"
            f"{context_str}"
        )

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=processed_query),
        ]

        try:
            llm_response = await self.llm_service.complete(
                messages=messages,
                options=CompletionOptions(),
            )
        except Exception as exc:
            logger.error(f"LLM failure during RAG generation: {exc}")
            raise LLMError("Failed to generate an answer from the LLM.") from exc

        # 6. Build Citations
        citations = self.citation_builder.build_citations(reranked_results)

        # 7. Return Result
        return RAGResponse(
            answer=llm_response.content,
            citations=citations,
        )

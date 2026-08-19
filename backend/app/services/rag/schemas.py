"""
Pydantic schemas for the RAG pipeline.
"""

import uuid
from typing import Any

from pydantic import BaseModel, Field


class RAGQuery(BaseModel):
    query: str = Field(..., description="The user's question.")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve.")
    filters: dict[str, Any] = Field(default_factory=dict, description="Optional metadata filters.")
    # In a full app, we might include conversation_id here for memory.


class SourceDocument(BaseModel):
    document_id: str
    chunk_id: str
    source_filename: str
    page_number: int | None = None
    relevance_score: float = 0.0


class Citation(BaseModel):
    citation_id: str = Field(description="The inline marker used in the text, e.g. [1]")
    source: SourceDocument
    quote: str | None = Field(default=None, description="The exact text chunk used.")


class RAGResponse(BaseModel):
    answer: str
    citations: list[Citation]
    # We could also include usage metrics here.

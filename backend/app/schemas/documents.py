"""
Pydantic API schemas for document management and ingestion endpoints.
"""

from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any
from pydantic import BaseModel, Field

from app.schemas.common import ResponseMeta


class DocumentChunkItem(BaseModel):
    """Chunk DTO returned for embedding and vector layer consumption."""

    id: uuid.UUID = Field(description="Unique chunk UUID")
    document_id: uuid.UUID = Field(description="Parent document UUID")
    chunk_index: int = Field(ge=0, description="0-based sequence index")
    content: str = Field(description="Clean text content")
    page_number: int | None = Field(default=None, description="Page number if applicable")
    row_number: int | None = Field(default=None, description="Row index if applicable")
    char_count: int = Field(ge=0, description="Character count")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary")


class DocumentResponseData(BaseModel):
    """Summary representation of an ingested document."""

    id: uuid.UUID = Field(description="Document UUID")
    workspace_id: uuid.UUID = Field(description="Workspace UUID")
    owner_id: uuid.UUID = Field(description="Owner user UUID")
    filename: str = Field(description="Original filename")
    file_type: str = Field(description="File extension")
    file_size: int = Field(ge=0, description="File size in bytes")
    status: str = Field(description="Ingestion status ('uploaded' | 'processing' | 'completed' | 'failed')")
    total_pages: int | None = Field(default=None, description="Total extracted pages/rows")
    total_chunks: int | None = Field(default=None, description="Total chunks generated")
    error_message: str | None = Field(default=None, description="Error details if failed")
    created_at: datetime = Field(description="Creation timestamp")


class DocumentResponse(BaseModel):
    """Response envelope for single document detail."""

    data: DocumentResponseData
    meta: ResponseMeta


class DocumentListResponse(BaseModel):
    """Response envelope for a list of workspace documents."""

    data: list[DocumentResponseData]
    meta: ResponseMeta


class ChunkListResponse(BaseModel):
    """Response envelope for document chunks consumption."""

    data: list[DocumentChunkItem]
    meta: ResponseMeta

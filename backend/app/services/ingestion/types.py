"""
Domain types and DTOs for the document ingestion pipeline.
"""

from __future__ import annotations

import uuid
from typing import Any
from pydantic import BaseModel, Field


class ParsedPage(BaseModel):
    """Extracted content from a single document page or tabular row."""

    page_number: int | None = Field(default=None, ge=1, description="1-based page index")
    row_number: int | None = Field(default=None, ge=1, description="1-based row index (for CSVs)")
    text: str = Field(description="Raw extracted text content")


class ParsedDocument(BaseModel):
    """Complete document text structure extracted by format parser."""

    pages: list[ParsedPage] = Field(default_factory=list, description="Extracted pages or sections")
    total_pages: int = Field(default=0, ge=0, description="Total pages/rows extracted")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Format-specific metadata")


class RawChunk(BaseModel):
    """A text chunk ready for storage and downstream embedding vectorization."""

    chunk_id: str = Field(description="Unique chunk identifier")
    document_id: str = Field(description="Parent document UUID string")
    chunk_index: int = Field(ge=0, description="0-based sequence index")
    content: str = Field(description="Clean text content")
    page_number: int | None = Field(default=None, description="Page number if applicable")
    row_number: int | None = Field(default=None, description="Row index if applicable")
    char_count: int = Field(ge=0, description="Character count")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")


class IngestionResult(BaseModel):
    """Summary result of a completed document ingestion run."""

    document_id: uuid.UUID = Field(description="Document UUID")
    workspace_id: uuid.UUID = Field(description="Workspace UUID")
    owner_id: uuid.UUID = Field(description="Owner user UUID")
    filename: str = Field(description="Original filename")
    file_type: str = Field(description="Canonical extension")
    file_size: int = Field(ge=0, description="Size in bytes")
    status: str = Field(description="Ingestion status ('completed' | 'failed')")
    total_pages: int | None = Field(default=None, description="Total pages")
    chunk_count: int = Field(default=0, ge=0, description="Number of generated chunks")
    chunks: list[RawChunk] = Field(default_factory=list, description="List of generated chunks")
    error_message: str | None = Field(default=None, description="Failure reason if failed")

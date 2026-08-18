"""
Document Ingestion Service — Orchestrates upload, validation, storage, parsing, text cleaning, chunking, and database persistence.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import DocumentError
from app.models.document import Document, DocumentChunk
from app.services.ingestion.chunker import RecursiveTextChunker
from app.services.ingestion.parsers.factory import ParserFactory
from app.services.ingestion.storage import FileStorageManager
from app.services.ingestion.types import IngestionResult, RawChunk
from app.services.ingestion.validators import validate_file_upload

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """
    Service managing the lifecycle of document ingestion.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        storage_manager: FileStorageManager | None = None,
    ) -> None:
        self.db = db_session
        self.storage_manager = storage_manager or FileStorageManager()

    async def ingest_document(
        self,
        content: bytes,
        filename: str,
        workspace_id: uuid.UUID,
        owner_id: uuid.UUID,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> IngestionResult:
        """
        Execute full document ingestion pipeline for an uploaded file.
        """
        settings = get_settings()
        target_chunk_size = chunk_size or settings.default_chunk_size
        target_chunk_overlap = chunk_overlap or settings.default_chunk_overlap

        # 1. Validate file extension, size, and magic signature
        file_type = validate_file_upload(
            filename=filename,
            content=content,
            max_size_mb=settings.max_upload_size_mb,
        )

        doc_id = uuid.uuid4()
        file_size = len(content)

        # 2. Save raw file to storage
        storage_path = self.storage_manager.save_file(
            content=content,
            original_filename=filename,
            document_id=doc_id,
            workspace_id=workspace_id,
        )

        # 3. Create document DB record (status: uploaded)
        doc_record = Document(
            id=doc_id,
            workspace_id=workspace_id,
            owner_id=owner_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            storage_path=storage_path,
            status="uploaded",
        )
        self.db.add(doc_record)
        await self.db.commit()

        # 4. Update status to processing
        doc_record.status = "processing"
        await self.db.commit()

        raw_chunks: list[RawChunk] = []

        try:
            # 5. Extract text via format parser
            parser = ParserFactory.get_parser(file_type)
            parsed_doc = await parser.parse(content, filename)

            # 6. Split into metadata-rich chunks
            chunker = RecursiveTextChunker(
                chunk_size=target_chunk_size,
                chunk_overlap=target_chunk_overlap,
            )
            raw_chunks = chunker.chunk_document(
                document_id=doc_id,
                source_filename=filename,
                parsed_doc=parsed_doc,
                extra_metadata={
                    "workspace_id": str(workspace_id),
                    "owner_id": str(owner_id),
                },
            )

            # 7. Save document chunks to database
            for raw_chunk in raw_chunks:
                chunk_record = DocumentChunk(
                    id=uuid.UUID(raw_chunk.chunk_id.replace(f"chunk_{doc_id}_", "")) if False else uuid.uuid4(),
                    document_id=doc_id,
                    chunk_index=raw_chunk.chunk_index,
                    content=raw_chunk.content,
                    page_number=raw_chunk.page_number,
                    row_number=raw_chunk.row_number,
                    char_count=raw_chunk.char_count,
                    metadata_json=json.dumps(raw_chunk.metadata),
                )
                self.db.add(chunk_record)

            # 8. Update document status to completed
            doc_record.status = "completed"
            doc_record.total_pages = parsed_doc.total_pages
            doc_record.total_chunks = len(raw_chunks)
            doc_record.error_message = None
            await self.db.commit()

            logger.info(
                "Document ingested successfully",
                extra={
                    "document_id": str(doc_id),
                    "filename": filename,
                    "chunks": len(raw_chunks),
                },
            )

            return IngestionResult(
                document_id=doc_id,
                workspace_id=workspace_id,
                owner_id=owner_id,
                filename=filename,
                file_type=file_type,
                file_size=file_size,
                status="completed",
                total_pages=parsed_doc.total_pages,
                chunk_count=len(raw_chunks),
                chunks=raw_chunks,
            )
        except Exception as exc:
            logger.exception(
                "Document ingestion failed",
                extra={"document_id": str(doc_id), "filename": filename, "error": str(exc)},
            )
            doc_record.status = "failed"
            doc_record.error_message = str(exc)
            await self.db.commit()

            if isinstance(exc, DocumentError):
                raise exc
            msg = f"Document processing failed: {exc}"
            raise DocumentError(msg) from exc

    async def get_document(self, document_id: uuid.UUID) -> Document | None:
        """Fetch document model by ID."""
        stmt = select(Document).where(Document.id == document_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_workspace_documents(self, workspace_id: uuid.UUID) -> Sequence[Document]:
        """Fetch all documents in a workspace."""
        stmt = select(Document).where(Document.workspace_id == workspace_id).order_by(Document.created_at.desc())
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_document_chunks(self, document_id: uuid.UUID) -> Sequence[DocumentChunk]:
        """Fetch all text chunks belonging to a document."""
        stmt = select(DocumentChunk).where(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index.asc())
        res = await self.db.execute(stmt)
        return res.scalars().all()

"""
Document Ingestion REST API routes.
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import NotFoundError, ForbiddenError, PaymentRequiredError
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.routes.auth import get_current_user
from app.dependencies import get_workspace_member, require_workspace_role
from app.schemas.common import ResponseMeta
from app.schemas.documents import (
    ChunkListResponse,
    DocumentChunkItem,
    DocumentListResponse,
    DocumentResponse,
    DocumentResponseData,
)
from app.services.ingestion.service import DocumentIngestionService

router = APIRouter(tags=["Documents"])


@router.post(
    "/workspaces/{workspace_id}/documents/upload",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentResponse,
    summary="Upload and ingest a document",
    description="Upload a document (.pdf, .docx, .txt, .csv) for validation, parsing, text cleaning, chunking, and metadata generation.",
)
async def upload_document(
    workspace_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    chunk_size: int | None = Form(None),
    chunk_overlap: int | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    request_id: str = getattr(request.state, "request_id", "unknown")
    
    # 1. Enforce access
    member = await get_workspace_member(workspace_id, current_user.id, db)
    
    # 2. Check limits — fetch workspace directly to avoid lazy-load issue
    from sqlalchemy import select, func
    from app.models.document import Document
    from app.models.workspace import Workspace
    workspace = await db.get(Workspace, workspace_id)
    max_docs = (workspace.settings or {}).get("max_documents", 100) if workspace else 100
    doc_count = await db.scalar(select(func.count(Document.id)).where(Document.workspace_id == workspace_id))
    if doc_count is not None and doc_count >= max_docs:
        raise PaymentRequiredError(f"Workspace has reached its maximum document limit ({max_docs}).")

    content = await file.read()
    filename = file.filename or "unnamed_document"

    service = DocumentIngestionService(db)
    result = await service.ingest_document(
        content=content,
        filename=filename,
        workspace_id=workspace_id,
        owner_id=current_user.id,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    # Index chunks in vector store
    try:
        from app.services.vector_store.service import VectorStoreService
        vs_service = VectorStoreService()
        chunks_payload = [
            {"id": c.chunk_id, "content": c.content, "page_number": c.page_number}
            for c in result.chunks
        ]
        await vs_service.index_document(
            workspace_id=str(workspace_id),
            document_id=str(result.document_id),
            chunks=chunks_payload,
            source_filename=filename,
        )
    except Exception as exc:
        logging.getLogger(__name__).warning(f"Vector indexing skipped/failed (dev fallback active): {exc}")

    doc_record = await service.get_document(result.document_id)
    if not doc_record:
        msg = f"Document '{result.document_id}' not found after ingestion."
        raise NotFoundError(msg)

    return DocumentResponse(
        data=DocumentResponseData(
            id=doc_record.id,
            workspace_id=doc_record.workspace_id,
            owner_id=doc_record.owner_id,
            filename=doc_record.filename,
            file_type=doc_record.file_type,
            file_size=doc_record.file_size,
            status=doc_record.status,
            total_pages=doc_record.total_pages,
            total_chunks=doc_record.total_chunks,
            error_message=doc_record.error_message,
            created_at=doc_record.created_at,
        ),
        meta=ResponseMeta(request_id=request_id),
    )


@router.get(
    "/workspaces/{workspace_id}/documents",
    status_code=status.HTTP_200_OK,
    response_model=DocumentListResponse,
    summary="List workspace documents",
    description="Retrieve all documents uploaded within a workspace.",
)
async def list_workspace_documents(
    workspace_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    request_id: str = getattr(request.state, "request_id", "unknown")
    # Enforce membership — returns 404 if user is not a member
    await get_workspace_member(workspace_id, current_user.id, db)
    service = DocumentIngestionService(db)
    documents = await service.list_workspace_documents(workspace_id)

    items = [
        DocumentResponseData(
            id=d.id,
            workspace_id=d.workspace_id,
            owner_id=d.owner_id,
            filename=d.filename,
            file_type=d.file_type,
            file_size=d.file_size,
            status=d.status,
            total_pages=d.total_pages,
            total_chunks=d.total_chunks,
            error_message=d.error_message,
            created_at=d.created_at,
        )
        for d in documents
    ]

    return DocumentListResponse(
        data=items,
        meta=ResponseMeta(request_id=request_id),
    )


@router.get(
    "/documents/{document_id}",
    status_code=status.HTTP_200_OK,
    response_model=DocumentResponse,
    summary="Get document details",
    description="Fetch processing status and metadata for a document.",
)
async def get_document(
    document_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    request_id: str = getattr(request.state, "request_id", "unknown")
    service = DocumentIngestionService(db)
    doc_record = await service.get_document(document_id)

    if not doc_record:
        msg = f"Document '{document_id}' not found."
        raise NotFoundError(msg)

    return DocumentResponse(
        data=DocumentResponseData(
            id=doc_record.id,
            workspace_id=doc_record.workspace_id,
            owner_id=doc_record.owner_id,
            filename=doc_record.filename,
            file_type=doc_record.file_type,
            file_size=doc_record.file_size,
            status=doc_record.status,
            total_pages=doc_record.total_pages,
            total_chunks=doc_record.total_chunks,
            error_message=doc_record.error_message,
            created_at=doc_record.created_at,
        ),
        meta=ResponseMeta(request_id=request_id),
    )


@router.get(
    "/documents/{document_id}/chunks",
    status_code=status.HTTP_200_OK,
    response_model=ChunkListResponse,
    summary="Get document text chunks",
    description="Retrieve extracted chunks with metadata for embedding and vector layer consumption.",
)
async def get_document_chunks(
    document_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> ChunkListResponse:
    request_id: str = getattr(request.state, "request_id", "unknown")
    service = DocumentIngestionService(db)
    doc_record = await service.get_document(document_id)

    if not doc_record:
        msg = f"Document '{document_id}' not found."
        raise NotFoundError(msg)

    chunks = await service.get_document_chunks(document_id)

    items = [
        DocumentChunkItem(
            id=c.id,
            document_id=c.document_id,
            chunk_index=c.chunk_index,
            content=c.content,
            page_number=c.page_number,
            row_number=c.row_number,
            char_count=c.char_count,
            metadata=c.metadata_dict,
        )
        for c in chunks
    ]

    return ChunkListResponse(
        data=items,
        meta=ResponseMeta(request_id=request_id),
    )


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = DocumentIngestionService(db)
    doc_record = await service.get_document(document_id)

    if not doc_record:
        raise NotFoundError("Document not found.")

    member = await get_workspace_member(doc_record.workspace_id, current_user.id, db)

    # Only owner or admin/owner can delete
    if str(doc_record.owner_id) != str(current_user.id) and member.role not in ("admin", "owner"):
        raise ForbiddenError("You do not have permission to delete this document.")

    await db.delete(doc_record)
    await db.commit()
    
    # Log the action
    from app.services.audit.service import AuditService
    audit_service = AuditService(db)
    await audit_service.log_action(
        workspace_id=doc_record.workspace_id,
        user_id=current_user.id,
        action="document.deleted",
        resource_type="Document",
        resource_id=str(doc_record.id),
        details={"filename": doc_record.filename},
    )


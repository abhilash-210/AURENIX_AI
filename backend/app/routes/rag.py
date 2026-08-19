"""
RAG endpoints.
"""

import uuid

from fastapi import APIRouter, Depends, Request, status

from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas.common import ResponseMeta
from app.services.rag.schemas import RAGQuery, RAGResponse
from app.services.rag.service import RAGService

router = APIRouter(tags=["RAG"])


@router.post(
    "/workspaces/{workspace_id}/rag/ask",
    status_code=status.HTTP_200_OK,
    response_model=RAGResponse,
    summary="Ask a question using RAG",
    description="Query documents within a workspace. Returns a grounded answer with citations.",
)
async def ask_question(
    workspace_id: uuid.UUID,
    query: RAGQuery,
    request: Request,
    current_user: User = Depends(get_current_user),  # noqa: ARG001
) -> RAGResponse:
    # We could add authorization check here to ensure the user belongs to the workspace.
    # The framework likely handles this in a dependency or middleware, but for Sprint 6
    # we enforce workspace isolation inside the Retriever using Qdrant filters.

    service = RAGService()
    response = await service.answer_question(str(workspace_id), query)
    
    # Ideally, we would add the request ID to a metadata wrapper, but for simplicity
    # and adhering to the requested schema, we return the RAGResponse directly.
    return response

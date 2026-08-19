"""
Analytics and Metrics REST API routes.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import ForbiddenError, NotFoundError
from app.models.chat import Conversation, Message
from app.models.document import Document
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.routes.auth import get_current_user
from app.schemas.common import ApiResponse, ResponseMeta

router = APIRouter(tags=["Analytics"])


async def verify_workspace_access(
    workspace_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> Workspace:
    """Check if the user is a member of the workspace."""
    stmt = (
        select(Workspace)
        .join(WorkspaceMember)
        .where(
            Workspace.id == workspace_id,
            WorkspaceMember.user_id == user_id,
            Workspace.is_active == True,
        )
    )
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()

    if not workspace:
        # Either doesn't exist or user doesn't have access
        # Return NotFound to avoid enumerating workspaces
        raise NotFoundError(f"Workspace '{workspace_id}' not found.")
    return workspace


@router.get(
    "/workspaces/{workspace_id}/analytics/overview",
    status_code=status.HTTP_200_OK,
    summary="Get analytics overview",
    description="Retrieve aggregate metrics for the workspace.",
)
async def get_analytics_overview(
    workspace_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    request_id: str = getattr(request.state, "request_id", "unknown")

    await verify_workspace_access(workspace_id, current_user.id, db)

    # 1. Documents count
    doc_stmt = select(func.count(Document.id)).where(Document.workspace_id == workspace_id)
    doc_count = await db.scalar(doc_stmt)

    # 2. Conversations count
    conv_stmt = select(func.count(Conversation.id)).where(Conversation.workspace_id == workspace_id)
    conv_count = await db.scalar(conv_stmt)

    # 3. AI Requests count (messages where role == 'assistant')
    ai_msg_stmt = (
        select(func.count(Message.id))
        .join(Conversation)
        .where(Conversation.workspace_id == workspace_id, Message.role == "assistant")
    )
    ai_requests_count = await db.scalar(ai_msg_stmt)

    metrics = {
        "documents": doc_count or 0,
        "conversations": conv_count or 0,
        "ai_requests": ai_requests_count or 0,
        # Unavailable metrics strictly marked as None to avoid fabricating data
        "agent_executions": None,
        "retrieval_operations": None,
        "response_latency": None,
        "token_usage": None,
        "errors": None,
    }

    return ApiResponse(
        data=metrics,
        meta=ResponseMeta(request_id=request_id),
    )


@router.get(
    "/workspaces/{workspace_id}/analytics/activity",
    status_code=status.HTTP_200_OK,
    summary="Get recent activity",
    description="Retrieve recent documents and conversations for the workspace.",
)
async def get_analytics_activity(
    workspace_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    request_id: str = getattr(request.state, "request_id", "unknown")

    await verify_workspace_access(workspace_id, current_user.id, db)

    # Fetch 5 most recent documents
    recent_docs_stmt = (
        select(Document)
        .where(Document.workspace_id == workspace_id)
        .order_by(Document.created_at.desc())
        .limit(5)
    )
    docs_result = await db.execute(recent_docs_stmt)
    documents = [
        {
            "id": str(d.id),
            "filename": d.filename,
            "status": d.status,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs_result.scalars().all()
    ]

    # Fetch 5 most recent conversations
    recent_conv_stmt = (
        select(Conversation)
        .where(Conversation.workspace_id == workspace_id)
        .order_by(Conversation.created_at.desc())
        .limit(5)
    )
    conv_result = await db.execute(recent_conv_stmt)
    conversations = [
        {
            "id": str(c.id),
            "title": c.title,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        }
        for c in conv_result.scalars().all()
    ]

    return ApiResponse(
        data={
            "recent_documents": documents,
            "recent_conversations": conversations,
        },
        meta=ResponseMeta(request_id=request_id),
    )

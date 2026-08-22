"""
Chat conversation REST API routes.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_workspace_role
from app.exceptions import ForbiddenError, NotFoundError
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.routes.auth import get_current_user
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    PaginatedConversationResponse,
    PaginatedMessageResponse,
)
from app.services.chat.service import ChatService

router = APIRouter(tags=["Conversations"])


class ConversationRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="New conversation title")


@router.post(
    "/workspaces/{workspace_id}/conversations",
    status_code=status.HTTP_201_CREATED,
    response_model=ConversationResponse,
    summary="Create a new conversation",
)
async def create_conversation(
    workspace_id: uuid.UUID,
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    _member: WorkspaceMember = Depends(require_workspace_role(["owner", "admin", "member"])),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    service = ChatService(db)
    return await service.create_conversation(workspace_id, current_user.id, payload)


@router.get(
    "/workspaces/{workspace_id}/conversations",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedConversationResponse,
    summary="List conversations in a workspace",
)
async def list_conversations(
    workspace_id: uuid.UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    _member: WorkspaceMember = Depends(require_workspace_role(["owner", "admin", "member"])),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    service = ChatService(db)
    items, total = await service.get_conversations(workspace_id, current_user.id, page, size)

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "has_more": (page * size) < total,
    }


@router.get(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_200_OK,
    response_model=ConversationResponse,
    summary="Get a single conversation",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    service = ChatService(db)
    return await service.get_conversation(conversation_id, current_user.id)


@router.patch(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_200_OK,
    response_model=ConversationResponse,
    summary="Rename a conversation",
)
async def rename_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationRename,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    service = ChatService(db)
    return await service.rename_conversation(conversation_id, current_user.id, payload.title)


@router.get(
    "/conversations/{conversation_id}/messages",
    status_code=status.HTTP_200_OK,
    response_model=PaginatedMessageResponse,
    summary="List conversation messages",
)
async def list_messages(
    conversation_id: uuid.UUID,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    service = ChatService(db)
    items, total = await service.get_messages(conversation_id, current_user.id, page, size)

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "has_more": (page * size) < total,
    }


@router.post(
    "/conversations/{conversation_id}/messages",
    status_code=status.HTTP_200_OK,
    summary="Send a message and stream RAG response",
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    request_id: str = getattr(request.state, "request_id", "unknown")
    service = ChatService(db)

    return StreamingResponse(
        service.stream_rag_chat(conversation_id, current_user.id, payload.content),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id,
        },
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation and all its messages",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ChatService(db)
    await service.delete_conversation(conversation_id, current_user.id)

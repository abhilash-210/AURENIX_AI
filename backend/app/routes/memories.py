"""
AI Memory REST API routes.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.routes.auth import get_current_user
from app.services.memory.schemas import MemoryResponse
from app.services.memory.service import MemoryService

router = APIRouter(tags=["Memory"])


@router.get(
    "/workspaces/{workspace_id}/memories",
    status_code=status.HTTP_200_OK,
    response_model=list[MemoryResponse],
    summary="List all memories for a workspace and user",
)
async def list_memories(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MemoryResponse]:
    service = MemoryService(db)
    # Get both workspace scoped and user scoped memories
    memories = await service.get_memories(workspace_id=workspace_id, user_id=current_user.id)
    return memories


@router.delete(
    "/memories/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a specific memory",
)
async def delete_memory(
    memory_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = MemoryService(db)
    await service.delete_memory(memory_id, current_user.id)

"""
Workspace REST API routes.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.routes.auth import get_current_user
from app.schemas.common import ApiResponse, ResponseMeta

router = APIRouter(tags=["Workspaces"])


@router.get(
    "/workspaces",
    status_code=status.HTTP_200_OK,
    summary="List user workspaces",
    description="Retrieve all workspaces the user belongs to. Creates a default workspace if none exist.",
)
async def list_workspaces(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[dict[str, Any]]]:
    request_id: str = getattr(request.state, "request_id", "unknown")

    # Fetch existing workspaces for the user
    stmt = (
        select(Workspace)
        .join(WorkspaceMember)
        .where(WorkspaceMember.user_id == current_user.id)
        .where(Workspace.is_active == True)
    )
    result = await db.execute(stmt)
    workspaces = result.scalars().all()

    if not workspaces:
        # Create a default workspace if the user has none
        new_workspace = Workspace(
            name="My Workspace",
            slug=f"workspace-{uuid.uuid4().hex[:8]}",
            description="Default workspace",
        )
        db.add(new_workspace)
        await db.flush()

        member = WorkspaceMember(
            workspace_id=new_workspace.id,
            user_id=current_user.id,
            role="owner",
        )
        db.add(member)
        await db.flush()
        
        workspaces = [new_workspace]

    items = [
        {
            "id": w.id,
            "name": w.name,
            "slug": w.slug,
            "description": w.description,
        }
        for w in workspaces
    ]

    return ApiResponse(
        data=items,
        meta=ResponseMeta(request_id=request_id),
    )

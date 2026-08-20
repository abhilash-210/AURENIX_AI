"""
Workspace REST API routes.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.exceptions import NotFoundError, ForbiddenError
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.routes.auth import get_current_user
from app.dependencies import require_workspace_role, get_workspace_member
from app.services.audit.service import AuditService
from app.schemas.common import ApiResponse, ResponseMeta

router = APIRouter(tags=["Workspaces"])


class WorkspaceSettingsUpdate(BaseModel):
    max_documents: int | None = None
    max_messages: int | None = None


class MemberRoleUpdate(BaseModel):
    role: str


@router.get(
    "/workspaces",
    status_code=status.HTTP_200_OK,
    summary="List user workspaces",
)
async def list_workspaces(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[dict[str, Any]]]:
    request_id: str = getattr(request.state, "request_id", "unknown")

    stmt = (
        select(Workspace)
        .join(WorkspaceMember)
        .where(WorkspaceMember.user_id == current_user.id)
        .where(Workspace.is_active == True)
    )
    result = await db.execute(stmt)
    workspaces = result.scalars().all()

    if not workspaces:
        new_workspace = Workspace(
            name="My Workspace",
            slug=f"workspace-{uuid.uuid4().hex[:8]}",
            description="Default workspace",
            settings={"max_documents": 100, "max_messages": 1000},
        )
        db.add(new_workspace)
        await db.flush()

        member = WorkspaceMember(
            workspace_id=new_workspace.id,
            user_id=current_user.id,
            role="owner",
        )
        db.add(member)
        await db.commit()
        
        workspaces = [new_workspace]

    items = [
        {
            "id": w.id,
            "name": w.name,
            "slug": w.slug,
            "description": w.description,
            "settings": w.settings,
        }
        for w in workspaces
    ]

    return ApiResponse(data=items, meta=ResponseMeta(request_id=request_id))


@router.get(
    "/workspaces/{workspace_id}/members",
    status_code=status.HTTP_200_OK,
    summary="List workspace members",
)
async def list_members(
    workspace_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    member: WorkspaceMember = Depends(require_workspace_role(["admin", "owner"])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[dict[str, Any]]]:
    request_id: str = getattr(request.state, "request_id", "unknown")

    stmt = (
        select(WorkspaceMember)
        .options(selectinload(WorkspaceMember.user))
        .where(WorkspaceMember.workspace_id == workspace_id)
    )
    result = await db.execute(stmt)
    members = result.scalars().all()

    items = [
        {
            "user_id": str(m.user.id),
            "email": m.user.email,
            "full_name": m.user.full_name,
            "role": m.role,
            "joined_at": m.joined_at.isoformat(),
        }
        for m in members
    ]

    return ApiResponse(data=items, meta=ResponseMeta(request_id=request_id))


@router.patch(
    "/workspaces/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Update member role",
)
async def update_member_role(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    data: MemberRoleUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    caller_member: WorkspaceMember = Depends(require_workspace_role(["admin", "owner"])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    request_id: str = getattr(request.state, "request_id", "unknown")

    if data.role not in ["owner", "admin", "member"]:
        raise ValueError("Invalid role.")
        
    if caller_member.role == "admin" and data.role == "owner":
        raise ForbiddenError("Admins cannot promote members to owner.")

    stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    )
    result = await db.execute(stmt)
    target_member = result.scalar_one_or_none()

    if not target_member:
        raise NotFoundError("Member not found in workspace.")
        
    if target_member.role == "owner" and caller_member.role != "owner":
        raise ForbiddenError("Only owners can modify other owners.")

    target_member.role = data.role
    await db.commit()
    
    audit_service = AuditService(db)
    await audit_service.log_action(
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="member.role_updated",
        resource_type="WorkspaceMember",
        resource_id=str(user_id),
        details={"new_role": data.role},
    )

    return ApiResponse(data={"status": "success"}, meta=ResponseMeta(request_id=request_id))


@router.delete(
    "/workspaces/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from the workspace",
)
async def remove_member(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    caller_member: WorkspaceMember = Depends(require_workspace_role(["admin", "owner"])),
    db: AsyncSession = Depends(get_db),
) -> None:
    stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    )
    result = await db.execute(stmt)
    target_member = result.scalar_one_or_none()

    if not target_member:
        raise NotFoundError("Member not found in workspace.")
        
    if target_member.role == "owner" and caller_member.role != "owner":
        raise ForbiddenError("Admins cannot remove owners.")

    await db.delete(target_member)
    await db.commit()
    
    audit_service = AuditService(db)
    await audit_service.log_action(
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="member.removed",
        resource_type="WorkspaceMember",
        resource_id=str(user_id),
        details={},
    )


@router.put(
    "/workspaces/{workspace_id}/settings",
    status_code=status.HTTP_200_OK,
    summary="Update workspace settings",
)
async def update_settings(
    workspace_id: uuid.UUID,
    data: WorkspaceSettingsUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    caller_member: WorkspaceMember = Depends(require_workspace_role(["admin", "owner"])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    request_id: str = getattr(request.state, "request_id", "unknown")

    stmt = select(Workspace).where(Workspace.id == workspace_id)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise NotFoundError("Workspace not found.")
        
    new_settings = dict(workspace.settings)
    if data.max_documents is not None:
        new_settings["max_documents"] = data.max_documents
    if data.max_messages is not None:
        new_settings["max_messages"] = data.max_messages
        
    workspace.settings = new_settings
    await db.commit()
    
    audit_service = AuditService(db)
    await audit_service.log_action(
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="workspace.settings_updated",
        resource_type="Workspace",
        resource_id=str(workspace_id),
        details=new_settings,
    )

    return ApiResponse(data=workspace.settings, meta=ResponseMeta(request_id=request_id))

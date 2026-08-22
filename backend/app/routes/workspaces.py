"""
Workspace REST API routes.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.exceptions import NotFoundError, ForbiddenError
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.document import Document, DocumentChunk
from app.models.chat import Conversation, Message
from app.models.memory import Memory
from app.routes.auth import get_current_user
from app.dependencies import require_workspace_role, get_workspace_member
from app.services.audit.service import AuditService
from app.schemas.common import ApiResponse, ResponseMeta

router = APIRouter(tags=["Workspaces"])


# ── Request/Response schemas ──────────────────────────────────────────────────

class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Workspace name")
    description: str | None = Field(default=None, max_length=1000)


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)


class WorkspaceSettingsUpdate(BaseModel):
    max_documents: int | None = None
    max_messages: int | None = None


class MemberRoleUpdate(BaseModel):
    role: str


def _workspace_to_dict(w: Workspace) -> dict[str, Any]:
    return {
        "id": str(w.id),
        "name": w.name,
        "slug": w.slug,
        "description": w.description,
        "settings": w.settings,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }


# ── Workspace CRUD ─────────────────────────────────────────────────────────────

@router.post(
    "/workspaces",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
)
async def create_workspace(
    data: WorkspaceCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    request_id: str = getattr(request.state, "request_id", "unknown")

    slug = f"{data.name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
    workspace = Workspace(
        name=data.name,
        slug=slug,
        description=data.description,
        settings={"max_documents": 100, "max_messages": 1000},
    )
    db.add(workspace)
    await db.flush()

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role="owner",
    )
    db.add(member)
    await db.commit()
    await db.refresh(workspace)

    audit_service = AuditService(db)
    await audit_service.log_action(
        workspace_id=workspace.id,
        user_id=current_user.id,
        action="workspace.created",
        resource_type="Workspace",
        resource_id=str(workspace.id),
        details={"name": workspace.name},
    )

    return ApiResponse(data=_workspace_to_dict(workspace), meta=ResponseMeta(request_id=request_id))


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
        .order_by(Workspace.created_at.asc())
    )
    result = await db.execute(stmt)
    workspaces = result.scalars().all()

    # Auto-create default workspace for brand new users
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

    return ApiResponse(
        data=[_workspace_to_dict(w) for w in workspaces],
        meta=ResponseMeta(request_id=request_id),
    )


@router.get(
    "/workspaces/{workspace_id}",
    status_code=status.HTTP_200_OK,
    summary="Get a single workspace",
)
async def get_workspace(
    workspace_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    request_id: str = getattr(request.state, "request_id", "unknown")

    # Authorization: user must be a member
    stmt = select(WorkspaceMember).where(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()
    if not member:
        raise ForbiddenError("You do not have access to this workspace.")

    ws_stmt = select(Workspace).where(Workspace.id == workspace_id, Workspace.is_active == True)
    ws_result = await db.execute(ws_stmt)
    workspace = ws_result.scalar_one_or_none()
    if not workspace:
        raise NotFoundError("Workspace not found.")

    return ApiResponse(data=_workspace_to_dict(workspace), meta=ResponseMeta(request_id=request_id))


@router.patch(
    "/workspaces/{workspace_id}",
    status_code=status.HTTP_200_OK,
    summary="Rename or update workspace",
)
async def update_workspace(
    workspace_id: uuid.UUID,
    data: WorkspaceUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    caller_member: WorkspaceMember = Depends(require_workspace_role(["admin", "owner"])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    request_id: str = getattr(request.state, "request_id", "unknown")

    stmt = select(Workspace).where(Workspace.id == workspace_id, Workspace.is_active == True)
    result = await db.execute(stmt)
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise NotFoundError("Workspace not found.")

    if data.name is not None:
        workspace.name = data.name
    if data.description is not None:
        workspace.description = data.description

    await db.commit()
    await db.refresh(workspace)

    audit_service = AuditService(db)
    await audit_service.log_action(
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="workspace.updated",
        resource_type="Workspace",
        resource_id=str(workspace_id),
        details=data.model_dump(exclude_none=True),
    )

    return ApiResponse(data=_workspace_to_dict(workspace), meta=ResponseMeta(request_id=request_id))


@router.delete(
    "/workspaces/{workspace_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a workspace and all its data",
)
async def delete_workspace(
    workspace_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    caller_member: WorkspaceMember = Depends(require_workspace_role(["owner"])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    """
    Permanently deletes a workspace and cascades deletion to:
    1. All document chunks
    2. All documents
    3. All messages (via conversation cascade)
    4. All conversations
    5. All memories
    6. All workspace members
    7. Qdrant vectors (best-effort)
    8. The workspace record itself
    """
    request_id: str = getattr(request.state, "request_id", "unknown")

    # Verify workspace exists
    ws_stmt = select(Workspace).where(Workspace.id == workspace_id, Workspace.is_active == True)
    ws_result = await db.execute(ws_stmt)
    workspace = ws_result.scalar_one_or_none()
    if not workspace:
        raise NotFoundError("Workspace not found.")

    # Gather summary counts for the response
    doc_count_stmt = select(Document).where(Document.workspace_id == workspace_id)
    doc_result = await db.execute(doc_count_stmt)
    docs = doc_result.scalars().all()
    doc_count = len(docs)

    conv_count_stmt = select(Conversation).where(Conversation.workspace_id == workspace_id)
    conv_result = await db.execute(conv_count_stmt)
    conversations = conv_result.scalars().all()
    conv_ids = [c.id for c in conversations]
    conv_count = len(conv_ids)

    msg_count = 0
    if conv_ids:
        msg_stmt = select(Message).where(Message.conversation_id.in_(conv_ids))
        msg_result = await db.execute(msg_stmt)
        messages = msg_result.scalars().all()
        msg_count = len(messages)

    # 1. Delete document chunks
    chunk_del = delete(DocumentChunk).where(
        DocumentChunk.document_id.in_([d.id for d in docs])
    )
    if docs:
        await db.execute(chunk_del)

    # 2. Delete documents
    await db.execute(delete(Document).where(Document.workspace_id == workspace_id))

    # 3. Delete messages then conversations
    if conv_ids:
        await db.execute(delete(Message).where(Message.conversation_id.in_(conv_ids)))
    await db.execute(delete(Conversation).where(Conversation.workspace_id == workspace_id))

    # 4. Delete memories
    await db.execute(delete(Memory).where(Memory.workspace_id == workspace_id))

    # 5. Hard-delete the workspace (cascade will remove workspace_members)
    await db.delete(workspace)
    await db.commit()

    # 6. Qdrant cleanup (best-effort, non-blocking)
    try:
        from app.services.vector_store.service import VectorStoreService
        vss = VectorStoreService()
        await vss.delete_workspace_vectors(str(workspace_id))
    except Exception:
        pass  # Qdrant offline in dev mode — vectors will be cleaned on next startup

    return ApiResponse(
        data={
            "deleted": True,
            "workspace_id": str(workspace_id),
            "summary": {
                "documents_deleted": doc_count,
                "conversations_deleted": conv_count,
                "messages_deleted": msg_count,
            },
        },
        meta=ResponseMeta(request_id=request_id),
    )


# ── Member management ─────────────────────────────────────────────────────────

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

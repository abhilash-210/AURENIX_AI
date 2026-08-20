"""
API Key management routes.
"""
from __future__ import annotations

import secrets
import uuid
import hashlib
from typing import Any
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.exceptions import NotFoundError
from app.models.api_key import ApiKey
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.routes.auth import get_current_user
from app.dependencies import require_workspace_role
from app.services.audit.service import AuditService
from app.schemas.common import ApiResponse, ResponseMeta

router = APIRouter(tags=["API Keys"])


class ApiKeyCreate(BaseModel):
    name: str
    expires_in_days: int | None = 365


def generate_api_key() -> tuple[str, str, str]:
    """Generate a raw key, its hash, and prefix."""
    raw_key = "sk-aur-" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    prefix = raw_key[:12] + "..."
    return raw_key, key_hash, prefix


@router.get(
    "/workspaces/{workspace_id}/api-keys",
    status_code=status.HTTP_200_OK,
    summary="List workspace API keys",
)
async def list_api_keys(
    workspace_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    member: WorkspaceMember = Depends(require_workspace_role(["admin", "owner"])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[dict[str, Any]]]:
    request_id: str = getattr(request.state, "request_id", "unknown")

    stmt = select(ApiKey).where(ApiKey.workspace_id == workspace_id).order_by(ApiKey.created_at.desc())
    result = await db.execute(stmt)
    keys = result.scalars().all()

    items = [
        {
            "id": str(k.id),
            "name": k.name,
            "prefix": k.key_prefix,
            "created_at": k.created_at.isoformat(),
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "is_active": k.is_active,
        }
        for k in keys
    ]

    return ApiResponse(data=items, meta=ResponseMeta(request_id=request_id))


@router.post(
    "/workspaces/{workspace_id}/api-keys",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
)
async def create_api_key(
    workspace_id: uuid.UUID,
    data: ApiKeyCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    member: WorkspaceMember = Depends(require_workspace_role(["admin", "owner"])),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    request_id: str = getattr(request.state, "request_id", "unknown")

    raw_key, key_hash, prefix = generate_api_key()
    
    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)

    api_key = ApiKey(
        workspace_id=workspace_id,
        created_by_id=current_user.id,
        name=data.name,
        key_hash=key_hash,
        key_prefix=prefix,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    audit_service = AuditService(db)
    await audit_service.log_action(
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="api_key.created",
        resource_type="ApiKey",
        resource_id=str(api_key.id),
        details={"name": api_key.name},
    )

    return ApiResponse(
        data={
            "id": str(api_key.id),
            "name": api_key.name,
            "raw_key": raw_key, # Displayed ONCE
            "prefix": api_key.key_prefix,
            "created_at": api_key.created_at.isoformat(),
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        },
        meta=ResponseMeta(request_id=request_id),
    )


@router.delete(
    "/workspaces/{workspace_id}/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
)
async def delete_api_key(
    workspace_id: uuid.UUID,
    key_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    member: WorkspaceMember = Depends(require_workspace_role(["admin", "owner"])),
    db: AsyncSession = Depends(get_db),
) -> None:
    stmt = select(ApiKey).where(ApiKey.id == key_id, ApiKey.workspace_id == workspace_id)
    result = await db.execute(stmt)
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise NotFoundError("API key not found.")

    await db.delete(api_key)
    await db.commit()
    
    audit_service = AuditService(db)
    await audit_service.log_action(
        workspace_id=workspace_id,
        user_id=current_user.id,
        action="api_key.deleted",
        resource_type="ApiKey",
        resource_id=str(api_key.id),
        details={"name": api_key.name},
    )

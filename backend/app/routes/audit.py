"""
Audit logging routes.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.routes.auth import get_current_user
from app.dependencies import require_workspace_role
from app.schemas.common import ApiResponse, ResponseMeta

router = APIRouter(tags=["Audit Logs"])


@router.get(
    "/workspaces/{workspace_id}/audit-logs",
    status_code=status.HTTP_200_OK,
    summary="List workspace audit logs",
)
async def list_audit_logs(
    workspace_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    member: WorkspaceMember = Depends(require_workspace_role(["admin", "owner"])),
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    size: int = 50,
) -> ApiResponse[list[dict[str, Any]]]:
    request_id: str = getattr(request.state, "request_id", "unknown")

    offset = (page - 1) * size
    stmt = (
        select(AuditLog)
        .where(AuditLog.workspace_id == workspace_id)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    items = [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]

    return ApiResponse(data=items, meta=ResponseMeta(request_id=request_id))

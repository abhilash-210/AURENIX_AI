"""
Common FastAPI dependencies for RBAC and Workspace access control.
"""
import uuid
from typing import Callable, Sequence

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import ForbiddenError, NotFoundError
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.routes.auth import get_current_user

async def get_workspace_member(
    workspace_id: uuid.UUID, 
    user_id: uuid.UUID, 
    db: AsyncSession
) -> WorkspaceMember:
    """Fetch the WorkspaceMember association, raising NotFound if not found or inactive."""
    stmt = (
        select(WorkspaceMember)
        .join(Workspace)
        .where(
            Workspace.id == workspace_id,
            WorkspaceMember.user_id == user_id,
            Workspace.is_active == True,
        )
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    if not member:
        raise NotFoundError(f"Workspace '{workspace_id}' not found.")
    
    return member

def require_workspace_role(allowed_roles: Sequence[str]) -> Callable:
    """
    Dependency factory to enforce workspace RBAC.
    """
    async def dependency(
        workspace_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> WorkspaceMember:
        member = await get_workspace_member(workspace_id, current_user.id, db)
        
        if member.role not in allowed_roles:
            raise ForbiddenError(f"Requires one of roles: {allowed_roles}")
            
        return member
        
    return dependency

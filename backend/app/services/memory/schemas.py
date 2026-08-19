"""
AI Memory Pydantic schemas.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.memory import MemoryScope


class MemoryCreate(BaseModel):
    scope: MemoryScope
    content: str
    workspace_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None


class MemoryResponse(BaseModel):
    id: uuid.UUID
    scope: MemoryScope
    content: str
    workspace_id: uuid.UUID | None
    user_id: uuid.UUID | None
    conversation_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemoryExtractionResult(BaseModel):
    memories: list[str] = Field(description="A list of distinct facts or preferences worth remembering.")

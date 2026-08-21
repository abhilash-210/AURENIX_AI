"""
Conversation and Message schemas.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.services.rag.schemas import Citation


class ConversationBase(BaseModel):
    title: str = Field(default="New Conversation", max_length=255)


class ConversationCreate(ConversationBase):
    pass


class ConversationResponse(ConversationBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageBase(BaseModel):
    content: str


class MessageCreate(MessageBase):
    pass


class MessageResponse(MessageBase):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    citations: list[Citation] | list[dict[str, Any]] | None = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("citations", mode="before")
    @classmethod
    def set_citations(cls, v: Any) -> list[Any]:
        return v if v is not None else []


class PaginatedMessageResponse(BaseModel):
    items: list[MessageResponse]
    total: int
    page: int
    size: int
    has_more: bool


class PaginatedConversationResponse(BaseModel):
    items: list[ConversationResponse]
    total: int
    page: int
    size: int
    has_more: bool

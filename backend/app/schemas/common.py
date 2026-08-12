"""
Pydantic schemas — common response envelopes used across all endpoints.

Every successful response is wrapped in ApiResponse[T].
Every error response is wrapped in ErrorResponse.

These mirror the contracts defined in docs/api-design.md §3 and §11.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ──────────────────────────────────────────────────────────────────────────────
# Shared field types
# ──────────────────────────────────────────────────────────────────────────────

RequestId = Annotated[
    str,
    Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request ID"),
]

ISOTimestamp = Annotated[
    datetime,
    Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description="ISO-8601 UTC timestamp",
    ),
]


# ──────────────────────────────────────────────────────────────────────────────
# Response meta block
# ──────────────────────────────────────────────────────────────────────────────


class ResponseMeta(BaseModel):
    """Metadata attached to every successful API response."""

    request_id: RequestId
    timestamp: ISOTimestamp


# ──────────────────────────────────────────────────────────────────────────────
# Success envelope
# ──────────────────────────────────────────────────────────────────────────────


class ApiResponse(BaseModel, Generic[T]):
    """
    Standard success envelope.

    Example::

        {
          "data": { ... },
          "meta": {
            "request_id": "uuid",
            "timestamp": "2026-08-12T17:00:00Z"
          }
        }
    """

    data: T
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


# ──────────────────────────────────────────────────────────────────────────────
# Error envelope
# ──────────────────────────────────────────────────────────────────────────────


class ErrorDetail(BaseModel):
    """Inner error object returned on failure."""

    code: str = Field(description="Machine-readable error code (upper-snake-case)")
    message: str = Field(description="Human-readable error description")
    request_id: RequestId
    timestamp: ISOTimestamp


class ErrorResponse(BaseModel):
    """
    Standard error envelope.

    Example::

        {
          "error": {
            "code": "NOT_FOUND",
            "message": "Resource does not exist.",
            "request_id": "uuid",
            "timestamp": "2026-08-12T17:00:00Z"
          }
        }
    """

    error: ErrorDetail

    @classmethod
    def from_exception(
        cls,
        *,
        code: str,
        message: str,
        request_id: str | None = None,
    ) -> "ErrorResponse":
        """Factory method to build an ErrorResponse from exception metadata."""
        return cls(
            error=ErrorDetail(
                code=code,
                message=message,
                request_id=request_id or str(uuid.uuid4()),
            )
        )

"""
Pydantic schemas for authentication endpoints.

Security design:
  - ``UserResponse`` explicitly lists safe fields only — ``hashed_password``
    is intentionally absent so it can never accidentally leak to a client.
  - ``RegisterRequest`` enforces a minimum password length of 8 characters
    at the schema level so invalid payloads are rejected before any DB call.
  - ``LoginRequest`` uses plain ``str`` for the password (not SecretStr) to
    keep JSON parsing simple; the value never persists beyond the request.
  - Email addresses are normalised to lowercase to prevent duplicate accounts
    like ``User@Example.COM`` vs ``user@example.com``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


# ──────────────────────────────────────────────────────────────────────────────
# Request schemas
# ──────────────────────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    """Payload for POST /api/v1/auth/register."""

    email: EmailStr = Field(
        description="A valid email address that will be used to log in.",
        examples=["alice@example.com"],
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Plain-text password (min 8, max 128 characters). Stored as bcrypt hash.",
        examples=["s3cur3P@ssw0rd"],
    )
    full_name: str | None = Field(
        default=None,
        max_length=255,
        description="Optional display name shown in the UI.",
        examples=["Alice Smith"],
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        """Lower-case the email so alice@Example.COM == alice@example.com."""
        return value.strip().lower()


class LoginRequest(BaseModel):
    """Payload for POST /api/v1/auth/login."""

    email: EmailStr = Field(
        description="The email address used during registration.",
        examples=["alice@example.com"],
    )
    password: str = Field(
        description="The account password.",
        examples=["s3cur3P@ssw0rd"],
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        return value.strip().lower()


# ──────────────────────────────────────────────────────────────────────────────
# Response schemas
# ──────────────────────────────────────────────────────────────────────────────


class UserResponse(BaseModel):
    """
    Public view of a user account.

    IMPORTANT: ``hashed_password`` is deliberately excluded — it must
    never appear in any API response.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
    role: str
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    """JWT token payload returned on successful authentication."""

    access_token: str = Field(description="Signed HS256 JWT.")
    token_type: str = Field(default="bearer", description="Always 'bearer'.")
    expires_in: int = Field(
        description="Token lifetime in seconds.",
        examples=[1800],
    )


class LoginResponse(BaseModel):
    """Combined token + user data returned on POST /api/v1/auth/login."""

    token: TokenResponse
    user: UserResponse

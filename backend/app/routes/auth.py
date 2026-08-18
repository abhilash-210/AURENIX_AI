"""
Authentication router — POST /register, POST /login, GET /me.

Security notes:
  - Registration emails are normalised to lower-case by the schema validator.
  - Login returns the same generic 401 for both "email not found" and "wrong
    password" to prevent user enumeration attacks.
  - ``get_current_user`` extracts the Bearer token from the Authorization
    header, validates it with the auth service, then loads the User from DB.
  - ``require_role`` is a dependency factory for basic role-based access
    control on any protected endpoint.

All endpoints follow the standard ``ApiResponse[T]`` envelope defined in
``app/schemas/common.py``.
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.exceptions import AuthenticationError, ConflictError, ForbiddenError
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import ApiResponse
from app.services.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# OAuth2 scheme — tells FastAPI where to look for the Bearer token.
# ``tokenUrl`` points at the login endpoint so Swagger UI renders a usable
# "Authorize" button.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ──────────────────────────────────────────────────────────────────────────────
# Shared dependencies
# ──────────────────────────────────────────────────────────────────────────────


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    FastAPI dependency that resolves the caller's identity from a Bearer JWT.

    Raises:
        AuthenticationError (401): token missing, malformed, expired, or the
                                   user no longer exists / is inactive.
    """
    payload = decode_access_token(token)  # raises AuthenticationError on failure
    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Token is missing user identity.")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError as exc:
        raise AuthenticationError("Token contains an invalid user ID.") from exc

    user = await db.get(User, user_id)
    if user is None:
        raise AuthenticationError("User account no longer exists.")
    if not user.is_active:
        raise AuthenticationError("User account is deactivated.")

    return user


# Type alias for cleaner signatures
CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):  # noqa: ANN201
    """
    Dependency factory that enforces one or more global roles.

    Usage::

        @router.delete("/admin/users/{id}")
        async def delete_user(
            _: User = Depends(require_role("owner", "admin")),
        ):
            ...

    Raises:
        ForbiddenError (403): if the authenticated user's role is not in ``roles``.
    """

    async def checker(current_user: CurrentUser) -> User:
        if current_user.is_superuser:
            return current_user  # superuser bypasses all role checks
        if current_user.role not in roles:
            raise ForbiddenError(
                f"This action requires one of the following roles: {', '.join(roles)}."
            )
        return current_user

    return checker


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────


@router.post(
    "/register",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    responses={
        201: {"description": "Account created successfully"},
        409: {"description": "Email already registered"},
        422: {"description": "Validation error (e.g. weak password)"},
    },
)
async def register(
    body: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[UserResponse]:
    """
    Create a new user account.

    - Email is normalised to lower-case.
    - Password is hashed with bcrypt before being stored.
    - Returns the new user's public profile (no password hash).
    """
    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError(f"An account with email '{body.email}' already exists.")

    user = User(
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.flush()   # populate user.id without committing the transaction
    await db.refresh(user)

    logger.info("New user registered", extra={"user_id": str(user.id)})

    return ApiResponse(data=UserResponse.model_validate(user))


@router.post(
    "/login",
    response_model=ApiResponse[LoginResponse],
    summary="Authenticate and receive a JWT",
    responses={
        200: {"description": "Login successful"},
        401: {"description": "Invalid credentials"},
    },
)
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[LoginResponse]:
    """
    Exchange email + password for a signed JWT access token.

    The same 401 is returned for both "email not found" and "wrong password"
    to prevent user enumeration via timing or error message differences.
    """
    _INVALID_MSG = "Invalid email or password."

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    # Deliberate constant-time path: always call verify_password so that the
    # response time doesn't reveal whether the email exists.
    # _DUMMY_HASH is a valid bcrypt hash of a random string — passlib needs a
    # properly formatted hash to run its constant-time comparison without error.
    _DUMMY_HASH = "$2b$12$KIXeATVPEPMBpNEQGZxZMeGabrTzuN6jWbIHKqJqbQGGAFJCDnFNS"
    stored_hash = user.hashed_password if user else _DUMMY_HASH

    if not verify_password(body.password, stored_hash) or user is None:
        raise AuthenticationError(_INVALID_MSG)

    if not user.is_active:
        raise AuthenticationError("This account has been deactivated.")

    settings = get_settings()
    token_str = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role},
    )

    token = TokenResponse(
        access_token=token_str,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )

    logger.info("User logged in", extra={"user_id": str(user.id)})

    return ApiResponse(
        data=LoginResponse(
            token=token,
            user=UserResponse.model_validate(user),
        )
    )


@router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
    summary="Return the current authenticated user",
    responses={
        200: {"description": "Current user's profile"},
        401: {"description": "Missing or invalid token"},
    },
)
async def me(current_user: CurrentUser) -> ApiResponse[UserResponse]:
    """
    Return the public profile of the caller.

    Requires a valid Bearer JWT in the ``Authorization`` header.
    """
    return ApiResponse(data=UserResponse.model_validate(current_user))

"""
Authentication service for Aurenix AI.

Responsibilities:
  - Secure password hashing and verification via passlib / bcrypt.
  - JWT creation and validation via python-jose.
  - Stateless: no database calls.  All DB access lives in routes.

Security notes:
  - Passwords are hashed with bcrypt (work factor ≥ 12, auto-tuned by passlib).
  - JWTs are signed HS256 using the ``JWT_SECRET_KEY`` setting (SecretStr).
  - The ``exp`` claim is always set; tokens without it are rejected.
  - Validation errors are translated to ``AuthenticationError`` so the
    global exception handler returns 401 consistently.

Public API:
    hash_password(plain)             -> str
    verify_password(plain, hashed)   -> bool
    create_access_token(subject, **) -> str
    decode_access_token(token)       -> dict[str, Any]
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings
from app.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

# Bcrypt work factor (number of rounds). 12 is the recommended minimum;
# higher values are slower but more resistant to brute-force attacks.
_BCRYPT_ROUNDS: int = 12


def hash_password(plain: str) -> str:
    """
    Return a bcrypt hash of ``plain``.

    Uses bcrypt directly (passlib 1.7.4 is not compatible with bcrypt ≥.0).
    The work factor and salt are embedded in the returned hash string.
    """
    password_bytes = plain.encode("utf-8")
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Return True if ``plain`` matches the stored ``hashed`` password.

    Uses a constant-time comparison internally — safe against timing attacks.
    """
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:  # noqa: BLE001
        # checkpw raises ValueError for malformed hashes; treat as mismatch.
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a signed HS256 JWT for ``subject`` (typically the user's UUID as str).

    Args:
        subject:      The ``sub`` claim — typically str(user.id).
        extra_claims: Optional additional claims merged into the payload
                      (e.g. ``{"role": "admin"}``).

    Returns:
        A compact JWT string.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    token: str = jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Validate and decode a JWT, returning its payload dict.

    Raises:
        AuthenticationError: if the token is missing, malformed, expired,
                             or has an invalid signature.
    """
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        logger.debug("JWT validation failed: %s", exc)
        raise AuthenticationError("Invalid or expired token.") from exc

    # Reject tokens that lack a subject claim
    if not payload.get("sub"):
        raise AuthenticationError("Token is missing the 'sub' claim.")

    # Reject non-access tokens (e.g. refresh tokens if introduced later)
    if payload.get("type") != "access":
        raise AuthenticationError("Token type is not 'access'.")

    return payload

"""
Centralised exception classes for the Aurenix AI backend.

All domain-level errors inherit from AurenixError, which carries an HTTP
status code and a machine-readable error code string.  The global exception
handler registered in main.py converts these into the standard JSON error
envelope defined in docs/api-design.md §11.

Adding a new error type:
    1. Create a subclass of AurenixError (or one of its children).
    2. Set the class-level ``status_code`` and ``error_code``.
    3. Raise it anywhere in the application.
    4. The global handler in main.py will serialise it automatically.

Error codes must match the table in docs/api-design.md §11.
"""

from __future__ import annotations

from http import HTTPStatus


class AurenixError(Exception):
    """
    Base class for all application-level errors.

    Attributes:
        message:     Human-readable description of the error.
        status_code: HTTP status code to return to the client.
        error_code:  Machine-readable identifier (upper-snake-case string).
    """

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or HTTPStatus(self.status_code).phrase
        super().__init__(self.message)


# ──────────────────────────────────────────────────────────────────────────────
# 4xx — Client errors
# ──────────────────────────────────────────────────────────────────────────────


class ValidationError(AurenixError):
    """Request body failed schema validation (supplement to Pydantic's 422)."""

    status_code = HTTPStatus.BAD_REQUEST
    error_code = "VALIDATION_ERROR"


class NotFoundError(AurenixError):
    """Requested resource does not exist."""

    status_code = HTTPStatus.NOT_FOUND
    error_code = "NOT_FOUND"


class ConflictError(AurenixError):
    """Resource already exists (e.g. duplicate email on registration)."""

    status_code = HTTPStatus.CONFLICT
    error_code = "CONFLICT"


class UnprocessableError(AurenixError):
    """Input is syntactically valid but semantically incorrect."""

    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    error_code = "UNPROCESSABLE"


class RateLimitError(AurenixError):
    """Client has exceeded the allowed request rate."""

    status_code = HTTPStatus.TOO_MANY_REQUESTS
    error_code = "RATE_LIMITED"


# ──────────────────────────────────────────────────────────────────────────────
# 5xx — Server errors
# ──────────────────────────────────────────────────────────────────────────────


class ServiceUnavailableError(AurenixError):
    """An upstream dependency (LLM provider, DB) is temporarily unavailable."""

    status_code = HTTPStatus.SERVICE_UNAVAILABLE
    error_code = "SERVICE_UNAVAILABLE"

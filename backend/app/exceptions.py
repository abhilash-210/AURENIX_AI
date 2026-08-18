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


class AuthenticationError(AurenixError):
    """
    Request is missing valid credentials or the credentials are wrong.

    Maps to HTTP 401.  The global exception handler adds the
    ``WWW-Authenticate: Bearer`` header so OAuth2 clients can discover the
    correct authentication scheme.
    """

    status_code = HTTPStatus.UNAUTHORIZED
    error_code = "AUTHENTICATION_ERROR"


class ForbiddenError(AurenixError):
    """
    The authenticated user lacks the required role or permission.

    Maps to HTTP 403.  Unlike 401, this means the server understood *who*
    the caller is but refuses to authorise the action.
    """

    status_code = HTTPStatus.FORBIDDEN
    error_code = "FORBIDDEN"


# ──────────────────────────────────────────────────────────────────────────────
# 5xx — Server errors
# ──────────────────────────────────────────────────────────────────────────────


class ServiceUnavailableError(AurenixError):
    """An upstream dependency (LLM provider, DB) is temporarily unavailable."""

    status_code = HTTPStatus.SERVICE_UNAVAILABLE
    error_code = "SERVICE_UNAVAILABLE"


# ──────────────────────────────────────────────────────────────────────────────
# LLM Gateway errors
# ──────────────────────────────────────────────────────────────────────────────


class LLMError(AurenixError):
    """Base exception for all LLM gateway failures."""

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    error_code = "LLM_ERROR"


class LLMProviderError(LLMError):
    """Upstream LLM provider returned an error response or failed to respond."""

    status_code = HTTPStatus.BAD_GATEWAY
    error_code = "LLM_PROVIDER_ERROR"


class LLMTimeoutError(LLMError):
    """LLM provider request timed out."""

    status_code = HTTPStatus.GATEWAY_TIMEOUT
    error_code = "LLM_TIMEOUT"


class LLMRateLimitError(LLMError):
    """LLM provider rate limit exceeded."""

    status_code = HTTPStatus.TOO_MANY_REQUESTS
    error_code = "LLM_RATE_LIMITED"


class LLMStructuredOutputError(LLMError):
    """Failed to parse or validate LLM response into requested structured schema."""

    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    error_code = "LLM_STRUCTURED_OUTPUT_ERROR"


# ──────────────────────────────────────────────────────────────────────────────
# Document Ingestion errors
# ──────────────────────────────────────────────────────────────────────────────


class DocumentError(AurenixError):
    """Base exception for document ingestion failures."""

    status_code = HTTPStatus.BAD_REQUEST
    error_code = "DOCUMENT_ERROR"


class UnsupportedFileTypeError(DocumentError):
    """Uploaded file extension or MIME type is not supported."""

    status_code = HTTPStatus.UNSUPPORTED_MEDIA_TYPE
    error_code = "UNSUPPORTED_FILE_TYPE"


class FileTooLargeError(DocumentError):
    """Uploaded file size exceeds configured maximum limit."""

    status_code = HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    error_code = "FILE_TOO_LARGE"


class DocumentParsingError(DocumentError):
    """Failed to parse or extract text from document."""

    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    error_code = "DOCUMENT_PARSING_ERROR"


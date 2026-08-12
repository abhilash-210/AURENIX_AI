"""
Tests for custom exception classes (app.exceptions).

Covers:
  - Each exception carries the correct status_code and error_code
  - The message defaults to the HTTP status phrase when not provided
  - Custom messages are preserved
  - All exceptions inherit from AurenixError
"""

from __future__ import annotations

from http import HTTPStatus

import pytest

from app.exceptions import (
    AurenixError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    UnprocessableError,
    ValidationError,
)


class TestAurenixErrorBase:
    """Base class behaviour."""

    def test_default_status_code(self) -> None:
        err = AurenixError()
        assert err.status_code == 500

    def test_default_error_code(self) -> None:
        err = AurenixError()
        assert err.error_code == "INTERNAL_ERROR"

    def test_custom_message_stored(self) -> None:
        err = AurenixError("Something went wrong")
        assert err.message == "Something went wrong"
        assert str(err) == "Something went wrong"

    def test_default_message_is_http_phrase(self) -> None:
        err = AurenixError()
        assert err.message == HTTPStatus(500).phrase


@pytest.mark.parametrize(
    ("exc_cls", "expected_status", "expected_code"),
    [
        (ValidationError, 400, "VALIDATION_ERROR"),
        (NotFoundError, 404, "NOT_FOUND"),
        (ConflictError, 409, "CONFLICT"),
        (UnprocessableError, 422, "UNPROCESSABLE"),
        (RateLimitError, 429, "RATE_LIMITED"),
        (ServiceUnavailableError, 503, "SERVICE_UNAVAILABLE"),
    ],
)
class TestSpecificExceptions:
    """Each concrete exception has the correct status and code."""

    def test_status_code(
        self,
        exc_cls: type[AurenixError],
        expected_status: int,
        expected_code: str,
    ) -> None:
        assert exc_cls.status_code == expected_status

    def test_error_code(
        self,
        exc_cls: type[AurenixError],
        expected_status: int,
        expected_code: str,
    ) -> None:
        assert exc_cls.error_code == expected_code

    def test_inherits_from_aurenix_error(
        self,
        exc_cls: type[AurenixError],
        expected_status: int,
        expected_code: str,
    ) -> None:
        assert issubclass(exc_cls, AurenixError)

    def test_custom_message_preserved(
        self,
        exc_cls: type[AurenixError],
        expected_status: int,
        expected_code: str,
    ) -> None:
        err = exc_cls("Custom error message")
        assert err.message == "Custom error message"

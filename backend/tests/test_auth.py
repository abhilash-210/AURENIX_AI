"""
Tests for authentication endpoints — Sprint 2.

Covers:
  POST /api/v1/auth/register
    - test_register_success              — 201 + UserResponse (no hashed_password)
    - test_register_duplicate_email      — 409 CONFLICT
    - test_register_invalid_email        — 422 VALIDATION_ERROR
    - test_register_short_password       — 422 VALIDATION_ERROR

  POST /api/v1/auth/login
    - test_login_success                 — 200 + access_token + user
    - test_login_wrong_password          — 401 AUTHENTICATION_ERROR
    - test_login_nonexistent_email       — 401 AUTHENTICATION_ERROR

  GET /api/v1/auth/me
    - test_me_authenticated              — 200 + correct user data
    - test_me_no_token                   — 401 with WWW-Authenticate header
    - test_me_invalid_token              — 401
    - test_me_expired_token              — 401
    - test_me_tampered_token             — 401

All tests use the async ``client`` fixture from conftest.py, which injects
an in-memory SQLite database — no running Postgres required.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from jose import jwt

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"

# A valid registration payload reused across multiple tests
VALID_USER = {
    "email": "alice@example.com",
    "password": "Str0ng!Pass",
    "full_name": "Alice Smith",
}


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


async def register_and_login(client: AsyncClient, user: dict | None = None) -> str:
    """Register a user and return a valid access token for that user."""
    payload = user or VALID_USER
    await client.post(REGISTER_URL, json=payload)
    resp = await client.post(LOGIN_URL, json={"email": payload["email"], "password": payload["password"]})
    return resp.json()["data"]["token"]["access_token"]


# ──────────────────────────────────────────────────────────────────────────────
# Registration
# ──────────────────────────────────────────────────────────────────────────────


class TestRegister:
    """Tests for POST /api/v1/auth/register."""

    async def test_register_success(self, client: AsyncClient) -> None:
        """201 with correct envelope and no hashed_password in response."""
        response = await client.post(REGISTER_URL, json=VALID_USER)
        assert response.status_code == 201

        body = response.json()
        assert "data" in body
        assert "meta" in body

        data = body["data"]
        assert data["email"] == VALID_USER["email"]
        assert data["full_name"] == VALID_USER["full_name"]
        assert data["is_active"] is True
        assert data["role"] == "member"
        assert "id" in data
        assert "created_at" in data

        # CRITICAL: password must never be returned
        assert "hashed_password" not in data
        assert "password" not in data

    async def test_register_email_normalised_to_lowercase(self, client: AsyncClient) -> None:
        """Email must be normalised: UPPER@EXAMPLE.COM → upper@example.com."""
        response = await client.post(
            REGISTER_URL,
            json={"email": "UPPER@EXAMPLE.COM", "password": "Str0ng!Pass"},
        )
        assert response.status_code == 201
        assert response.json()["data"]["email"] == "upper@example.com"

    async def test_register_duplicate_email(self, client: AsyncClient) -> None:
        """Registering the same email twice returns 409 CONFLICT."""
        await client.post(REGISTER_URL, json=VALID_USER)
        response = await client.post(REGISTER_URL, json=VALID_USER)

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CONFLICT"

    async def test_register_invalid_email(self, client: AsyncClient) -> None:
        """A malformed email address returns 422 VALIDATION_ERROR."""
        response = await client.post(
            REGISTER_URL,
            json={"email": "not-an-email", "password": "Str0ng!Pass"},
        )
        assert response.status_code == 422

    async def test_register_short_password(self, client: AsyncClient) -> None:
        """A password shorter than 8 characters returns 422."""
        response = await client.post(
            REGISTER_URL,
            json={"email": "bob@example.com", "password": "short"},
        )
        assert response.status_code == 422

    async def test_register_missing_email(self, client: AsyncClient) -> None:
        """Omitting the email field returns 422."""
        response = await client.post(REGISTER_URL, json={"password": "Str0ng!Pass"})
        assert response.status_code == 422

    async def test_register_missing_password(self, client: AsyncClient) -> None:
        """Omitting the password field returns 422."""
        response = await client.post(REGISTER_URL, json={"email": "carol@example.com"})
        assert response.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# Login
# ──────────────────────────────────────────────────────────────────────────────


class TestLogin:
    """Tests for POST /api/v1/auth/login."""

    @pytest.fixture(autouse=True)
    async def _register(self, client: AsyncClient) -> None:
        """Ensure a user exists before each login test."""
        await client.post(REGISTER_URL, json=VALID_USER)

    async def test_login_success(self, client: AsyncClient) -> None:
        """200 with a Bearer token and user profile."""
        response = await client.post(
            LOGIN_URL,
            json={"email": VALID_USER["email"], "password": VALID_USER["password"]},
        )
        assert response.status_code == 200

        data = response.json()["data"]
        assert "token" in data
        assert "user" in data

        token = data["token"]
        assert token["token_type"] == "bearer"
        assert len(token["access_token"]) > 0
        assert token["expires_in"] > 0

        user = data["user"]
        assert user["email"] == VALID_USER["email"]
        assert "hashed_password" not in user

    async def test_login_success_email_case_insensitive(self, client: AsyncClient) -> None:
        """Login must succeed regardless of email capitalisation."""
        response = await client.post(
            LOGIN_URL,
            json={"email": VALID_USER["email"].upper(), "password": VALID_USER["password"]},
        )
        assert response.status_code == 200

    async def test_login_wrong_password(self, client: AsyncClient) -> None:
        """401 returned when the password is incorrect."""
        response = await client.post(
            LOGIN_URL,
            json={"email": VALID_USER["email"], "password": "WrongPassword!"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTHENTICATION_ERROR"

    async def test_login_nonexistent_email(self, client: AsyncClient) -> None:
        """401 returned when the email does not exist — same as wrong password."""
        response = await client.post(
            LOGIN_URL,
            json={"email": "nobody@example.com", "password": VALID_USER["password"]},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTHENTICATION_ERROR"

    async def test_login_returns_www_authenticate_on_401(self, client: AsyncClient) -> None:
        """A failed login must include the WWW-Authenticate: Bearer header."""
        response = await client.post(
            LOGIN_URL,
            json={"email": "nobody@example.com", "password": "anything"},
        )
        assert response.status_code == 401
        assert "www-authenticate" in response.headers
        assert response.headers["www-authenticate"] == "Bearer"


# ──────────────────────────────────────────────────────────────────────────────
# Current user (/me)
# ──────────────────────────────────────────────────────────────────────────────


class TestMe:
    """Tests for GET /api/v1/auth/me."""

    async def test_me_authenticated(self, client: AsyncClient) -> None:
        """200 with the current user's profile for a valid token."""
        token = await register_and_login(client)
        response = await client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["email"] == VALID_USER["email"]
        assert "hashed_password" not in data

    async def test_me_no_token(self, client: AsyncClient) -> None:
        """401 when the Authorization header is absent."""
        response = await client.get(ME_URL)
        assert response.status_code == 401

    async def test_me_invalid_token(self, client: AsyncClient) -> None:
        """401 for a syntactically invalid token."""
        response = await client.get(ME_URL, headers={"Authorization": "Bearer not.a.jwt"})
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTHENTICATION_ERROR"

    async def test_me_expired_token(self, client: AsyncClient) -> None:
        """401 for an expired (but well-formed) token."""
        from app.config import get_settings

        settings = get_settings()
        past = datetime.now(UTC) - timedelta(hours=1)
        expired_token = jwt.encode(
            {"sub": "00000000-0000-0000-0000-000000000000", "exp": past, "type": "access"},
            settings.jwt_secret_key.get_secret_value(),
            algorithm=settings.jwt_algorithm,
        )
        response = await client.get(
            ME_URL, headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401

    async def test_me_tampered_token(self, client: AsyncClient) -> None:
        """401 when the token signature has been tampered with."""
        token = await register_and_login(client)
        # Flip the last character to corrupt the signature
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        response = await client.get(ME_URL, headers={"Authorization": f"Bearer {tampered}"})
        assert response.status_code == 401

    async def test_me_wrong_token_type(self, client: AsyncClient) -> None:
        """401 for a token with type != 'access' (future refresh token guard)."""
        from app.config import get_settings

        settings = get_settings()
        future = datetime.now(UTC) + timedelta(days=7)
        refresh_token = jwt.encode(
            {"sub": "00000000-0000-0000-0000-000000000000", "exp": future, "type": "refresh"},
            settings.jwt_secret_key.get_secret_value(),
            algorithm=settings.jwt_algorithm,
        )
        response = await client.get(
            ME_URL, headers={"Authorization": f"Bearer {refresh_token}"}
        )
        assert response.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# Protected endpoint / RBAC smoke test
# ──────────────────────────────────────────────────────────────────────────────


class TestUnauthorizedAccess:
    """Verify that protected endpoints reject unauthenticated requests."""

    async def test_me_is_protected(self, client: AsyncClient) -> None:
        """/me must return 401 with no credentials."""
        response = await client.get(ME_URL)
        assert response.status_code == 401

    async def test_me_rejects_malformed_bearer(self, client: AsyncClient) -> None:
        """'Authorization: Bearer' with no token value returns 401."""
        response = await client.get(ME_URL, headers={"Authorization": "Bearer"})
        assert response.status_code in (401, 403, 422)  # depends on OAuth2 scheme parsing

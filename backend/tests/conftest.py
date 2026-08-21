"""
Pytest fixtures shared across the test suite — Sprint 2 revision.

Changes from Sprint 1:
  - Adds an async in-memory SQLite engine that creates all ORM tables once
    per test session.
  - Adds a ``db_session`` fixture that yields an async session and rolls back
    after every test (isolation without re-creating the schema each time).
  - Overrides the ``get_db`` FastAPI dependency so HTTP tests hit the same
    in-memory database.
  - Replaces the synchronous ``TestClient`` with an ``AsyncClient`` so async
    route handlers can be exercised properly via ``httpx``.
  - Keeps the ``APP_ENV=testing`` override so Settings picks the correct env.

Async runtime:
  - pytest-asyncio is configured with ``asyncio_mode = "auto"`` in pyproject.toml
    so all ``async def test_*`` functions run automatically.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

# Force the testing environment BEFORE any app module is imported.
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("LOG_FORMAT", "text")
# Use the 32-char placeholder — long enough to pass the validator
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-at-least-32-chars!!")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


# ──────────────────────────────────────────────────────────────────────────────
# Database fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """
    Create a single in-memory SQLite async engine for the entire test session.

    StaticPool forces SQLite to keep one connection alive so that the tables
    created by ``create_all`` are visible to all subsequent queries (normally
    each ``:memory:`` connection gets an independent database).
    """
    from app.models.base import Base

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async session for a single test; roll back after the test.

    Rolling back instead of committing means each test starts with a clean
    state without recreating the schema (which would be slow).
    """
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


# ──────────────────────────────────────────────────────────────────────────────
# HTTP client fixture
# ──────────────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Yield an async HTTPX client wired to the FastAPI app.

    The ``get_db`` dependency is overridden to inject the test session so
    that route handlers use the same in-memory database as the test code.
    """
    from app.config import get_settings
    from app.database import get_db
    from app.main import create_app

    get_settings.cache_clear()

    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Backwards-compatibility: Sprint 1 sync TestClient
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def test_client():
    """
    Synchronous TestClient for Sprint 1 tests.

    Sprint 1 tests (test_health.py, test_config.py, etc.) use this fixture.
    Sprint 2+ tests use the async ``client`` fixture instead.
    """
    from fastapi.testclient import TestClient

    from app.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


# ──────────────────────────────────────────────────────────────────────────────
# Shared Auth and Workspace Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def async_client(client: AsyncClient) -> AsyncClient:
    """Alias for client fixture for parity with async_client."""
    return client


@pytest_asyncio.fixture
async def auth_user(db_session: AsyncSession):
    """Create a persistent test user."""
    import uuid
    from app.models.user import User
    from app.services.auth import hash_password

    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:6]}@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="Test Enterprise User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def auth_token(auth_user) -> str:
    """Generate a valid JWT access token for auth_user."""
    from app.services.auth import create_access_token
    return create_access_token(subject=str(auth_user.id))


@pytest_asyncio.fixture
async def setup_workspaces(db_session: AsyncSession, auth_user):
    """Create a test workspace and attach auth_user as owner."""
    import uuid
    from app.models.workspace import Workspace, WorkspaceMember

    ws = Workspace(
        id=uuid.uuid4(),
        name="Test Workspace",
        slug=f"test-{uuid.uuid4().hex[:8]}",
        settings={"max_documents": 100, "max_messages": 1000},
    )
    db_session.add(ws)
    await db_session.flush()

    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=auth_user.id,
        role="owner",
    )
    db_session.add(member)
    await db_session.flush()
    return ws, auth_user


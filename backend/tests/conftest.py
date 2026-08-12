"""
Pytest fixtures shared across the test suite.

The ``test_client`` fixture creates an isolated FastAPI app instance per test
session with the environment set to "testing".  This means:
  - No real .env file is read for secrets (APP_ENV overrides it)
  - OpenAPI docs are enabled (non-production)
  - Log format is "text" for readable test output

Async tests use pytest-asyncio (configured as asyncio_mode = "auto" in
pyproject.toml), so ``async def test_*`` functions run automatically.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Force the testing environment BEFORE the app module is imported,
# so Settings picks it up via the environment (not from a .env file).
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("LOG_LEVEL", "WARNING")   # quieter output during tests
os.environ.setdefault("LOG_FORMAT", "text")


@pytest.fixture(scope="session")
def test_client() -> TestClient:
    """
    Return a synchronous TestClient wrapping the FastAPI app.

    Using scope="session" means the app is created once for the entire test
    run, which is acceptable because no shared mutable state exists in Sprint 1.
    Tests that need a fresh app state should create their own client.
    """
    # Import here (after env vars are set) so Settings is initialised correctly
    from app.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()  # discard any cached Settings from earlier imports

    app = create_app()
    return TestClient(app, raise_server_exceptions=False)

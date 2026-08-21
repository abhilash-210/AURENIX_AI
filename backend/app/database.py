"""
Async database engine and session management for Aurenix AI.

Design notes:
  - Uses SQLAlchemy 2.x async API (AsyncEngine + AsyncSession).
  - ``get_db`` is a FastAPI dependency that yields a session per request,
    commits on success, and rolls back automatically on any exception.
  - ``create_db_tables`` is called at application startup to ensure the schema
    exists (useful in development / testing; production should use Alembic).
  - SQLite is supported for local dev and test runs — simply set DATABASE_URL
    to ``sqlite+aiosqlite:///./aurenix_dev.db`` (the default in Settings).

Usage:
    from app.database import get_db

    @router.get("/items")
    async def list_items(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Item))
        return result.scalars().all()
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

logger = logging.getLogger(__name__)


def _build_engine() -> AsyncEngine:
    """
    Construct the async SQLAlchemy engine from application settings.

    SQLite requires ``check_same_thread=False`` because the async driver
    can hand the connection to a different thread.  For PostgreSQL, connection
    pooling parameters (pool_size, max_overflow, pool_recycle) are configured.
    """
    settings = get_settings()
    connect_args: dict[str, Any] = {}
    engine_kwargs: dict[str, Any] = {
        "echo": settings.debug,
        "pool_pre_ping": True,
    }

    if "sqlite" in settings.database_url:
        connect_args["check_same_thread"] = False
    else:
        engine_kwargs["pool_size"] = settings.db_pool_size
        engine_kwargs["max_overflow"] = settings.db_max_overflow
        engine_kwargs["pool_timeout"] = settings.db_pool_timeout
        engine_kwargs["pool_recycle"] = settings.db_pool_recycle

    return create_async_engine(
        settings.database_url,
        connect_args=connect_args,
        **engine_kwargs,
    )


# Module-level engine — shared for the lifetime of the process.
# Tests replace this by overriding the ``get_db`` dependency.
engine: AsyncEngine = _build_engine()

# Session factory — do not instantiate AsyncSession directly.
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # objects remain usable after commit
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: yield an async database session per request.

    Commits the transaction on success; rolls back on any exception so that
    partial writes never persist silently.

    Usage::

        @router.post("/users")
        async def create_user(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_db_tables() -> None:
    """
    Create all tables defined in ``Base.metadata`` if they do not exist.

    Called during application startup in development / testing.
    Production deployments should use ``alembic upgrade head`` instead.
    """
    # Import here to avoid circular imports at module load time
    from app.models.base import Base  # noqa: PLC0415

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ensured")

"""
Alembic environment configuration for Aurenix AI.

This file is executed by Alembic for both ``alembic upgrade`` (online mode)
and ``alembic revision --autogenerate`` (offline mode).

Key design points:
  - The database URL is **always** read from the ``DATABASE_URL`` environment
    variable (or the .env file via pydantic-settings) — never hardcoded.
  - We import ``Base.metadata`` so ``--autogenerate`` can diff the ORM models
    against the live schema.
  - Alembic uses a *synchronous* engine because it does not have native async
    support.  ``config.database_url_sync`` converts the async DSN to its sync
    equivalent (e.g. ``postgresql+asyncpg`` → ``postgresql+psycopg2``).
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Ensure the backend/ package is importable when Alembic is invoked from the
# backend/ directory (i.e. ``alembic -c alembic.ini upgrade head``).
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all models so their tables are registered in Base.metadata.
# This is the only place where models must be explicitly imported for Alembic.
from app.config import get_settings  # noqa: E402
from app.models import Base  # noqa: E402  (also imports User, Workspace, etc.)

# ---------------------------------------------------------------------------
# Alembic Config object — access to alembic.ini values
# ---------------------------------------------------------------------------
config = context.config

# Configure Python logging from the alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Provide the metadata to Alembic for autogenerate support
target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Override the sqlalchemy.url from the application settings so no DSN ever
# needs to be stored in alembic.ini.
# ---------------------------------------------------------------------------
_settings = get_settings()
config.set_main_option("sqlalchemy.url", _settings.database_url_sync)


# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """
    Emit migration SQL to stdout without connecting to the database.

    Useful for generating SQL scripts to review before applying them.
    Run with: ``alembic upgrade head --sql``
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Apply migrations against a live database connection.

    Uses a connection pool that is disposed after the migration run to avoid
    leaving idle connections.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # no pooling — migration is a short-lived process
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,   # detect column type changes in autogenerate
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""
Configuration management for the Aurenix AI backend.

All settings are loaded from environment variables (and an optional .env file).
Pydantic Settings provides automatic type-coercion and validation — the
application will fail fast with a clear error if a required variable is missing
or has the wrong type.

Usage:
    from app.config import get_settings

    settings = get_settings()
    print(settings.app_name)
"""

from __future__ import annotations

import logging
from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Valid runtime environments."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class LogFormat(StrEnum):
    """Log output format choices."""

    JSON = "json"
    TEXT = "text"


class Settings(BaseSettings):
    """
    Application settings, populated from environment variables.

    All variables can be overridden by a `.env` file in the backend directory.
    Refer to `.env.example` for the full list of supported variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # silently ignore unrecognised env vars
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Application
    # ──────────────────────────────────────────────────────────────────────────
    app_env: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Runtime environment (development | production | testing)",
    )
    app_name: str = Field(default="Aurenix AI", description="Application display name")
    app_version: str = Field(default="0.1.0", description="Semantic version string")
    debug: bool = Field(
        default=False,
        description="Enable debug mode (auto-set True in development)",
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Server
    # ──────────────────────────────────────────────────────────────────────────
    host: str = Field(default="0.0.0.0", description="Uvicorn bind host")  # noqa: S104
    port: int = Field(default=8000, ge=1, le=65535, description="Uvicorn bind port")

    # ──────────────────────────────────────────────────────────────────────────
    # CORS
    # ──────────────────────────────────────────────────────────────────────────
    cors_origins: list[str] | str = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins (comma-separated string or JSON list)",
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Database
    # ──────────────────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite+aiosqlite:///./aurenix_dev.db",
        description=(
            "Async SQLAlchemy DSN. Use postgresql+asyncpg://... in production. "
            "Defaults to SQLite for zero-config local development."
        ),
    )

    # ──────────────────────────────────────────────────────────────────────────
    # JWT Authentication
    # ──────────────────────────────────────────────────────────────────────────
    jwt_secret_key: SecretStr = Field(
        default=SecretStr("changeme-replace-in-production"),
        description="HS256 signing secret — must be ≥32 chars. Generate: openssl rand -hex 32",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm (HS256 is the production default)",
    )
    jwt_access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        description="Lifetime of access tokens in minutes",
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        description="Lifetime of refresh tokens in days (used from Sprint 3 onwards)",
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Logging
    # ──────────────────────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Python logging level",
    )
    log_format: LogFormat = Field(
        default=LogFormat.TEXT,
        description="Log output format: 'json' for production, 'text' for development",
    )

    # ──────────────────────────────────────────────────────────────────────────
    # LLM Gateway
    # ──────────────────────────────────────────────────────────────────────────
    llm_provider: str = Field(
        default="openai",
        description="Default LLM provider (openai | anthropic | mock)",
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        description="OpenAI API key (read from OPENAI_API_KEY)",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="Default OpenAI model name",
    )
    openai_api_base: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL",
    )
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        description="Anthropic API key (read from ANTHROPIC_API_KEY)",
    )
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Default Anthropic model name",
    )
    anthropic_api_base: str = Field(
        default="https://api.anthropic.com/v1",
        description="Anthropic API base URL",
    )
    llm_timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        description="Default HTTP timeout for LLM provider requests in seconds",
    )
    llm_max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts for transient LLM errors",
    )
    llm_retry_backoff_factor: float = Field(
        default=0.5,
        ge=0.0,
        description="Exponential backoff multiplier for retries",
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Embeddings
    # ──────────────────────────────────────────────────────────────────────────
    embedding_provider: str = Field(
        default="openai",
        description="Default embedding provider (openai | mock)",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Default embedding model",
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Vector Database (Qdrant)
    # ──────────────────────────────────────────────────────────────────────────
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant server URL",
    )
    qdrant_api_key: SecretStr | None = Field(
        default=None,
        description="Optional Qdrant API key",
    )
    qdrant_collection_name: str = Field(
        default="aurenix_documents",
        description="Name of the main Qdrant collection",
    )
    qdrant_memory_collection_name: str = Field(
        default="aurenix_memories",
        description="Name of the Qdrant collection for semantic memories",
    )

    # ──────────────────────────────────────────────────────────────────────────
    # MCP (Model Context Protocol) Integration
    # ──────────────────────────────────────────────────────────────────────────
    mcp_servers_config: str = Field(
        default="[]",
        description="JSON string defining trusted MCP servers and their allowed tools.",
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Document Ingestion
    # ──────────────────────────────────────────────────────────────────────────
    upload_dir: str = Field(
        default="storage/uploads",
        description="Directory path where uploaded files are stored",
    )
    max_upload_size_mb: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum allowed file upload size in megabytes",
    )
    default_chunk_size: int = Field(
        default=500,
        ge=50,
        le=4000,
        description="Target character length for document text chunks",
    )
    default_chunk_overlap: int = Field(
        default=50,
        ge=0,
        le=1000,
        description="Character overlap between consecutive chunks",
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Derived properties
    # ──────────────────────────────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        """Return True when running in the production environment."""
        return self.app_env == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Return True when running in the development environment."""
        return self.app_env == Environment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        """Return True when running under pytest."""
        return self.app_env == Environment.TESTING

    @property
    def openapi_enabled(self) -> bool:
        """Expose OpenAPI docs only outside of production."""
        return not self.is_production

    @property
    def numeric_log_level(self) -> int:
        """Return the numeric logging level for Python's logging module."""
        return logging.getLevelName(self.log_level)

    @property
    def database_url_sync(self) -> str:
        """
        Synchronous DSN for Alembic (which does not support async drivers).

        Converts ``postgresql+asyncpg`` → ``postgresql+psycopg2`` and
        ``sqlite+aiosqlite`` → ``sqlite`` so Alembic can run migrations
        with a regular synchronous engine.
        """
        url = self.database_url
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg2")
        url = url.replace("sqlite+aiosqlite", "sqlite")
        return url

    # ──────────────────────────────────────────────────────────────────────────
    # Validators
    # ──────────────────────────────────────────────────────────────────────────
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        """
        Accept either a comma-separated string or a JSON array for CORS_ORIGINS.

        This allows the env var to be written as:
            CORS_ORIGINS=http://localhost:3000,https://app.aurenix.ai
        """
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("jwt_secret_key", mode="after")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        """
        Refuse to start in production with the placeholder JWT secret.

        A minimum length of 32 characters is enforced to guarantee adequate
        entropy regardless of environment.
        """
        secret = value.get_secret_value()
        if len(secret) < 32:  # noqa: PLR2004
            msg = "JWT_SECRET_KEY must be at least 32 characters long."
            raise ValueError(msg)
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached application settings singleton.

    Using lru_cache ensures the .env file is read only once during the process
    lifetime. In tests, call ``get_settings.cache_clear()`` after overriding
    environment variables.
    """
    return Settings()

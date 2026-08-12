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

from pydantic import Field, field_validator
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
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins (comma-separated string or JSON list)",
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached application settings singleton.

    Using lru_cache ensures the .env file is read only once during the process
    lifetime. In tests, call ``get_settings.cache_clear()`` after overriding
    environment variables.
    """
    return Settings()

"""
Tests for application configuration (app.config).

Covers:
  - Default values when no env vars are set
  - Environment enum validation
  - CORS origin parsing from comma-separated string
  - Derived property: is_production
  - Derived property: openapi_enabled
"""

from __future__ import annotations

import pytest

from app.config import Environment, Settings


class TestSettingsDefaults:
    """Settings constructed with no env vars use sensible defaults."""

    def test_default_app_env_is_development(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # conftest sets APP_ENV=testing globally; isolate this test
        monkeypatch.delenv("APP_ENV", raising=False)
        s = Settings()
        assert s.app_env == Environment.DEVELOPMENT

    def test_default_app_name(self) -> None:
        s = Settings()
        assert s.app_name == "Aurenix AI"

    def test_default_port_is_8000(self) -> None:
        s = Settings()
        assert s.port == 8000

    def test_default_debug_is_false(self) -> None:
        s = Settings()
        assert s.debug is False

    def test_default_log_level_is_info(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # conftest sets LOG_LEVEL=WARNING globally; isolate this test
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        s = Settings()
        assert s.log_level == "INFO"


class TestSettingsValidation:
    """Settings raise errors for invalid values."""

    def test_invalid_environment_raises(self) -> None:
        with pytest.raises(Exception):
            Settings(app_env="invalid_env")  # type: ignore[arg-type]

    def test_port_below_range_raises(self) -> None:
        with pytest.raises(Exception):
            Settings(port=0)

    def test_port_above_range_raises(self) -> None:
        with pytest.raises(Exception):
            Settings(port=99999)


class TestCorsOriginParsing:
    """CORS_ORIGINS can be a comma-separated string or a list."""

    def test_comma_separated_string_is_parsed(self) -> None:
        s = Settings(cors_origins="http://localhost:3000,https://app.aurenix.ai")  # type: ignore[arg-type]
        assert s.cors_origins == ["http://localhost:3000", "https://app.aurenix.ai"]

    def test_list_passthrough(self) -> None:
        origins = ["http://localhost:3000", "https://app.aurenix.ai"]
        s = Settings(cors_origins=origins)
        assert s.cors_origins == origins

    def test_whitespace_is_stripped(self) -> None:
        s = Settings(cors_origins="  http://localhost:3000 ,  http://localhost:3001  ")  # type: ignore[arg-type]
        assert s.cors_origins == ["http://localhost:3000", "http://localhost:3001"]


class TestDerivedProperties:
    """Derived boolean properties reflect the correct environment."""

    def test_is_production_true_in_production(self) -> None:
        s = Settings(app_env=Environment.PRODUCTION)
        assert s.is_production is True
        assert s.is_development is False

    def test_is_development_true_in_development(self) -> None:
        s = Settings(app_env=Environment.DEVELOPMENT)
        assert s.is_development is True
        assert s.is_production is False

    def test_openapi_disabled_in_production(self) -> None:
        s = Settings(app_env=Environment.PRODUCTION)
        assert s.openapi_enabled is False

    def test_openapi_enabled_in_development(self) -> None:
        s = Settings(app_env=Environment.DEVELOPMENT)
        assert s.openapi_enabled is True

    def test_openapi_enabled_in_testing(self) -> None:
        s = Settings(app_env=Environment.TESTING)
        assert s.openapi_enabled is True

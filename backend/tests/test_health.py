"""
Tests for GET /api/v1/health.

Covers:
  - Happy path: 200 response with correct envelope structure
  - Correct content-type header
  - Required fields present in data payload
  - Environment and version values come from Settings
  - X-Request-ID header is present on the response
  - OpenAPI schema includes the endpoint (docs enabled in testing env)
"""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for GET /api/v1/health."""

    ENDPOINT = "/api/v1/health"

    # ── Status and structure ──────────────────────────────────────────────────

    def test_returns_200(self, test_client: TestClient) -> None:
        """Health endpoint must return HTTP 200."""
        response = test_client.get(self.ENDPOINT)
        assert response.status_code == 200

    def test_content_type_is_json(self, test_client: TestClient) -> None:
        """Response must be JSON."""
        response = test_client.get(self.ENDPOINT)
        assert "application/json" in response.headers["content-type"]

    def test_response_has_data_and_meta(self, test_client: TestClient) -> None:
        """Top-level keys must be 'data' and 'meta' (standard envelope)."""
        body = test_client.get(self.ENDPOINT).json()
        assert "data" in body
        assert "meta" in body

    # ── data payload ─────────────────────────────────────────────────────────

    def test_data_has_required_fields(self, test_client: TestClient) -> None:
        """data must include status, version, environment, and services."""
        data = test_client.get(self.ENDPOINT).json()["data"]
        assert "status" in data
        assert "version" in data
        assert "environment" in data
        assert "services" in data

    def test_status_is_ok(self, test_client: TestClient) -> None:
        """Nominal health status must be 'ok'."""
        data = test_client.get(self.ENDPOINT).json()["data"]
        assert data["status"] == "ok"

    def test_environment_is_testing(self, test_client: TestClient) -> None:
        """Environment must match APP_ENV=testing set in conftest."""
        data = test_client.get(self.ENDPOINT).json()["data"]
        assert data["environment"] == "testing"

    def test_version_is_non_empty_string(self, test_client: TestClient) -> None:
        """Version must be a non-empty string."""
        data = test_client.get(self.ENDPOINT).json()["data"]
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    def test_services_is_dict(self, test_client: TestClient) -> None:
        """services must be a dict (empty in Sprint 1, populated later)."""
        data = test_client.get(self.ENDPOINT).json()["data"]
        assert isinstance(data["services"], dict)

    # ── meta block ───────────────────────────────────────────────────────────

    def test_meta_has_request_id(self, test_client: TestClient) -> None:
        """meta.request_id must be a non-empty string."""
        meta = test_client.get(self.ENDPOINT).json()["meta"]
        assert "request_id" in meta
        assert isinstance(meta["request_id"], str)
        assert len(meta["request_id"]) > 0

    def test_meta_has_timestamp(self, test_client: TestClient) -> None:
        """meta.timestamp must be an ISO-8601 string."""
        meta = test_client.get(self.ENDPOINT).json()["meta"]
        assert "timestamp" in meta
        # A valid ISO timestamp will contain 'T' and end with 'Z' or '+...'
        assert "T" in meta["timestamp"]

    # ── Response headers ─────────────────────────────────────────────────────

    def test_x_request_id_header_present(self, test_client: TestClient) -> None:
        """Middleware must attach X-Request-ID to every response."""
        response = test_client.get(self.ENDPOINT)
        assert "x-request-id" in response.headers

    def test_x_request_id_is_uuid_format(self, test_client: TestClient) -> None:
        """X-Request-ID must look like a UUID (36 chars with hyphens)."""
        response = test_client.get(self.ENDPOINT)
        request_id = response.headers["x-request-id"]
        # UUID v4 format: 8-4-4-4-12 hex chars separated by hyphens
        parts = request_id.split("-")
        assert len(parts) == 5

    def test_each_request_gets_unique_request_id(
        self, test_client: TestClient
    ) -> None:
        """Every request must receive a distinct X-Request-ID."""
        id_1 = test_client.get(self.ENDPOINT).headers["x-request-id"]
        id_2 = test_client.get(self.ENDPOINT).headers["x-request-id"]
        assert id_1 != id_2

    # ── OpenAPI schema ────────────────────────────────────────────────────────

    def test_endpoint_appears_in_openapi_schema(
        self, test_client: TestClient
    ) -> None:
        """Health endpoint must be declared in the generated OpenAPI spec."""
        schema = test_client.get("/openapi.json").json()
        paths = schema.get("paths", {})
        assert self.ENDPOINT in paths
        assert "get" in paths[self.ENDPOINT]


class TestNotFoundHandling:
    """Verify that unknown routes return a proper 404 JSON response."""

    def test_unknown_route_returns_404(self, test_client: TestClient) -> None:
        """Requesting a non-existent route must return 404."""
        response = test_client.get("/api/v1/does-not-exist")
        assert response.status_code == 404

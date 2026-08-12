"""
Schemas for the health endpoint.

Defines the structure of the response returned by GET /api/v1/health.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ServiceStatus(StrEnum):
    """Health state of an individual service dependency."""

    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


class DependencyHealth(BaseModel):
    """Health status of a single downstream dependency."""

    status: ServiceStatus = Field(description="Current health state")
    latency_ms: float | None = Field(
        default=None,
        description="Round-trip latency in milliseconds (None if not measured)",
    )


class HealthResponse(BaseModel):
    """
    Response body for GET /api/v1/health.

    Future sprints will populate the ``services`` dict with real connectivity
    checks (PostgreSQL, Redis, ChromaDB).  In Sprint 1 the application reports
    its own liveness only.
    """

    status: ServiceStatus = Field(description="Overall system health")
    version: str = Field(description="Application version from settings")
    environment: str = Field(description="Runtime environment name")
    services: dict[str, DependencyHealth] = Field(
        default_factory=dict,
        description="Health of individual downstream services (populated in later sprints)",
    )

"""
Health check router — GET /api/v1/health.

This is the only endpoint implemented in Sprint 1.  Its purpose is to:
  1. Confirm the application process is alive and accepting requests.
  2. Report the current environment and version.
  3. Provide a scaffold for downstream dependency health checks (Sprint 1b+).

The endpoint is intentionally public (no auth required) so that load balancers
and orchestrators can probe it without credentials.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.common import ApiResponse
from app.schemas.health import HealthResponse, ServiceStatus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=ApiResponse[HealthResponse],
    summary="System health check",
    description=(
        "Returns the liveness status of the application and, in future sprints, "
        "the health of downstream services (database, cache, vector store)."
    ),
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "One or more dependencies are unavailable"},
    },
)
async def health_check() -> ApiResponse[HealthResponse]:
    """
    Return the current health of the Aurenix AI backend.

    Sprint 1 reports application liveness only.  Downstream service checks
    (PostgreSQL, Redis, ChromaDB) will be added when those services are
    introduced in subsequent sprints.
    """
    settings = get_settings()

    logger.debug("Health check requested", extra={"endpoint": "/api/v1/health"})

    health = HealthResponse(
        status=ServiceStatus.OK,
        version=settings.app_version,
        environment=settings.app_env.value,
        services={},  # populated in later sprints
    )

    return ApiResponse(data=health)

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
import time

from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.schemas.common import ApiResponse
from app.schemas.health import DependencyHealth, HealthResponse, ServiceStatus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=ApiResponse[HealthResponse],
    summary="System health check",
    description=(
        "Returns the liveness status of the application and the health of "
        "downstream dependencies (database, storage, vector store)."
    ),
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "One or more dependencies are unavailable"},
    },
)
async def health_check() -> ApiResponse[HealthResponse]:
    """
    Return the current health of the Aurenix AI backend and its dependencies.
    """
    settings = get_settings()
    services: dict[str, DependencyHealth] = {}
    overall_status = ServiceStatus.OK

    # ── Database Health Probe ─────────────────────────────────────────────────
    db_start = time.perf_counter()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_latency = (time.perf_counter() - db_start) * 1000.0
        services["database"] = DependencyHealth(
            status=ServiceStatus.OK,
            latency_ms=round(db_latency, 2),
        )
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        services["database"] = DependencyHealth(
            status=ServiceStatus.DOWN,
            latency_ms=None,
        )
        overall_status = ServiceStatus.DEGRADED

    health = HealthResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.app_env.value,
        services=services,
    )

    return ApiResponse(data=health)


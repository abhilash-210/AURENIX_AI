"""
Aurenix AI — FastAPI application factory.

This module is the single entry point for the application.  It:
  1. Configures structured logging via configure_logging().
  2. Creates the FastAPI instance with OpenAPI metadata.
  3. Registers CORS middleware.
  4. Registers the request logging middleware.
  5. Registers global exception handlers for AurenixError and Pydantic's
     RequestValidationError, converting them to the standard error envelope.
  6. Mounts the versioned API router under /api/v1.
  7. Exposes the ``app`` object that uvicorn loads.

Running locally:
    uvicorn app.main:app --reload --port 8000

Production (via Docker):
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import create_db_tables, engine
from app.exceptions import AurenixError, AuthenticationError, ForbiddenError
from app.logging_config import configure_logging
from app.middleware.logging import RequestLoggingMiddleware
from app.routes import auth, chat, conversations, documents, health, memories, rag, workspaces, analytics
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Lifespan — startup / shutdown
# ──────────────────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
    """
    Manage application lifecycle events.

    Startup tasks (before ``yield``):
        - Configure logging so all subsequent log calls use the correct format.
        - Future sprints: initialise DB connection pool, vector store client, etc.

    Shutdown tasks (after ``yield``):
        - Future sprints: gracefully close connection pools.
    """
    settings = get_settings()

    # Must be the first call — configures the root logger before anything else
    configure_logging(
        level=settings.log_level,
        fmt=settings.log_format.value,
    )

    logger.info(
        "Aurenix AI starting",
        extra={
            "version": settings.app_version,
            "environment": settings.app_env.value,
        },
    )

    # Create DB tables on startup (dev/test convenience).
    # Production deployments should use ``alembic upgrade head`` instead.
    await create_db_tables()

    yield  # application is running

    # Gracefully close the async connection pool on shutdown
    await engine.dispose()
    logger.info("Aurenix AI shutting down")


# ──────────────────────────────────────────────────────────────────────────────
# Application factory
# ──────────────────────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    """
    Build and configure the FastAPI application.

    Returns a fully-configured app instance.  Extracting this into a factory
    function (rather than module-level code) makes it trivial to create
    isolated app instances in tests.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Aurenix AI — Enterprise Intelligence Operating System. "
            "Modular, agentic, production-grade."
        ),
        docs_url="/docs" if settings.openapi_enabled else None,
        redoc_url="/redoc" if settings.openapi_enabled else None,
        openapi_url="/openapi.json" if settings.openapi_enabled else None,
        lifespan=lifespan,
    )

    # ── Middleware (outermost first) ──────────────────────────────────────────

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RequestLoggingMiddleware)

    # ── Exception handlers ────────────────────────────────────────────────────

    @app.exception_handler(AurenixError)
    async def aurenix_error_handler(
        request: Request,
        exc: AurenixError,
    ) -> JSONResponse:
        """Convert any AurenixError into the standard error envelope."""
        request_id: str = getattr(request.state, "request_id", "unknown")

        logger.warning(
            "Application error: %s",
            exc.message,
            extra={
                "request_id": request_id,
                "error_code": exc.error_code,
                "status_code": exc.status_code,
            },
        )

        body = ErrorResponse.from_exception(
            code=exc.error_code,
            message=exc.message,
            request_id=request_id,
        )

        headers: dict[str, str] = {}
        if isinstance(exc, AuthenticationError):
            headers["WWW-Authenticate"] = "Bearer"

        return JSONResponse(
            status_code=exc.status_code,
            content=body.model_dump(mode="json"),
            headers=headers or None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Convert Pydantic validation errors into the standard error envelope."""
        request_id: str = getattr(request.state, "request_id", "unknown")

        # Build a concise human-readable summary of the validation failures
        errors = exc.errors()
        detail = "; ".join(
            f"{' → '.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in errors
        )

        logger.warning(
            "Request validation failed",
            extra={"request_id": request_id, "detail": detail},
        )

        body = ErrorResponse.from_exception(
            code="VALIDATION_ERROR",
            message=f"Request validation failed: {detail}",
            request_id=request_id,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=body.model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Catch-all handler — prevents stack traces leaking to clients."""
        request_id: str = getattr(request.state, "request_id", "unknown")

        logger.exception(
            "Unhandled exception",
            extra={"request_id": request_id},
            exc_info=exc,
        )

        body = ErrorResponse.from_exception(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred. Please try again later.",
            request_id=request_id,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=body.model_dump(mode="json"),
        )

    # ── Routers ───────────────────────────────────────────────────────────────

    API_PREFIX = "/api/v1"

    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(auth.router, prefix=API_PREFIX)
    app.include_router(chat.router, prefix=API_PREFIX)
    app.include_router(conversations.router, prefix=API_PREFIX)
    app.include_router(documents.router, prefix=API_PREFIX)
    app.include_router(memories.router, prefix=API_PREFIX)
    app.include_router(rag.router, prefix=API_PREFIX)
    app.include_router(workspaces.router, prefix=API_PREFIX)
    app.include_router(analytics.router, prefix=API_PREFIX)

    return app


# ──────────────────────────────────────────────────────────────────────────────
# Module-level app instance (loaded by uvicorn)
# ──────────────────────────────────────────────────────────────────────────────

app = create_app()

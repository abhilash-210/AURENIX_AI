"""
Request/response logging middleware.

Attaches a unique ``request_id`` (UUID v4) to every incoming request and logs:
  - On request arrival:  method, path, client IP
  - On response completion: method, path, status code, duration in ms

The ``request_id`` is also set as a response header (``X-Request-ID``) so
clients and load balancers can correlate logs.

All log records are emitted at INFO level in production and DEBUG in development,
using the structured logger configured in ``app.logging_config``.
"""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that logs every HTTP request/response pair.

    Adds:
        - ``request_id`` query attribute on the Request state object
        - ``X-Request-ID`` header on the Response
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()

        logger.info(
            "Request received",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": self._get_client_ip(request),
            },
        )

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """
        Extract the real client IP, honouring X-Forwarded-For when present.

        X-Forwarded-For is trusted only if the application is behind a reverse
        proxy (nginx, load balancer).  In production, ensure the proxy is
        configured to set this header correctly.
        """
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

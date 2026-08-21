"""
Sliding Window Token Bucket Rate Limiting Middleware for FastAPI.

Protects authentication endpoints, LLM routes, and background jobs
from denial-of-service and runaway token consumption.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


class RateLimiter:
    """In-memory sliding window rate limiter."""

    def __init__(self, requests_per_minute: int = 120, window_seconds: int = 60) -> None:
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self._clients: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_key: str) -> tuple[bool, int, float]:
        """
        Check whether the client request is within the rate limit.

        Returns:
            (allowed: bool, remaining_quota: int, retry_after_seconds: float)
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Clean timestamps outside sliding window
        timestamps = [t for t in self._clients[client_key] if t > window_start]
        self._clients[client_key] = timestamps

        if len(timestamps) < self.requests_per_minute:
            self._clients[client_key].append(now)
            remaining = self.requests_per_minute - len(self._clients[client_key])
            return True, remaining, 0.0

        # Rate limited: calculate time until the oldest request expires
        oldest_ts = timestamps[0]
        retry_after = max(1.0, (oldest_ts + self.window_seconds) - now)
        return False, 0, round(retry_after, 1)

    def clear(self) -> None:
        """Reset all rate limiter tracking."""
        self._clients.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware applying rate limits per client IP or API key.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 120,
        whitelist_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.limiter = RateLimiter(requests_per_minute=requests_per_minute)
        self.whitelist_paths = set(whitelist_paths or ["/api/v1/health", "/docs", "/openapi.json"])

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip whitelisted health and documentation endpoints
        if request.url.path in self.whitelist_paths:
            return await call_next(request)

        # Extract client identifier: Authorization header token or client IP
        auth_header = request.headers.get("Authorization", "")
        api_key_header = request.headers.get("X-API-Key", "")
        client_ip = request.client.host if request.client else "unknown"

        client_key = api_key_header or (auth_header[:32] if auth_header else client_ip)

        allowed, remaining, retry_after = self.limiter.is_allowed(client_key)

        if not allowed:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(
                "Rate limit exceeded for client: %s (retry after %.1fs)",
                client_ip,
                retry_after,
                extra={"client": client_ip, "path": request.url.path},
            )

            err = ErrorResponse.from_exception(
                code="RATE_LIMITED",
                message=f"Rate limit exceeded. Please retry after {int(retry_after)} seconds.",
                request_id=request_id,
            )

            headers = {
                "Retry-After": str(int(retry_after)),
                "X-RateLimit-Limit": str(self.limiter.requests_per_minute),
                "X-RateLimit-Remaining": "0",
            }
            return JSONResponse(
                status_code=429,
                content=err.model_dump(mode="json"),
                headers=headers,
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

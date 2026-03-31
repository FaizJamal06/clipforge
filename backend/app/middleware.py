"""
ClipForge AI — Security Middleware

FastAPI middleware for rate limiting, security headers, and API key auth.
"""

import time
import logging
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate Limiter (in-memory sliding window, per IP)
# ---------------------------------------------------------------------------

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limiting using a sliding window counter.

    Tracks request timestamps in memory. No Redis required.
    Configurable via settings: rate_limit_per_minute, rate_limit_burst.
    """

    def __init__(self, app):
        super().__init__(app)
        # {ip: [timestamp, timestamp, ...]}
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._settings = get_settings()

    def _cleanup_old(self, ip: str, now: float):
        """Remove timestamps older than the window (60 seconds)."""
        window = 60.0
        self._requests[ip] = [
            ts for ts in self._requests[ip] if now - ts < window
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and docs
        path = request.url.path
        if path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        # Get client IP (respect X-Forwarded-For for proxied deployments)
        client_ip = request.headers.get(
            "X-Forwarded-For", request.client.host if request.client else "unknown"
        )
        # Take first IP if comma-separated
        client_ip = client_ip.split(",")[0].strip()

        now = time.time()
        self._cleanup_old(client_ip, now)

        limit = self._settings.rate_limit_per_minute
        recent = self._requests[client_ip]

        # Check burst: more than burst_limit in last 2 seconds
        burst_limit = self._settings.rate_limit_burst
        burst_window = [ts for ts in recent if now - ts < 2.0]
        if len(burst_window) >= burst_limit:
            logger.warning(f"Rate limit BURST exceeded for IP {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down.",
                    "retry_after": 2,
                },
                headers={"Retry-After": "2"},
            )

        # Check per-minute limit
        if len(recent) >= limit:
            logger.warning(f"Rate limit exceeded for IP {client_ip}: {len(recent)}/{limit} req/min")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": 60,
                },
                headers={"Retry-After": "60"},
            )

        # Record this request
        self._requests[client_ip].append(now)

        return await call_next(request)


# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard security headers to all HTTP responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # HSTS — only in production (when debug is off)
        settings = get_settings()
        if not settings.debug:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

        return response


# ---------------------------------------------------------------------------
# API Key Authentication (optional)
# ---------------------------------------------------------------------------

# Paths that skip API key validation
_PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Optional API key validation via X-API-Key header.

    If no API keys are configured in settings, this middleware is a no-op
    (all requests pass through). When keys are configured, requests without
    a valid key receive 401 Unauthorized.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()

        # If no API keys configured, skip auth entirely
        if not settings.api_keys:
            return await call_next(request)

        # Skip auth for public paths
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        # Check for API key
        api_key = request.headers.get("X-API-Key", "")

        if api_key not in settings.api_keys:
            logger.warning(
                f"Unauthorized API request from {request.client.host if request.client else 'unknown'}"
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key."},
            )

        return await call_next(request)

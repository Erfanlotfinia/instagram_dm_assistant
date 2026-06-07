from __future__ import annotations

import logging
import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings, get_settings
from app.core.metrics import HTTP_REQUEST_DURATION
from app.core.request_context import new_request_id, set_request_context

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or new_request_id()
        ip_address = request.headers.get("X-Forwarded-For")
        if ip_address:
            ip_address = ip_address.split(",")[0].strip()
        elif request.client:
            ip_address = request.client.host

        ctx = set_request_context(
            request_id=request_id,
            ip_address=ip_address,
            user_agent=request.headers.get("User-Agent"),
        )
        request.state.request_id = ctx.request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        path = request.url.path
        HTTP_REQUEST_DURATION.labels(request.method, path).observe(duration)

        response.headers["X-Request-ID"] = ctx.request_id
        logger.info(
            "request completed method=%s path=%s status=%s duration_ms=%.1f",
            request.method,
            path,
            response.status_code,
            duration * 1000,
            extra={"request_id": ctx.request_id},
        )
        return response


class SecureHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings | None = None) -> None:
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        if self.settings.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response

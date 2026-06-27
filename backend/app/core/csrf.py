from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
EXEMPT_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/webhooks",
)


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in UNSAFE and request.cookies.get("__Host-modira_access"):
            if not any(request.url.path.startswith(prefix) for prefix in EXEMPT_PREFIXES):
                cookie = request.cookies.get("modira_csrf")
                header = request.headers.get("x-csrf-token")
                if not cookie or not header or cookie != header:
                    return JSONResponse({"detail": "CSRF validation failed"}, status_code=403)
        return await call_next(request)

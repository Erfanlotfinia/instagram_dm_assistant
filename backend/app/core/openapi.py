from __future__ import annotations

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

SWAGGER_AUTH_GUIDE = """
## Manual API testing (Swagger)

Modira uses **HttpOnly cookies** in the browser admin app, but Swagger works best with **Bearer JWT**.

### Recommended flow (Bearer)

1. Call **`POST /api/v1/auth/login?token_only=true`** with your email and password.
2. Copy **`access_token`** from the JSON response (do **not** use the cookie flow in Swagger).
3. Click **Authorize** → **BearerAuth** → paste the token (without the `Bearer` prefix).
4. Call any protected endpoint. Mutating requests do **not** need a CSRF header when you use Bearer only.

`token_only=true` skips session cookies so Swagger requests are not blocked by CSRF checks.

### Browser cookie flow (optional)

If you log in without `token_only`, the API sets cookies and **POST/PUT/PATCH/DELETE** require
header **`X-CSRF-Token`** matching the **`modira_csrf`** cookie. Use **CsrfToken** in Authorize
with the cookie value, and enable credentials in your HTTP client. Prefer the Bearer flow above in Swagger.

### Token lifetime

Access tokens expire after the configured JWT TTL (default 15 minutes). Repeat step 1–3 when requests return `401`.
"""

PUBLIC_OPERATIONS: set[tuple[str, str]] = {
    ("post", "/api/v1/auth/login"),
    ("post", "/api/v1/auth/refresh"),
    ("get", "/health"),
    ("get", "/ready"),
    ("get", "/api/v1/health"),
    ("get", "/api/v1/ready"),
    ("get", "/api/v1/metrics"),
}

PUBLIC_PATH_PREFIXES = (
    "/api/v1/payments/mock/",
)


def _operation_is_public(method: str, path: str) -> bool:
    key = (method.lower(), path)
    if key in PUBLIC_OPERATIONS:
        return True
    if any(path.startswith(prefix) for prefix in PUBLIC_PATH_PREFIXES):
        return True
    if path.startswith("/api/v1/channels/") and path.endswith("/webhook"):
        return True
    if path.startswith("/api/v1/webhooks/"):
        return True
    return False


def configure_openapi(app: FastAPI) -> None:
    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=SWAGGER_AUTH_GUIDE,
            routes=app.routes,
        )

        components = openapi_schema.setdefault("components", {})
        components["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": (
                    "JWT from `POST /api/v1/auth/login?token_only=true`. "
                    "Paste the `access_token` value only."
                ),
            },
            "CsrfToken": {
                "type": "apiKey",
                "in": "header",
                "name": "X-CSRF-Token",
                "description": (
                    "Required for cookie-based sessions on POST/PUT/PATCH/DELETE. "
                    "Value must match the `modira_csrf` cookie. Not needed for Bearer-only auth."
                ),
            },
        }

        for path, path_item in openapi_schema.get("paths", {}).items():
            for method, operation in path_item.items():
                if method.lower() not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                    continue
                if not isinstance(operation, dict):
                    continue
                if _operation_is_public(method, path):
                    operation["security"] = []
                else:
                    operation["security"] = [{"BearerAuth": []}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.errors import add_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware, SecureHeadersMiddleware
from app.core.csrf import CSRFMiddleware
from app.core.openapi import configure_openapi

settings = get_settings()
configure_logging(settings)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Multi-channel Catalog Commerce Assistant API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        swagger_ui_parameters={
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "withCredentials": False,
        },
    )

    app.add_middleware(SecureHeadersMiddleware, settings=settings)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Hub-Signature-256", "X-CSRF-Token"],
    )

    add_exception_handlers(app)
    app.include_router(v1_router, prefix="/api/v1")

    from app.api.v1.health import health as root_health_check, ready as readiness_check

    app.add_api_route("/health", root_health_check, methods=["GET"], tags=["health"])
    app.add_api_route("/ready", readiness_check, methods=["GET"], tags=["health"])

    if not settings.is_production:
        configure_openapi(app)

    return app


app = create_app()

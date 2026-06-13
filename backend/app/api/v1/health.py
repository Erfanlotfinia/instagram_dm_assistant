from __future__ import annotations

import logging
from typing import Any, Literal

import pika
import redis
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.config import get_settings
from app.core.metrics import metrics_response
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

CheckStatus = Literal["ok", "error"]


def _normalize_check(result: dict[str, Any]) -> CheckStatus:
    return "ok" if result.get("status") == "ok" else "error"


def _check_postgres() -> dict[str, Any]:
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Postgres health check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


def _check_redis() -> dict[str, Any]:
    settings = get_settings()
    try:
        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        client.ping()
        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis health check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


def _check_rabbitmq() -> dict[str, Any]:
    settings = get_settings()
    try:
        connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
        connection.close()
        return {"status": "ok"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("RabbitMQ health check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


def _check_qdrant() -> dict[str, Any]:
    settings = get_settings()
    try:
        import urllib.request

        with urllib.request.urlopen(f"{settings.qdrant_url.rstrip('/')}/healthz", timeout=3) as resp:
            if resp.status == 200:
                return {"status": "ok"}
            return {"status": "error", "detail": f"HTTP {resp.status}"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Qdrant health check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


def _check_openai_config() -> dict[str, Any]:
    settings = get_settings()
    if settings.llm_api_key_configured:
        return {"status": "ok", "provider": settings.llm_provider}
    provider = settings.llm_provider
    key_name = "GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY"
    return {"status": "error", "detail": f"{key_name} is not configured", "provider": provider}


def build_readiness_payload() -> tuple[str, dict[str, CheckStatus], bool]:
    raw_checks = {
        "postgres": _check_postgres(),
        "redis": _check_redis(),
        "rabbitmq": _check_rabbitmq(),
        "qdrant": _check_qdrant(),
        "openai_config": _check_openai_config(),
    }
    checks: dict[str, CheckStatus] = {
        name: _normalize_check(result) for name, result in raw_checks.items()
    }
    postgres_ok = checks["postgres"] == "ok"
    all_ok = all(value == "ok" for value in checks.values())
    if not postgres_ok:
        overall = "failed"
    elif all_ok:
        overall = "ok"
    else:
        overall = "degraded"
    return overall, checks, all_ok


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(response: Response) -> dict[str, Any]:
    overall, checks, _all_ok = build_readiness_payload()
    if overall == "failed":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": overall, "checks": checks}


@router.get("/metrics")
def metrics() -> Response:
    body, content_type = metrics_response()
    return Response(content=body, media_type=content_type)

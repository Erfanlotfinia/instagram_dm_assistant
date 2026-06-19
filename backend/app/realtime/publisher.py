"""Fire-and-forget realtime event publishing over Redis pub/sub.

Producers (API handlers, workers) call :func:`publish_event` to broadcast an
event for a shop. The WebSocket endpoint subscribes to the same channel and
relays events to connected operators. All failures are swallowed so realtime
never blocks the request path — the frontend falls back to polling.
"""
from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


def shop_channel(shop_id: UUID | str) -> str:
    return f"realtime:shop:{shop_id}"


def _get_client() -> redis.Redis | None:
    global _client
    if _client is None:
        try:
            _client = redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
        except Exception:  # pragma: no cover - defensive
            logger.warning("Realtime publisher could not initialise Redis client", exc_info=True)
            return None
    return _client


def publish_event(shop_id: UUID | str, event_type: str, payload: dict[str, Any] | None = None) -> None:
    """Publish a realtime event. Never raises."""
    client = _get_client()
    if client is None:
        return
    message = json.dumps({"type": event_type, "payload": payload or {}})
    try:
        client.publish(shop_channel(shop_id), message)
    except Exception:  # pragma: no cover - defensive
        logger.debug("Realtime publish failed for shop %s", shop_id, exc_info=True)

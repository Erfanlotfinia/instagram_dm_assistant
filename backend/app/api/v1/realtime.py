"""WebSocket endpoint for realtime command-center updates.

Clients connect to ``/api/v1/ws/shops/{shop_id}?token=<jwt>`` and receive
JSON events of the form ``{"type": ..., "payload": ..., "timestamp": ...}``.
Events are relayed from a Redis pub/sub channel populated by API handlers and
workers via :func:`app.realtime.publisher.publish_event`.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis import asyncio as aioredis

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.realtime.publisher import shop_channel
from app.services.auth_service import AuthService
from app.services.shop_service import ShopService

logger = logging.getLogger(__name__)

router = APIRouter()

HEARTBEAT_SECONDS = 25


def _authorize(token: str | None, shop_id: UUID) -> bool:
    """Validate the JWT and confirm the user can access the shop."""
    if not token:
        return False
    db = SessionLocal()
    try:
        user = AuthService(db).get_user_from_token(token)
        membership = ShopService(db).get_membership(shop_id, user.id)
        return membership is not None
    except Exception:
        return False
    finally:
        db.close()


@router.websocket("/ws/shops/{shop_id}")
async def shop_realtime(websocket: WebSocket, shop_id: UUID) -> None:
    token = websocket.query_params.get("token")
    if not await asyncio.to_thread(_authorize, token, shop_id):
        await websocket.close(code=4401)
        return

    await websocket.accept()
    settings = get_settings()

    try:
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.subscribe(shop_channel(shop_id))
    except Exception:
        logger.warning("Realtime WebSocket could not subscribe to Redis", exc_info=True)
        await websocket.send_json({"type": "realtime.unavailable", "payload": {}, "timestamp": _now()})
        await websocket.close(code=1011)
        return

    await websocket.send_json({"type": "realtime.connected", "payload": {"shop_id": str(shop_id)}, "timestamp": _now()})

    async def relay() -> None:
        async for message in pubsub.listen():
            if message is None or message.get("type") != "message":
                continue
            try:
                envelope = json.loads(message["data"])
            except (ValueError, TypeError):
                continue
            envelope.setdefault("timestamp", _now())
            await websocket.send_json(envelope)

    async def heartbeat() -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_SECONDS)
            await websocket.send_json({"type": "ping", "payload": {}, "timestamp": _now()})

    relay_task = asyncio.create_task(relay())
    heartbeat_task = asyncio.create_task(heartbeat())

    try:
        # Keep the connection open; ignore inbound client frames.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.debug("Realtime WebSocket closed", exc_info=True)
    finally:
        relay_task.cancel()
        heartbeat_task.cancel()
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe(shop_channel(shop_id))
            await pubsub.aclose()
            await client.aclose()


def _now() -> str:
    return datetime.now(UTC).isoformat()

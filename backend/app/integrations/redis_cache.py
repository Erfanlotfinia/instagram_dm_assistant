from __future__ import annotations

import json
import logging
from typing import Any

import redis

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class RedisCacheService:
    def __init__(self, settings: Settings | None = None, redis_client: redis.Redis | None = None) -> None:
        self.settings = settings or get_settings()
        self._redis = redis_client

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.Redis.from_url(self.settings.redis_url, decode_responses=True)
        return self._redis

    def try_acquire_idempotency(self, key: str, ttl_seconds: int = 86400) -> bool:
        """Return True if this is the first time seeing the key."""
        acquired = self.redis.set(f"webhook:idem:{key}", "1", nx=True, ex=ttl_seconds)
        return bool(acquired)

    def set_reservation_cache(self, reservation_id: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        self.redis.setex(f"reservation:{reservation_id}", ttl_seconds, json.dumps(payload))

    def get_reservation_cache(self, reservation_id: str) -> dict[str, Any] | None:
        raw = self.redis.get(f"reservation:{reservation_id}")
        if raw is None:
            return None
        return json.loads(raw)

    def delete_reservation_cache(self, reservation_id: str) -> None:
        self.redis.delete(f"reservation:{reservation_id}")

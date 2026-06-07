from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from typing import Iterator

import redis

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class ConversationLockService:
    def __init__(self, settings: Settings | None = None, redis_client: redis.Redis | None = None) -> None:
        self.settings = settings or get_settings()
        self._redis = redis_client

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.Redis.from_url(self.settings.redis_url, decode_responses=True)
        return self._redis

    def lock_key(self, conversation_id: str) -> str:
        return f"conversation:{conversation_id}:lock"

    def acquire(self, conversation_id: str, ttl_seconds: int | None = None) -> str | None:
        token = str(uuid.uuid4())
        ttl = ttl_seconds or self.settings.conversation_lock_ttl_seconds
        acquired = self.redis.set(self.lock_key(conversation_id), token, nx=True, ex=ttl)
        if acquired:
            return token
        return None

    def release(self, conversation_id: str, token: str) -> bool:
        key = self.lock_key(conversation_id)
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = self.redis.eval(script, 1, key, token)
        return bool(result)

    @contextmanager
    def hold(self, conversation_id: str, ttl_seconds: int | None = None) -> Iterator[str | None]:
        token = self.acquire(conversation_id, ttl_seconds=ttl_seconds)
        try:
            yield token
        finally:
            if token:
                self.release(conversation_id, token)

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import redis
from fastapi import HTTPException, Request, status

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitRule:
    key_prefix: str
    limit: int
    window_seconds: int


class RateLimiter:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: redis.Redis | None = None

    def _redis(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis.from_url(self.settings.redis_url, decode_responses=True)
        return self._client

    def check(self, rule: RateLimitRule, identifier: str) -> None:
        if not self.settings.rate_limit_enabled:
            return

        key = f"ratelimit:{rule.key_prefix}:{identifier}"
        now = int(time.time())
        window_start = now - rule.window_seconds

        pipe = self._redis().pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, rule.window_seconds)
        _, _, count, _ = pipe.execute()

        if count > rule.limit:
            logger.warning(
                "Rate limit exceeded prefix=%s identifier=%s count=%s limit=%s",
                rule.key_prefix,
                identifier,
                count,
                rule.limit,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(rule.window_seconds)},
            )


def client_identifier(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def enforce_rate_limit(request: Request, rule: RateLimitRule, identifier: str | None = None) -> None:
    RateLimiter().check(rule, identifier or client_identifier(request))

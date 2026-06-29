from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from uuid import uuid4

import redis
from fastapi import HTTPException, Request, Response, status

from app.core.client_ip import client_identifier
from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitRule:
    key_prefix: str
    limit: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitResult:
    limit: int
    remaining: int
    reset_seconds: int
    retry_after_seconds: int

    @property
    def headers(self) -> dict[str, str]:
        return {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(self.reset_seconds),
        }


class RateLimiter:
    _SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local now_ms = tonumber(ARGV[3])
local member = ARGV[4]
local window_start = now_ms - window_ms

redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
local count = redis.call('ZCARD', key)
local allowed = 0
if count < limit then
    redis.call('ZADD', key, now_ms, member)
    count = count + 1
    allowed = 1
end
redis.call('PEXPIRE', key, window_ms)

local reset_ms = window_ms
local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
if oldest[2] ~= nil then
    reset_ms = (tonumber(oldest[2]) + window_ms) - now_ms
    if reset_ms < 0 then
        reset_ms = 0
    end
end

local reset_seconds = math.ceil(reset_ms / 1000)
local retry_after_seconds = 0
if allowed == 0 then
    retry_after_seconds = reset_seconds
    if retry_after_seconds < 1 then
        retry_after_seconds = 1
    end
end
local remaining = limit - count
if remaining < 0 then
    remaining = 0
end

return {allowed, limit, remaining, reset_seconds, retry_after_seconds}
"""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: redis.Redis | None = None

    def _redis(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis.from_url(self.settings.redis_url, decode_responses=True)
        return self._client

    def check(self, rule: RateLimitRule, identifier: str) -> RateLimitResult:
        if not self.settings.rate_limit_enabled:
            return RateLimitResult(
                limit=rule.limit,
                remaining=rule.limit,
                reset_seconds=rule.window_seconds,
                retry_after_seconds=0,
            )

        key = f"ratelimit:{rule.key_prefix}:{identifier}"
        now_ms = int(time.time() * 1000)
        member = f"{now_ms}:{uuid4()}"
        allowed, limit, remaining, reset_seconds, retry_after_seconds = self._redis().eval(
            self._SCRIPT,
            1,
            key,
            rule.limit,
            rule.window_seconds * 1000,
            now_ms,
            member,
        )
        result = RateLimitResult(
            limit=int(limit),
            remaining=int(remaining),
            reset_seconds=int(reset_seconds),
            retry_after_seconds=int(retry_after_seconds),
        )

        if int(allowed) != 1:
            logger.warning(
                "Rate limit exceeded prefix=%s identifier=%s limit=%s",
                rule.key_prefix,
                identifier,
                rule.limit,
            )
            headers = result.headers | {"Retry-After": str(result.retry_after_seconds)}
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers=headers,
            )
        return result


def enforce_rate_limit(
    request: Request,
    rule: RateLimitRule,
    response: Response | None = None,
    identifier: str | None = None,
    settings: Settings | None = None,
) -> RateLimitResult:
    settings = settings or get_settings()
    result = RateLimiter(settings).check(rule, identifier or client_identifier(request, settings))
    if response is not None:
        response.headers.update(result.headers)
    return result

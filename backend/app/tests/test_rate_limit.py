from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers
from starlette.requests import Request

from app.core.config import Settings
from app.core.rate_limit import RateLimiter, RateLimitRule, client_identifier


class FakeRedis:
    def __init__(self) -> None:
        self.sorted_sets: dict[str, dict[str, int]] = defaultdict(dict)

    def eval(
        self,
        _script: str,
        _numkeys: int,
        key: str,
        limit: int,
        window_ms: int,
        now_ms: int,
        member: str,
    ):
        zset = self.sorted_sets[key]
        window_start = now_ms - window_ms
        for existing_member, score in list(zset.items()):
            if score <= window_start:
                del zset[existing_member]

        count = len(zset)
        allowed = 0
        if count < limit:
            zset[member] = now_ms
            count += 1
            allowed = 1

        reset_ms = window_ms
        if zset:
            reset_ms = max(0, min(zset.values()) + window_ms - now_ms)
        reset_seconds = math.ceil(reset_ms / 1000)
        retry_after_seconds = 0 if allowed else max(reset_seconds, 1)
        remaining = max(limit - count, 0)
        return [allowed, limit, remaining, reset_seconds, retry_after_seconds]


@dataclass
class Client:
    host: str
    port: int = 12345


def make_request(client_host: str, headers: dict[str, str] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": Headers(headers or {}).raw,
            "client": (client_host, 12345),
        }
    )


def enabled_settings(**overrides) -> Settings:
    values = {
        "rate_limit_enabled": True,
        "redis_url": "redis://localhost:6379/15",
        "trusted_proxy_cidrs": [],
    }
    values.update(overrides)
    return Settings(**values)


def test_same_millisecond_requests_count_individually(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    limiter = RateLimiter(enabled_settings())
    fake_redis = FakeRedis()
    monkeypatch.setattr(limiter, "_redis", lambda: fake_redis)
    monkeypatch.setattr("app.core.rate_limit.time.time", lambda: 1_700_000_000.123)

    rule = RateLimitRule("test", 10, 60)
    results = [limiter.check(rule, "client") for _ in range(10)]

    assert [result.remaining for result in results] == list(range(9, -1, -1))
    assert len(fake_redis.sorted_sets["ratelimit:test:client"]) == 10


def test_exceeding_limit_returns_429_with_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    limiter = RateLimiter(enabled_settings())
    fake_redis = FakeRedis()
    monkeypatch.setattr(limiter, "_redis", lambda: fake_redis)
    monkeypatch.setattr("app.core.rate_limit.time.time", lambda: 1_700_000_000.123)
    rule = RateLimitRule("test", 2, 60)

    limiter.check(rule, "client")
    limiter.check(rule, "client")

    with pytest.raises(HTTPException) as exc_info:
        limiter.check(rule, "client")

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers == {
        "X-RateLimit-Limit": "2",
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": "60",
        "Retry-After": "60",
    }


def test_spoofed_forwarded_for_is_ignored_when_proxy_is_not_trusted() -> None:
    request = make_request("203.0.113.10", {"X-Forwarded-For": "198.51.100.99"})

    assert (
        client_identifier(request, enabled_settings(trusted_proxy_cidrs=["10.0.0.0/8"]))
        == "203.0.113.10"
    )


def test_forwarded_for_is_honored_when_proxy_is_trusted() -> None:
    request = make_request(
        "10.1.2.3",
        {"X-Forwarded-For": "198.51.100.99, 10.1.2.3", "X-Real-IP": "198.51.100.100"},
    )

    assert (
        client_identifier(request, enabled_settings(trusted_proxy_cidrs=["10.0.0.0/8"]))
        == "198.51.100.99"
    )

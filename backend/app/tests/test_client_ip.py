from __future__ import annotations

from starlette.datastructures import Headers
from starlette.requests import Request

from app.core.client_ip import resolve_client_ip
from app.core.config import Settings


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


def test_uses_client_host_when_no_trusted_proxy_configured() -> None:
    request = make_request("203.0.113.10", {"X-Forwarded-For": "198.51.100.99"})

    assert resolve_client_ip(request, enabled_settings()) == "203.0.113.10"


def test_spoofed_forwarded_for_is_ignored_from_untrusted_source() -> None:
    request = make_request("203.0.113.10", {"X-Forwarded-For": "198.51.100.99"})

    assert (
        resolve_client_ip(request, enabled_settings(trusted_proxy_cidrs=["10.0.0.0/8"]))
        == "203.0.113.10"
    )


def test_forwarded_for_is_used_when_source_is_trusted_proxy() -> None:
    request = make_request(
        "10.1.2.3",
        {"X-Forwarded-For": "198.51.100.99, 10.1.2.3", "X-Real-IP": "198.51.100.100"},
    )

    assert (
        resolve_client_ip(request, enabled_settings(trusted_proxy_cidrs=["10.0.0.0/8"]))
        == "198.51.100.99"
    )


def test_real_ip_is_used_when_trusted_proxy_and_no_forwarded_for() -> None:
    request = make_request("10.1.2.3", {"X-Real-IP": "198.51.100.100"})

    assert (
        resolve_client_ip(request, enabled_settings(trusted_proxy_cidrs=["10.0.0.0/8"]))
        == "198.51.100.100"
    )

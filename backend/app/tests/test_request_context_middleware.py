from __future__ import annotations

import pytest
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings
from app.core.middleware import RequestContextMiddleware
from app.core.request_context import clear_request_context, get_request_context


def _settings(**overrides) -> Settings:
    values = {
        "rate_limit_enabled": True,
        "redis_url": "redis://localhost:6379/15",
        "trusted_proxy_cidrs": [],
    }
    values.update(overrides)
    return Settings(**values)


def _make_request(client_host: str, headers: dict[str, str] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": Headers(headers or {}).raw,
            "client": (client_host, 12345),
        }
    )


@pytest.fixture(autouse=True)
def _clear_context() -> None:
    clear_request_context()
    yield
    clear_request_context()


@pytest.mark.asyncio
async def test_middleware_uses_client_host_without_trusted_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.middleware.get_settings", lambda: _settings())
    captured: list[str | None] = []

    async def call_next(request: Request) -> Response:
        ctx = get_request_context()
        captured.append(ctx.ip_address if ctx else None)
        return Response(status_code=200)

    middleware = RequestContextMiddleware(app=object())  # type: ignore[arg-type]
    await middleware.dispatch(_make_request("203.0.113.10", {"X-Forwarded-For": "198.51.100.99"}), call_next)

    assert captured == ["203.0.113.10"]


@pytest.mark.asyncio
async def test_middleware_ignores_spoofed_forwarded_for(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.core.middleware.get_settings",
        lambda: _settings(trusted_proxy_cidrs=["10.0.0.0/8"]),
    )
    captured: list[str | None] = []

    async def call_next(request: Request) -> Response:
        ctx = get_request_context()
        captured.append(ctx.ip_address if ctx else None)
        return Response(status_code=200)

    middleware = RequestContextMiddleware(app=object())  # type: ignore[arg-type]
    await middleware.dispatch(_make_request("203.0.113.10", {"X-Forwarded-For": "198.51.100.99"}), call_next)

    assert captured == ["203.0.113.10"]


@pytest.mark.asyncio
async def test_middleware_uses_forwarded_for_from_trusted_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.core.middleware.get_settings",
        lambda: _settings(trusted_proxy_cidrs=["10.0.0.0/8"]),
    )
    captured: list[str | None] = []

    async def call_next(request: Request) -> Response:
        ctx = get_request_context()
        captured.append(ctx.ip_address if ctx else None)
        return Response(status_code=200)

    middleware = RequestContextMiddleware(app=object())  # type: ignore[arg-type]
    await middleware.dispatch(
        _make_request("10.1.2.3", {"X-Forwarded-For": "198.51.100.99, 10.1.2.3"}),
        call_next,
    )

    assert captured == ["198.51.100.99"]

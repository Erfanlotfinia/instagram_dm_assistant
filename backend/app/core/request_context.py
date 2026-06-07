from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class RequestContext:
    request_id: str
    ip_address: str | None = None
    user_agent: str | None = None


_request_context: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)


def new_request_id() -> str:
    return str(uuid4())


def set_request_context(
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> RequestContext:
    ctx = RequestContext(
        request_id=request_id or new_request_id(),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    _request_context.set(ctx)
    return ctx


def get_request_context() -> RequestContext | None:
    return _request_context.get()


def get_request_id() -> str | None:
    ctx = get_request_context()
    return ctx.request_id if ctx else None


def context_log_extra() -> dict[str, Any]:
    ctx = get_request_context()
    if ctx is None:
        return {}
    extra: dict[str, Any] = {"request_id": ctx.request_id}
    if ctx.ip_address:
        extra["ip_address"] = ctx.ip_address
    return extra

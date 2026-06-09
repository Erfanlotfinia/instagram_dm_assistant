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
    tenant_id: str | None = None
    conversation_id: str | None = None
    order_id: str | None = None


_request_context: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)


def new_request_id() -> str:
    return str(uuid4())


def set_request_context(
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    tenant_id: str | None = None,
    conversation_id: str | None = None,
    order_id: str | None = None,
) -> RequestContext:
    ctx = RequestContext(
        request_id=request_id or new_request_id(),
        ip_address=ip_address,
        user_agent=user_agent,
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        order_id=order_id,
    )
    _request_context.set(ctx)
    return ctx


def set_order_context(tenant_id: str, order_id: str, conversation_id: str | None = None) -> RequestContext:
    current = get_request_context()
    return set_request_context(
        request_id=current.request_id if current else new_request_id(),
        ip_address=current.ip_address if current else None,
        user_agent=current.user_agent if current else None,
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        order_id=order_id,
    )


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
    if ctx.tenant_id:
        extra["tenant_id"] = ctx.tenant_id
    if ctx.conversation_id:
        extra["conversation_id"] = ctx.conversation_id
    if ctx.order_id:
        extra["order_id"] = ctx.order_id
    return extra

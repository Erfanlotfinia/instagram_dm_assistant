from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from app.services.soc_events import DomainEvent, TenantScope


class FrozenPayload(dict[str, Any]):
    """Deeply immutable, JSON-compatible event payload snapshot."""

    _sealed: bool

    def __init__(self, value: dict[str, Any]) -> None:
        super().__init__((key, _freeze_payload(item)) for key, item in value.items())
        self._sealed = True

    def _immutable(self, *_: object, **__: object) -> None:
        raise TypeError("event_payload_is_immutable")

    def __setitem__(self, key: str, value: Any) -> None:
        if getattr(self, "_sealed", False):
            self._immutable()
        super().__setitem__(key, value)

    def __delitem__(self, key: str) -> None:
        self._immutable()

    def __deepcopy__(self, memo: dict[int, object]) -> FrozenPayload:
        return self

    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable


def _freeze_payload(value: Any) -> Any:
    if isinstance(value, FrozenPayload):
        return value
    if isinstance(value, dict):
        return FrozenPayload(deepcopy(value))
    if isinstance(value, list | tuple):
        return tuple(_freeze_payload(item) for item in deepcopy(value))
    if isinstance(value, set | frozenset):
        return frozenset(_freeze_payload(item) for item in deepcopy(value))
    return deepcopy(value)


def _freeze_event(event: DomainEvent) -> DomainEvent:
    return replace(event, payload=_freeze_payload(event.payload))


@dataclass(frozen=True, slots=True)
class StoredEvent:
    offset: int
    event: DomainEvent


class ImmutableEventStore:
    """Append-only event store with tenant/conversation indexes and replay."""

    def __init__(self) -> None:
        self._events: list[StoredEvent] = []
        self._by_tenant: dict[str, list[StoredEvent]] = defaultdict(list)
        self._by_conversation: dict[tuple[str, str], list[StoredEvent]] = defaultdict(list)
        self.audit_compliance_mode = True

    def append(self, event: DomainEvent) -> StoredEvent:
        event.validate()
        frozen_event = _freeze_event(event)
        stored = StoredEvent(len(self._events), frozen_event)
        self._events.append(stored)
        self._by_tenant[frozen_event.tenant_id].append(stored)
        self._by_conversation[(frozen_event.tenant_id, frozen_event.conversation_id)].append(stored)
        return stored

    def update(self, *_: object, **__: object) -> None:
        raise PermissionError("event_store_is_append_only_updates_forbidden")

    def delete(self, *_: object, **__: object) -> None:
        raise PermissionError("event_store_is_append_only_deletes_forbidden")

    def replay(
        self,
        scope: TenantScope,
        *,
        conversation_id: str | None = None,
        until: datetime | None = None,
    ) -> list[DomainEvent]:
        rows: Iterable[StoredEvent]
        if conversation_id:
            rows = self._by_conversation[(scope.tenant_id, conversation_id)]
        else:
            rows = self._by_tenant[scope.tenant_id]
        events = [
            row.event
            for row in rows
            if row.event.shop_id == scope.shop_id
            and (until is None or row.event.event_time <= until)
        ]
        return sorted(events, key=lambda e: (e.event_time, e.sequence or 0, e.event_id))

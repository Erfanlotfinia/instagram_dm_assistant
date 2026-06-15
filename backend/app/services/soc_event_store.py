from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from app.services.soc_events import DomainEvent, TenantScope


@dataclass(frozen=True, slots=True)
class StoredEvent:
    offset: int
    event: DomainEvent


class ImmutableEventStore:
    """Append-only event store with tenant/conversation indexes and replay."""

    def __init__(self) -> None:
        self._events: list[StoredEvent] = []
        self._by_tenant: dict[str, list[StoredEvent]] = defaultdict(list)
        self._by_conversation: dict[tuple[str, str], list[StoredEvent]] = defaultdict(
            list
        )
        self.audit_compliance_mode = True

    def append(self, event: DomainEvent) -> StoredEvent:
        event.validate()
        stored = StoredEvent(len(self._events), event)
        self._events.append(stored)
        self._by_tenant[event.tenant_id].append(stored)
        self._by_conversation[(event.tenant_id, event.conversation_id)].append(stored)
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

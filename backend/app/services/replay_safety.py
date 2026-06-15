from __future__ import annotations

from dataclasses import dataclass, field

from app.services.soc_event_store import ImmutableEventStore
from app.services.soc_events import DomainEvent, DomainEventType, TenantScope

SIDE_EFFECTING = {
    DomainEventType.ORDER_CREATED,
    DomainEventType.PAYMENT_UPDATED,
    DomainEventType.INVENTORY_UPDATED,
}


@dataclass(slots=True)
class ReplayResult:
    events_seen: int
    side_effects_blocked: int
    reconstructed_state: dict[str, object] = field(default_factory=dict)


class SafeReplayEngine:
    """Deterministic dry-run replay that refuses irreversible side effects."""

    def __init__(self, store: ImmutableEventStore) -> None:
        self.store = store

    def dry_run(
        self, scope: TenantScope, *, conversation_id: str | None = None
    ) -> ReplayResult:
        state: dict[str, object] = {"messages": 0, "handoffs": 0, "llm_calls": 0}
        blocked = 0
        for event in self.store.replay(scope, conversation_id=conversation_id):
            if event.event_type in SIDE_EFFECTING:
                blocked += 1
                continue
            self._rehydrate(state, event)
        return ReplayResult(
            events_seen=len(self.store.replay(scope, conversation_id=conversation_id)),
            side_effects_blocked=blocked,
            reconstructed_state=state,
        )

    def _rehydrate(self, state: dict[str, object], event: DomainEvent) -> None:
        if event.event_type == DomainEventType.MESSAGE_RECEIVED:
            state["messages"] = int(state["messages"]) + 1
        elif event.event_type == DomainEventType.HANDOFF_TRIGGERED:
            state["handoffs"] = int(state["handoffs"]) + 1
        elif event.event_type == DomainEventType.LLM_FALLBACK_CALLED:
            state["llm_calls"] = int(state["llm_calls"]) + 1

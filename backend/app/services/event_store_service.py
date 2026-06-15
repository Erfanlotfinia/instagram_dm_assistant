from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import TraceEventType
from app.domain.models import TraceEvent
from app.services.decision_trace_service import DecisionTraceService


@dataclass(frozen=True)
class ReplayEvent:
    sequence: int
    event_type: str
    payload: dict[str, Any]


class EventStoreService:
    """Append-only interaction log backed by trace_events for replay."""

    EVENT_TYPE_MAP = {
        "message_received": TraceEventType.ACTION_ATTEMPTED,
        "scenario_detected": TraceEventType.ACTION_ATTEMPTED,
        "automation_executed": TraceEventType.ACTION_ATTEMPTED,
        "llm_called": TraceEventType.ACTION_ATTEMPTED,
        "handoff_triggered": TraceEventType.ACTION_ATTEMPTED,
        "order_created": TraceEventType.ACTION_ATTEMPTED,
        "payment_updated": TraceEventType.ACTION_ATTEMPTED,
        "policy_blocked": TraceEventType.ACTION_BLOCKED,
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.traces = DecisionTraceService(db)

    def append(
        self,
        *,
        trace_id: UUID,
        shop_id: UUID,
        conversation_id: UUID | None,
        event_type: str,
        payload: dict[str, Any],
    ) -> TraceEvent:
        mapped = self.EVENT_TYPE_MAP.get(event_type, TraceEventType.ACTION_ATTEMPTED)
        return self.traces.record(
            trace_id=trace_id,
            shop_id=shop_id,
            conversation_id=conversation_id,
            event_type=mapped,
            payload={"event_type": event_type, **payload},
        )

    def replay(self, conversation_id: UUID) -> list[ReplayEvent]:
        rows = self.db.scalars(
            select(TraceEvent)
            .where(TraceEvent.conversation_id == conversation_id)
            .order_by(TraceEvent.created_at.asc(), TraceEvent.sequence.asc())
        ).all()
        return [
            ReplayEvent(
                r.sequence,
                r.payload_json.get("event_type", r.event_type.value),
                r.payload_json,
            )
            for r in rows
        ]

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.request_context import get_trace_id, set_trace_context
from app.domain.enums import TraceEventType
from app.domain.models import AgentDecisionTrace, TraceEvent
from app.schemas.trace import AssembledDecisionTraceRead, TraceEventRead

logger = logging.getLogger(__name__)


class DecisionTraceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def new_trace_id() -> UUID:
        return uuid4()

    def record(
        self,
        *,
        trace_id: UUID,
        shop_id: UUID,
        event_type: TraceEventType,
        payload: dict[str, Any],
        conversation_id: UUID | None = None,
        commit: bool = False,
    ) -> TraceEvent:
        sequence = int(
            self.db.scalar(
                select(func.coalesce(func.max(TraceEvent.sequence), -1)).where(TraceEvent.trace_id == trace_id)
            )
            or -1
        ) + 1
        event = TraceEvent(
            trace_id=trace_id,
            shop_id=shop_id,
            conversation_id=conversation_id,
            sequence=sequence,
            event_type=event_type,
            payload_json=payload,
        )
        self.db.add(event)
        if commit:
            self.db.commit()
            self.db.refresh(event)
        else:
            self.db.flush()
        logger.info(
            "trace_event_recorded trace_id=%s event_type=%s sequence=%s",
            trace_id,
            event_type.value,
            sequence,
            extra={"trace_id": str(trace_id), "shop_id": str(shop_id)},
        )
        return event

    def record_policy_checks(
        self,
        *,
        trace_id: UUID,
        shop_id: UUID,
        checks: list[dict[str, Any]],
        conversation_id: UUID | None = None,
    ) -> None:
        for check in checks:
            self.record(
                trace_id=trace_id,
                shop_id=shop_id,
                event_type=TraceEventType.POLICY_CHECK,
                payload=check,
                conversation_id=conversation_id,
            )

    def get_events(self, trace_id: UUID) -> list[TraceEvent]:
        return list(
            self.db.scalars(
                select(TraceEvent).where(TraceEvent.trace_id == trace_id).order_by(TraceEvent.sequence.asc())
            ).all()
        )

    def get_assembled_trace(self, shop_id: UUID, trace_id: UUID) -> AssembledDecisionTraceRead | None:
        events = self.get_events(trace_id)
        if not events:
            return None
        if events[0].shop_id != shop_id:
            return None

        header = self.db.scalar(
            select(AgentDecisionTrace).where(AgentDecisionTrace.id == trace_id)
        )
        if header is None:
            conversation_id = events[0].conversation_id
            header = self.db.scalar(
                select(AgentDecisionTrace)
                .where(AgentDecisionTrace.conversation_id == conversation_id)
                .order_by(AgentDecisionTrace.created_at.desc())
                .limit(1)
            ) if conversation_id else None

        retrieval = [e for e in events if e.event_type == TraceEventType.RETRIEVAL_EVIDENCE]
        slots = [e for e in events if e.event_type == TraceEventType.SLOTS_EXTRACTED]
        confidence = [e for e in events if e.event_type == TraceEventType.CONFIDENCE_BAND]
        policy_checks = [e for e in events if e.event_type == TraceEventType.POLICY_CHECK]
        attempted = [e for e in events if e.event_type == TraceEventType.ACTION_ATTEMPTED]
        blocked = [e for e in events if e.event_type == TraceEventType.ACTION_BLOCKED]

        return AssembledDecisionTraceRead(
            trace_id=trace_id,
            shop_id=shop_id,
            conversation_id=events[0].conversation_id,
            header={
                "intent": header.intent if header else None,
                "next_state": header.next_state if header else None,
                "auto_send_allowed": header.auto_send_allowed if header else None,
                "human_handoff_required": header.human_handoff_required if header else None,
                "reasoning_summary": header.reasoning_summary if header else None,
            },
            retrieval_evidence=[TraceEventRead.model_validate(e) for e in retrieval],
            slots_extracted=[TraceEventRead.model_validate(e) for e in slots],
            confidence_bands=[TraceEventRead.model_validate(e) for e in confidence],
            policy_checks=[TraceEventRead.model_validate(e) for e in policy_checks],
            actions_attempted=[TraceEventRead.model_validate(e) for e in attempted],
            actions_blocked=[TraceEventRead.model_validate(e) for e in blocked],
            all_events=[TraceEventRead.model_validate(e) for e in events],
        )

    def bind_trace_context(self, trace_id: UUID | None = None) -> UUID:
        resolved = trace_id or self.new_trace_id()
        set_trace_context(trace_id=str(resolved))
        return resolved

    def current_trace_id(self) -> UUID | None:
        raw = get_trace_id()
        if raw is None:
            return None
        try:
            return UUID(raw)
        except ValueError:
            return None

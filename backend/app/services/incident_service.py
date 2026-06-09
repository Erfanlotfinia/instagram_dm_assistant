from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import IncidentSeverity, IncidentStatus, IncidentTrigger
from app.domain.models import Incident, IncidentEvent


class IncidentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def open_from_emergency_stop(
        self,
        shop_id: UUID,
        *,
        user_id: UUID | None,
        scope_preview: dict,
        reason: str | None = None,
    ) -> Incident:
        incident = Incident(
            shop_id=shop_id,
            title="Emergency stop activated",
            severity=IncidentSeverity.CRITICAL,
            status=IncidentStatus.OPEN,
            trigger=IncidentTrigger.EMERGENCY_STOP,
            opened_by_user_id=user_id,
            summary_json={"reason": reason, "scope_preview": scope_preview},
        )
        self.db.add(incident)
        self.db.flush()
        self.append_event(
            incident,
            event_type="emergency_stop_activated",
            actor_user_id=user_id,
            description=reason or "Emergency stop activated",
            metadata=scope_preview,
            affected_conversation_ids=scope_preview.get("affected_conversation_ids", []),
            commit=False,
        )
        return incident

    def open_from_policy_breach(
        self,
        shop_id: UUID,
        *,
        user_id: UUID | None,
        policy_name: str,
        details: dict,
    ) -> Incident:
        incident = Incident(
            shop_id=shop_id,
            title=f"Policy breach: {policy_name}",
            severity=IncidentSeverity.HIGH,
            status=IncidentStatus.OPEN,
            trigger=IncidentTrigger.POLICY_BREACH,
            opened_by_user_id=user_id,
            summary_json={"policy_name": policy_name, "details": details},
        )
        self.db.add(incident)
        self.db.flush()
        self.append_event(
            incident,
            event_type="policy_breach_detected",
            actor_user_id=user_id,
            description=f"Policy breach detected for {policy_name}",
            metadata=details,
            commit=False,
        )
        return incident

    def append_event(
        self,
        incident: Incident,
        *,
        event_type: str,
        actor_user_id: UUID | None,
        description: str | None = None,
        metadata: dict | None = None,
        affected_conversation_ids: list[str] | None = None,
        commit: bool = True,
    ) -> IncidentEvent:
        event = IncidentEvent(
            incident_id=incident.id,
            event_type=event_type,
            actor_user_id=actor_user_id,
            description=description,
            metadata_json=metadata or {},
            affected_conversation_ids=affected_conversation_ids or [],
        )
        self.db.add(event)
        if commit:
            self.db.commit()
            self.db.refresh(event)
        else:
            self.db.flush()
        return event

    def get_incident(self, shop_id: UUID, incident_id: UUID) -> Incident | None:
        incident = self.db.scalar(
            select(Incident)
            .where(Incident.id == incident_id, Incident.shop_id == shop_id)
            .options(selectinload(Incident.events))
        )
        return incident

    def resolve(self, incident: Incident) -> Incident:
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(incident)
        return incident

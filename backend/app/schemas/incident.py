from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class IncidentEventRead(BaseModel):
    id: UUID
    incident_id: UUID
    event_type: str
    actor_user_id: UUID | None
    description: str | None
    metadata_json: dict
    affected_conversation_ids: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentRead(BaseModel):
    id: UUID
    shop_id: UUID
    title: str
    severity: str
    status: str
    trigger: str
    opened_by_user_id: UUID | None
    opened_at: datetime
    resolved_at: datetime | None
    summary_json: dict
    events: list[IncidentEventRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}

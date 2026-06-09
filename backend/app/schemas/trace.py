from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TraceEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trace_id: UUID
    shop_id: UUID
    conversation_id: UUID | None
    sequence: int
    event_type: str
    payload_json: dict
    created_at: datetime

    @field_validator("event_type", mode="before")
    @classmethod
    def _event_type_str(cls, value: object) -> str:
        return value.value if hasattr(value, "value") else str(value)


class AssembledDecisionTraceRead(BaseModel):
    trace_id: UUID
    shop_id: UUID
    conversation_id: UUID | None = None
    header: dict = Field(default_factory=dict)
    retrieval_evidence: list[TraceEventRead] = Field(default_factory=list)
    slots_extracted: list[TraceEventRead] = Field(default_factory=list)
    confidence_bands: list[TraceEventRead] = Field(default_factory=list)
    policy_checks: list[TraceEventRead] = Field(default_factory=list)
    actions_attempted: list[TraceEventRead] = Field(default_factory=list)
    actions_blocked: list[TraceEventRead] = Field(default_factory=list)
    all_events: list[TraceEventRead] = Field(default_factory=list)

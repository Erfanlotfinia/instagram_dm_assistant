from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DMSimulatorRequest(BaseModel):
    instagram_account_id: UUID
    message_text: str = Field(min_length=1, max_length=2000)
    shared_post_url: str | None = Field(default=None, max_length=2048)
    instagram_user_id: str = Field(default="simulated-customer", max_length=64)


class DMSimulatorResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    is_simulation: bool = True
    intent: str | None = None
    extracted_slots: dict = Field(default_factory=dict)
    product_resolution: dict = Field(default_factory=dict)
    variant_resolution: dict = Field(default_factory=dict)
    inventory_result: dict = Field(default_factory=dict)
    next_state: str
    suggested_reply: str | None = None
    auto_send_decision: dict = Field(default_factory=dict)
    handoff_reason: str | None = None
    draft_order: dict | None = None
    decision_trace: dict = Field(default_factory=dict)


class SimulatorRunSummary(BaseModel):
    conversation_id: UUID
    message_id: UUID | None = None
    created_at: datetime
    intent: str | None = None
    next_state: str | None = None
    suggested_reply: str | None = None
    message_preview: str | None = None


class SimulatorResetResponse(BaseModel):
    deleted_conversations: int

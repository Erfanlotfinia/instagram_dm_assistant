from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class DMSimulatorRequest(BaseModel):
    instagram_account_id: UUID
    message_text: str = Field(min_length=1, max_length=2000)
    shared_post_url: str | None = Field(default=None, max_length=2048)
    instagram_user_id: str = Field(default="simulated-customer", max_length=64)


class DMSimulatorResponse(BaseModel):
    conversation_id: UUID
    is_simulation: bool = True
    extracted_intent: str | None = None
    extracted_slots: dict = Field(default_factory=dict)
    product_resolution: dict = Field(default_factory=dict)
    variant_resolution: dict = Field(default_factory=dict)
    inventory_result: dict = Field(default_factory=dict)
    next_state: str
    suggested_reply: str | None = None
    auto_send: bool = False
    preview_required: bool = False
    handoff_required: bool = False
    audit: list[dict] = Field(default_factory=list)

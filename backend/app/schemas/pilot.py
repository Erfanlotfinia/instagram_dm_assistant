from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PilotSettingsBase(BaseModel):
    pilot_enabled: bool = False
    pilot_name: str = "Pilot"
    pilot_start_date: datetime | None = None
    pilot_end_date: datetime | None = None
    max_auto_sent_messages_per_day: int = Field(default=50, ge=0)
    max_auto_created_orders_per_day: int = Field(default=20, ge=0)
    require_operator_approval_for_first_50_orders: bool = True
    allowed_instagram_account_ids: list[UUID] = Field(default_factory=list)
    allowed_product_ids: list[UUID] | None = None
    emergency_stop_enabled: bool = False
    operating_mode: str = "copilot"
    category_overrides_json: dict = Field(default_factory=dict)
    campaign_overrides_json: dict = Field(default_factory=dict)


class PilotSettingsUpdate(BaseModel):
    pilot_enabled: bool | None = None
    pilot_name: str | None = None
    pilot_start_date: datetime | None = None
    pilot_end_date: datetime | None = None
    max_auto_sent_messages_per_day: int | None = Field(default=None, ge=0)
    max_auto_created_orders_per_day: int | None = Field(default=None, ge=0)
    require_operator_approval_for_first_50_orders: bool | None = None
    allowed_instagram_account_ids: list[UUID] | None = None
    allowed_product_ids: list[UUID] | None = None
    emergency_stop_enabled: bool | None = None
    operating_mode: str | None = None
    category_overrides_json: dict | None = None
    campaign_overrides_json: dict | None = None


class PilotSettingsRead(PilotSettingsBase):
    shop_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PilotChecklistItem(BaseModel):
    key: str
    label: str
    passed: bool
    detail: str | None = None


class PilotReadinessCriterion(BaseModel):
    key: str
    label: str
    passed: bool
    detail: str | None = None


class PilotReadinessResponse(BaseModel):
    shop_id: UUID
    ready_for_trl6_pilot: bool
    checklist: list[PilotChecklistItem]
    criteria: list[PilotReadinessCriterion]
    latest_trl_validation: dict | None = None
    pilot_settings: PilotSettingsRead
    warnings: list[str]


class PilotMetricsRead(BaseModel):
    inbound_messages: int
    auto_sent_messages: int
    previewed_messages: int
    human_handoff_count: int
    draft_orders: int
    confirmed_orders: int
    paid_orders: int
    cancelled_orders: int
    failed_jobs: int
    invalid_llm_outputs: int
    average_response_time_ms: float
    p95_response_time_ms: float
    operator_takeover_count: int


class PilotEventRead(BaseModel):
    id: UUID
    shop_id: UUID
    event_type: str
    severity: str
    title: str
    description: str | None = None
    metadata: dict | None = None
    created_at: datetime


class PilotEventLogRead(BaseModel):
    events: list[PilotEventRead]


class PilotActionResponse(BaseModel):
    pilot_settings: PilotSettingsRead
    event: PilotEventRead


class EmergencyStopScopePreview(BaseModel):
    active_conversation_count: int
    simulation_conversation_count: int
    affected_conversation_ids: list[UUID] = Field(default_factory=list)


class EmergencyStopRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class EmergencyStopResponse(BaseModel):
    pilot_settings: PilotSettingsRead
    event: PilotEventRead
    scope_preview: EmergencyStopScopePreview
    incident_id: UUID | None = None


class PilotModeUpdateRequest(BaseModel):
    operating_mode: str
    scope: str = "global"
    scope_ref: str | None = None
    reason: str | None = None
    category_overrides_json: dict | None = None
    campaign_overrides_json: dict | None = None


class PilotModeUpdateResponse(BaseModel):
    pilot_settings: PilotSettingsRead
    history_id: UUID

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["low", "medium", "high", "critical"]


class AgentRiskSettingsRead(BaseModel):
    shop_id: UUID
    intent_confidence_threshold: float = Field(ge=0, le=1)
    slot_confidence_threshold: float = Field(ge=0, le=1)
    product_confidence_threshold: float = Field(ge=0, le=1)
    variant_confidence_threshold: float = Field(ge=0, le=1)
    address_confidence_threshold: float = Field(ge=0, le=1)
    high_value_order_threshold: float = Field(ge=0)
    handoff_for_high_risk: bool
    handoff_for_low_variant_confidence: bool
    preview_required_for_high_value_order: bool


class AgentRiskSettingsUpdate(BaseModel):
    intent_confidence_threshold: float | None = Field(default=None, ge=0, le=1)
    slot_confidence_threshold: float | None = Field(default=None, ge=0, le=1)
    product_confidence_threshold: float | None = Field(default=None, ge=0, le=1)
    variant_confidence_threshold: float | None = Field(default=None, ge=0, le=1)
    address_confidence_threshold: float | None = Field(default=None, ge=0, le=1)
    high_value_order_threshold: float | None = Field(default=None, ge=0)
    handoff_for_high_risk: bool | None = None
    handoff_for_low_variant_confidence: bool | None = None
    preview_required_for_high_value_order: bool | None = None


class AgentDecisionTraceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    message_id: UUID | None
    agent_run_id: UUID | None
    intent: str | None
    extracted_slots: dict[str, Any]
    normalized_slots: dict[str, Any]
    product_candidates: list[dict[str, Any]]
    selected_product_id: UUID | None
    variant_resolution: dict[str, Any]
    inventory_result: dict[str, Any]
    risk_score: dict[str, Any]
    order_action: dict[str, Any]
    next_state: str
    outbound_message_id: UUID | None
    auto_send_allowed: bool
    human_handoff_required: bool
    reasoning_summary: str | None
    created_at: datetime


class TRLRiskMetricsRead(BaseModel):
    invalid_llm_json_count: int = 0
    safe_fallback_count: int = 0
    human_handoff_count: int = 0
    false_positive_order_creation: int = 0
    false_positive_auto_send: int = 0
    average_risk_score: float = 0
    critical_risk_count: int = 0
    scenario_pass_rate_by_category: dict[str, float] = Field(default_factory=dict)
    average_processing_latency: float = 0
    p95_processing_latency: float = 0

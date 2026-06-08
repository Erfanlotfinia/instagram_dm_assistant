from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import AgentMode, SellingStyle


class ShopAgentStudioSettingsRead(BaseModel):
    shop_id: UUID
    mode: AgentMode = AgentMode.COPILOT
    auto_send_enabled: bool = True
    preview_required_for_low_confidence: bool = True
    preview_required_for_first_order: bool = True
    preview_required_for_high_value_order: bool = True
    confidence_threshold_intent: Decimal = Decimal("0.75")
    confidence_threshold_product: Decimal = Decimal("0.80")
    confidence_threshold_variant: Decimal = Decimal("0.85")
    confidence_threshold_address: Decimal = Decimal("0.80")
    high_value_order_threshold: Decimal = Decimal("0")
    brand_voice: str | None = None
    selling_style: SellingStyle = SellingStyle.FRIENDLY
    discount_policy_json: dict = Field(default_factory=dict)
    handoff_policy_json: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShopAgentStudioSettingsUpdate(BaseModel):
    mode: AgentMode | None = None
    auto_send_enabled: bool | None = None
    preview_required_for_low_confidence: bool | None = None
    preview_required_for_first_order: bool | None = None
    preview_required_for_high_value_order: bool | None = None
    confidence_threshold_intent: Decimal | None = Field(default=None, ge=0, le=1)
    confidence_threshold_product: Decimal | None = Field(default=None, ge=0, le=1)
    confidence_threshold_variant: Decimal | None = Field(default=None, ge=0, le=1)
    confidence_threshold_address: Decimal | None = Field(default=None, ge=0, le=1)
    high_value_order_threshold: Decimal | None = Field(default=None, ge=0)
    brand_voice: str | None = None
    selling_style: SellingStyle | None = None
    discount_policy_json: dict | None = None
    handoff_policy_json: dict | None = None


class AutoSendDecisionRequest(BaseModel):
    intent_confidence: float = 1.0
    product_confidence: float = 1.0
    variant_confidence: float = 1.0
    address_confidence: float = 1.0
    order_total: Decimal = Decimal("0")
    is_first_order: bool = False
    handoff_reason: str | None = None
    message_risk: str | None = None


class AutoSendDecisionRead(BaseModel):
    auto_send_allowed: bool
    preview_required: bool
    requires_handoff: bool = False
    reasons: list[str] = Field(default_factory=list)

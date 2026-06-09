from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PolicyConfigValidateRequest(BaseModel):
    config_json: dict[str, Any] = Field(default_factory=dict)


class PolicyConfigValidateResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class PolicyEvaluationSampleRequest(BaseModel):
    config_json: dict[str, Any] = Field(default_factory=dict)
    operating_mode: str = "copilot"
    intent_confidence: float = Field(default=0.9, ge=0, le=1)
    product_confidence: float = Field(default=0.9, ge=0, le=1)
    variant_confidence: float = Field(default=0.9, ge=0, le=1)
    customer_confirmed: bool = False
    stock_reserved: bool = True
    within_messaging_window: bool = True
    action_name: str | None = None
    requires_write: bool = False
    handoff_required: bool = False
    emergency_stop: bool = False


class PolicyCheckResultRead(BaseModel):
    name: str
    passed: bool
    reason: str | None = None
    severity: str = "info"


class PolicyEvaluationResponse(BaseModel):
    allowed: bool
    checks: list[PolicyCheckResultRead] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)


class PolicyVersionRead(BaseModel):
    id: UUID
    shop_id: UUID
    version: str
    name: str
    config_json: dict[str, Any]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

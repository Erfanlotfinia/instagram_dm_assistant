from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminTaskCreate(BaseModel):
    task_type: str = Field(min_length=1, max_length=64)
    context: str = ""
    conversation_id: UUID | None = None


class AdminTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    requested_by_user_id: UUID | None
    task_type: str
    input_json: dict[str, Any]
    output_json: dict[str, Any]
    status: str
    requires_approval: bool
    approved_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class OperatorCorrectionCreate(BaseModel):
    conversation_id: UUID
    message_id: UUID | None = None
    before_json: dict[str, Any] = Field(default_factory=dict)
    after_json: dict[str, Any] = Field(default_factory=dict)


class OperatorCorrectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    conversation_id: UUID
    message_id: UUID | None
    correction_type: str
    before_json: dict[str, Any]
    after_json: dict[str, Any]
    operator_id: UUID | None
    created_at: datetime


class AutomationSuggestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    source_correction_id: UUID | None
    suggested_rule_json: dict[str, Any]
    status: str
    created_at: datetime


class AutomationRuleStepRead(BaseModel):
    order: int
    label: str
    tier: str
    detail: str

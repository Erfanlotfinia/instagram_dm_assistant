from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TRLValidationRunRequest(BaseModel):
    reset_demo_data: bool = False
    scenario_limit: int | None = Field(default=None, ge=1, le=1000)


class TRLValidationResetResponse(BaseModel):
    deleted_runs: int
    deleted_conversations: int
    deleted_orders: int


class TRLValidationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    status: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    metrics_json: dict[str, Any]
    started_at: datetime
    completed_at: datetime | None
    created_by_user_id: UUID | None


class TRLValidationScenarioResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    scenario_id: str
    input_json: dict[str, Any]
    expected_json: dict[str, Any]
    actual_json: dict[str, Any]
    passed: bool
    failure_reasons: list[str]
    processing_time_ms: int
    conversation_id: UUID | None
    order_id: UUID | None
    created_at: datetime

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ReplayScenarioInput(BaseModel):
    item_key: str = Field(min_length=1, max_length=128)
    message_text: str = Field(min_length=1, max_length=2000)
    shared_post_url: str | None = Field(default=None, max_length=2048)
    instagram_user_id: str = Field(default="replay-customer", max_length=64)
    expected_json: dict[str, Any] = Field(default_factory=dict)


class ReplayRunRequest(BaseModel):
    label: str | None = Field(default=None, max_length=255)
    model_version: str | None = Field(default=None, max_length=128)
    prompt_version: str | None = Field(default=None, max_length=64)
    policy_version_id: UUID | None = None
    campaign: str | None = Field(default=None, max_length=128)
    scenarios: list[ReplayScenarioInput] = Field(min_length=1)
    conversation_id: UUID | None = None


class SimulatorRunItemRead(BaseModel):
    id: UUID
    run_id: UUID
    item_key: str
    input_json: dict[str, Any]
    expected_json: dict[str, Any]
    actual_json: dict[str, Any]
    diff_json: dict[str, Any]
    passed: bool
    trace_id: UUID | None
    conversation_id: UUID | None
    processing_time_ms: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SimulatorRunSummaryRead(BaseModel):
    id: UUID
    shop_id: UUID
    label: str | None
    source_type: str
    model_version: str
    prompt_version: str
    policy_version_id: UUID | None
    catalog_snapshot_hash: str
    status: str
    total_items: int
    passed_items: int
    failed_items: int
    diff_summary_json: dict[str, Any]
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class SimulatorRunDetailRead(SimulatorRunSummaryRead):
    items: list[SimulatorRunItemRead] = Field(default_factory=list)
    catalog_snapshot_json: dict[str, Any] = Field(default_factory=dict)


class ReplayRunResponse(BaseModel):
    run: SimulatorRunDetailRead

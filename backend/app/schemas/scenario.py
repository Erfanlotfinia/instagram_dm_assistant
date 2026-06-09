from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import ScenarioPackType


class ScenarioPackCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    pack_type: ScenarioPackType = ScenarioPackType.HANDCRAFTED
    description: str | None = None
    scenarios_json: list[dict[str, Any]] = Field(default_factory=list)
    is_golden: bool = False
    template: dict[str, Any] | None = None
    count: int | None = Field(default=None, ge=1, le=100)
    conversation_ids: list[UUID] | None = None


class ScenarioPackRead(BaseModel):
    id: UUID
    shop_id: UUID
    name: str
    pack_type: str
    description: str | None
    scenarios_json: list[dict[str, Any]]
    is_golden: bool
    created_by_user_id: UUID | None

    model_config = {"from_attributes": True}

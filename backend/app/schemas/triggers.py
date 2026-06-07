from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import TriggerSourceType


class TriggerRuleBase(BaseModel):
    instagram_account_id: UUID
    instagram_media_id: str | None = None
    source_type: TriggerSourceType = TriggerSourceType.COMMENT
    keyword: str = Field(min_length=1, max_length=128)
    response_template: str = Field(min_length=1)
    target_product_id: UUID | None = None
    is_active: bool = True


class TriggerRuleCreate(TriggerRuleBase):
    pass


class TriggerRuleUpdate(BaseModel):
    instagram_media_id: str | None = None
    source_type: TriggerSourceType | None = None
    keyword: str | None = Field(default=None, min_length=1, max_length=128)
    response_template: str | None = Field(default=None, min_length=1)
    target_product_id: UUID | None = None
    is_active: bool | None = None


class TriggerRuleRead(TriggerRuleBase):
    id: UUID
    shop_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TriggerPerformanceRead(BaseModel):
    trigger_id: UUID
    keyword: str
    source_type: TriggerSourceType
    impressions: int = 0
    dm_sent: int = 0
    paid_orders: int = 0
    revenue: Decimal = Decimal("0")
    conversion_rate: float = 0.0


class TriggerMatchRequest(BaseModel):
    instagram_account_id: UUID
    text: str
    source_type: TriggerSourceType = TriggerSourceType.COMMENT
    instagram_media_id: str | None = None
    instagram_user_id: str = "simulated-trigger-user"


class TriggerMatchResponse(BaseModel):
    matched: bool
    trigger_id: UUID | None = None
    response_text: str | None = None
    target_product_id: UUID | None = None
    conversation_id: UUID | None = None

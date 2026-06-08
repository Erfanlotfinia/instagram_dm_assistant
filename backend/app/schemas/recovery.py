from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecoveryRuleCreate(BaseModel):
    is_active: bool = True
    trigger_after_minutes: int = Field(default=60, ge=1, le=10080)
    max_attempts: int = Field(default=3, ge=1, le=10)
    message_template: str = Field(min_length=1)
    only_inside_allowed_messaging_window: bool = True


class RecoveryRuleUpdate(BaseModel):
    is_active: bool | None = None
    trigger_after_minutes: int | None = Field(default=None, ge=1, le=10080)
    max_attempts: int | None = Field(default=None, ge=1, le=10)
    message_template: str | None = Field(default=None, min_length=1)
    only_inside_allowed_messaging_window: bool | None = None


class RecoveryRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    is_active: bool
    trigger_after_minutes: int
    max_attempts: int
    message_template: str
    only_inside_allowed_messaging_window: bool
    created_at: datetime
    updated_at: datetime

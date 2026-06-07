from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import InstagramAccountStatus


class InstagramAccountCreate(BaseModel):
    ig_user_id: str = Field(min_length=1, max_length=64)
    username: str = Field(min_length=1, max_length=255)
    access_token: str = Field(min_length=1)
    page_id: str | None = Field(default=None, max_length=64)
    token_expires_at: datetime | None = None
    webhook_enabled: bool = False


class InstagramAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    ig_user_id: str
    page_id: str | None
    username: str
    token_expires_at: datetime | None
    webhook_enabled: bool
    status: InstagramAccountStatus
    created_at: datetime
    updated_at: datetime

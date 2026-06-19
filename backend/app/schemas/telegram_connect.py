from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import TelegramConnectionMode, TelegramConnectionSessionStatus


class TelegramConnectStartRequest(BaseModel):
    mode: TelegramConnectionMode = TelegramConnectionMode.BOT
    display_name: str | None = None
    channel_account_id: UUID | None = None
    managed_bot: bool = False


class TelegramConnectStartResponse(BaseModel):
    session_id: UUID
    expires_at: datetime
    status: TelegramConnectionSessionStatus
    deep_link: str | None = None
    suggested_bot_username: str | None = None
    managed_bot: bool = False


class TelegramConnectBotTokenRequest(BaseModel):
    bot_token: str = Field(min_length=1)
    webhook_secret: str | None = None


class TelegramConnectSessionRead(BaseModel):
    id: UUID
    shop_id: UUID
    mode: TelegramConnectionMode
    status: TelegramConnectionSessionStatus
    expires_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None
    channel_account_id: UUID | None = None
    bot_username: str | None = None
    bot_id: str | None = None
    telegram_business_enabled: bool = False
    deep_link: str | None = None
    suggested_bot_username: str | None = None
    managed_bot: bool = False
    metadata_json: dict = Field(default_factory=dict)

    model_config = {"from_attributes": True}

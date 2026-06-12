from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import (
    ChannelAccountStatus,
    ChannelMessageType,
    ChannelProvider,
    WebhookSecurityType,
)


class ChannelCapabilities(BaseModel):
    supports_webhook: bool = True
    supports_long_polling: bool = False
    supports_text: bool = True
    supports_images: bool = False
    supports_video: bool = False
    supports_voice: bool = False
    supports_files: bool = False
    supports_buttons: bool = False
    supports_reply_keyboard: bool = False
    supports_inline_keyboard: bool = False
    supports_templates: bool = False
    supports_payments: bool = False
    supports_catalog_messages: bool = False
    supports_message_edit: bool = False
    supports_delete_message: bool = False
    supports_typing_indicator: bool = False
    max_text_length: int = 1000
    webhook_security_type: WebhookSecurityType = WebhookSecurityType.UNKNOWN
    supports_customer_service_window: bool = False
    default_customer_service_window_hours: int | None = None


class MediaItem(BaseModel):
    id: str | None = None
    url: str | None = None
    mime_type: str | None = None
    file_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedInboundMessage(BaseModel):
    provider: ChannelProvider
    shop_id: UUID | None = None
    channel_account_id: UUID | None = None
    external_update_id: str | None = None
    external_message_id: str | None = None
    external_chat_id: str
    external_user_id: str
    username: str | None = None
    display_name: str | None = None
    phone: str | None = None
    message_type: ChannelMessageType = ChannelMessageType.UNKNOWN
    text: str | None = None
    caption: str | None = None
    media_items: list[MediaItem] = Field(default_factory=list)
    shared_post_url: str | None = None
    button_id: str | None = None
    button_text: str | None = None
    location: dict[str, Any] | None = None
    contact: dict[str, Any] | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=datetime.utcnow)


class OutboundButton(BaseModel):
    id: str
    text: str


class NormalizedOutboundMessage(BaseModel):
    provider: ChannelProvider
    channel_account_id: UUID
    external_chat_id: str
    message_type: ChannelMessageType = ChannelMessageType.TEXT
    text: str | None = None
    media_items: list[MediaItem] = Field(default_factory=list)
    buttons: list[OutboundButton] = Field(default_factory=list)
    template_name: str | None = None
    template_params: dict[str, Any] | None = None
    reply_to_external_message_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderSendResult(BaseModel):
    provider: ChannelProvider
    success: bool
    external_message_id: str | None = None
    raw_response: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False


class ChannelAccountCreate(BaseModel):
    provider: ChannelProvider
    display_name: str
    external_account_id: str | None = None
    phone_number_id: str | None = None
    bot_username: str | None = None
    bot_id: str | None = None
    webhook_verify_token: str | None = None
    webhook_secret: str | None = None
    access_token: str | None = None
    bot_token: str | None = None
    settings_json: dict[str, Any] = Field(default_factory=dict)


class ChannelAccountRead(BaseModel):
    id: UUID
    shop_id: UUID
    provider: ChannelProvider
    display_name: str
    external_account_id: str | None
    phone_number_id: str | None
    bot_username: str | None
    bot_id: str | None
    status: ChannelAccountStatus
    capabilities_json: dict[str, Any]
    settings_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebhookTestResponse(BaseModel):
    status: str = "ok"
    provider: ChannelProvider
    channel_account_id: UUID

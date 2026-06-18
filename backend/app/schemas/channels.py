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


class NormalizedMessage(BaseModel):
    """Modira core message envelope shared by all channel adapters.

    Adapters for Instagram, WhatsApp, Telegram, Bale, and Rubika normalize
    provider-specific webhook payloads into this shape before invoking the
    channel-agnostic social admin engine.
    """

    channel: ChannelProvider
    user_id: str
    conversation_id: str
    message_type: ChannelMessageType = ChannelMessageType.UNKNOWN
    content: str | None = None
    attachments: list[MediaItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_inbound(cls, message: NormalizedInboundMessage) -> NormalizedMessage:
        return cls(
            channel=message.provider,
            user_id=message.external_user_id,
            conversation_id=message.external_chat_id,
            message_type=message.message_type,
            content=message.text or message.caption,
            attachments=message.media_items,
            metadata={
                "external_update_id": message.external_update_id,
                "external_message_id": message.external_message_id,
                "shared_post_url": message.shared_post_url,
                "button_id": message.button_id,
                "raw_payload": message.raw_payload,
            },
        )


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
    webhook_url: str | None = None
    webhook_verify_token: str | None = None
    token_expires_at: datetime | None = None
    scopes: list[str] | None = None
    capabilities: dict[str, Any] | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class ChannelAccountUpdate(BaseModel):
    display_name: str | None = None
    external_account_id: str | None = None
    phone_number_id: str | None = None
    bot_username: str | None = None
    bot_id: str | None = None
    webhook_url: str | None = None
    webhook_verify_token: str | None = None
    token_expires_at: datetime | None = None
    scopes: list[str] | None = None
    capabilities: dict[str, Any] | None = None
    settings: dict[str, Any] | None = None
    status: ChannelAccountStatus | None = None


class ChannelAccountCredentials(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    bot_token: str | None = None
    webhook_secret: str | None = None
    webhook_verify_token: str | None = None
    token_expires_at: datetime | None = None


class ChannelAccountRead(BaseModel):
    id: UUID
    shop_id: UUID
    provider: ChannelProvider
    display_name: str
    external_account_id: str | None
    phone_number_id: str | None
    bot_username: str | None
    bot_id: str | None
    webhook_url: str | None
    status: ChannelAccountStatus
    capabilities: dict[str, Any] = Field(validation_alias="capabilities_json")
    settings: dict[str, Any] = Field(validation_alias="settings_json")
    token_configured: bool = False
    bot_token_configured: bool = False
    webhook_secret_configured: bool = False
    last_validation_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_account(cls, account: Any) -> "ChannelAccountRead":
        response = cls.model_validate(account)
        response.token_configured = bool(account.access_token_encrypted)
        response.bot_token_configured = bool(account.bot_token_encrypted)
        response.webhook_secret_configured = bool(account.webhook_secret_encrypted)
        return response


class WebhookTestResponse(BaseModel):
    status: str = "ok"
    provider: ChannelProvider
    channel_account_id: UUID

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import Request

from app.channels.base import ChannelProviderAdapter
from app.domain.enums import ChannelMessageType, ChannelProvider, WebhookSecurityType
from app.integrations.instagram_webhook import parse_instagram_webhook_payload
from app.schemas.channels import (
    ChannelCapabilities,
    MediaItem,
    NormalizedInboundMessage,
    NormalizedOutboundMessage,
    ProviderSendResult,
)


def _dt_from_ms(value: Any) -> datetime:
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
    except Exception:
        return datetime.now(UTC)


class StaticTokenAdapter(ChannelProviderAdapter):
    provider: ChannelProvider
    token: str | None = None
    webhook_secret: str | None = None

    async def verify_webhook(self, request: Request) -> bool:
        if self.webhook_secret:
            return (
                request.headers.get("X-Telegram-Bot-Api-Secret-Token") == self.webhook_secret
                or request.headers.get("X-Webhook-Secret") == self.webhook_secret
            )
        return True


class InstagramProviderAdapter(StaticTokenAdapter):
    provider = ChannelProvider.INSTAGRAM

    def __init__(self, app_secret: str | None = None) -> None:
        self.webhook_secret = app_secret

    async def verify_webhook(self, request: Request) -> bool:
        if not self.webhook_secret:
            return True
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256")
        if not signature or not signature.startswith("sha256="):
            return False
        digest = hmac.new(self.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, f"sha256={digest}")

    def parse_inbound_update(
        self, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> list[NormalizedInboundMessage]:
        messages: list[NormalizedInboundMessage] = []
        for parsed in parse_instagram_webhook_payload(payload):
            message_type = ChannelMessageType.TEXT
            media_items: list[MediaItem] = []
            if parsed.shared_post_url:
                message_type = ChannelMessageType.INTERACTIVE
            elif parsed.attachment_url:
                message_type = ChannelMessageType.IMAGE
                media_items.append(MediaItem(url=parsed.attachment_url))
            messages.append(
                NormalizedInboundMessage(
                    provider=self.provider,
                    external_update_id=parsed.message_id,
                    external_message_id=parsed.message_id,
                    external_chat_id=parsed.sender_id,
                    external_user_id=parsed.sender_id,
                    message_type=message_type,
                    text=parsed.text,
                    media_items=media_items,
                    shared_post_url=parsed.shared_post_url,
                    raw_payload=parsed.messaging_event,
                    received_at=parsed.timestamp or datetime.now(UTC),
                )
            )
        return messages

    async def send_message(self, message: NormalizedOutboundMessage) -> ProviderSendResult:
        return ProviderSendResult(
            provider=self.provider,
            success=False,
            error_code="not_configured",
            error_message="Instagram outbound is still handled by InstagramOutboundSender",
            retryable=False,
        )

    def get_capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            supports_images=True,
            supports_video=True,
            supports_buttons=True,
            supports_typing_indicator=True,
            max_text_length=1000,
            webhook_security_type=WebhookSecurityType.SIGNATURE,
        )


class WhatsAppProviderAdapter(StaticTokenAdapter):
    provider = ChannelProvider.WHATSAPP

    def __init__(
        self,
        access_token: str | None = None,
        phone_number_id: str | None = None,
        verify_token: str | None = None,
    ) -> None:
        self.token = access_token
        self.phone_number_id = phone_number_id
        self.verify_token = verify_token

    def parse_inbound_update(
        self, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> list[NormalizedInboundMessage]:
        result: list[NormalizedInboundMessage] = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                phone_id = value.get("metadata", {}).get("phone_number_id")
                contacts = {c.get("wa_id"): c for c in value.get("contacts", [])}
                for msg in value.get("messages", []):
                    sender = str(msg.get("from"))
                    msg_type = msg.get("type", "unknown")
                    text = msg.get("text", {}).get("body")
                    button = (
                        msg.get("button")
                        or msg.get("interactive", {}).get("button_reply")
                        or msg.get("interactive", {}).get("list_reply")
                        or {}
                    )
                    media_items = []
                    if msg_type in {"image", "video", "audio", "voice", "document"}:
                        media = msg.get(msg_type, {})
                        media_items.append(
                            MediaItem(
                                id=media.get("id"),
                                mime_type=media.get("mime_type"),
                                file_name=media.get("filename"),
                            )
                        )
                    contact = contacts.get(sender, {})
                    result.append(
                        NormalizedInboundMessage(
                            provider=self.provider,
                            external_update_id=msg.get("id"),
                            external_message_id=msg.get("id"),
                            external_chat_id=sender,
                            external_user_id=sender,
                            display_name=(contact.get("profile") or {}).get("name"),
                            phone=sender,
                            message_type=ChannelMessageType(msg_type)
                            if msg_type in ChannelMessageType._value2member_map_
                            else ChannelMessageType.UNKNOWN,
                            text=text,
                            media_items=media_items,
                            button_id=button.get("id"),
                            button_text=button.get("text") or button.get("title"),
                            raw_payload={
                                "message": msg,
                                "phone_number_id": phone_id,
                                "contact": contact,
                            },
                            received_at=_dt_from_ms(
                                int(msg.get("timestamp", 0)) * 1000
                                if msg.get("timestamp")
                                else None
                            ),
                        )
                    )
        return result

    async def send_message(self, message: NormalizedOutboundMessage) -> ProviderSendResult:
        if not self.token or not self.phone_number_id:
            return ProviderSendResult(
                provider=self.provider,
                success=False,
                error_code="missing_credentials",
                error_message="WhatsApp access token or phone_number_id is missing",
            )
        payload = {
            "messaging_product": "whatsapp",
            "to": message.external_chat_id,
            "type": "text",
            "text": {"body": message.text or ""},
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"https://graph.facebook.com/v20.0/{self.phone_number_id}/messages",
                headers={"Authorization": f"Bearer {self.token}"},
                json=payload,
            )
        data = response.json()
        return ProviderSendResult(
            provider=self.provider,
            success=response.is_success,
            external_message_id=((data.get("messages") or [{}])[0]).get("id"),
            raw_response=data,
            error_code=None if response.is_success else str(response.status_code),
            error_message=None if response.is_success else data.get("error", {}).get("message"),
            retryable=response.status_code >= 500,
        )

    def get_capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            supports_images=True,
            supports_video=True,
            supports_voice=True,
            supports_files=True,
            supports_buttons=True,
            supports_templates=True,
            supports_catalog_messages=True,
            max_text_length=4096,
            webhook_security_type=WebhookSecurityType.VERIFY_TOKEN,
            supports_customer_service_window=True,
            default_customer_service_window_hours=24,
        )


class TelegramProviderAdapter(StaticTokenAdapter):
    provider = ChannelProvider.TELEGRAM
    api_base = "https://api.telegram.org"

    def __init__(self, bot_token: str | None = None, webhook_secret: str | None = None) -> None:
        self.token = bot_token
        self.webhook_secret = webhook_secret

    def parse_inbound_update(
        self, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> list[NormalizedInboundMessage]:
        msg = (
            payload.get("message")
            or payload.get("edited_message")
            or payload.get("callback_query", {}).get("message")
            or {}
        )
        callback = payload.get("callback_query")
        if not msg and not callback:
            return []
        user = callback.get("from") if callback else msg.get("from", {})
        chat = msg.get("chat", {})
        text = msg.get("text") or msg.get("caption")
        media_items = []
        msg_type = ChannelMessageType.TEXT if text else ChannelMessageType.UNKNOWN
        for key, ctype in [
            ("photo", ChannelMessageType.IMAGE),
            ("video", ChannelMessageType.VIDEO),
            ("voice", ChannelMessageType.VOICE),
            ("audio", ChannelMessageType.AUDIO),
            ("document", ChannelMessageType.DOCUMENT),
        ]:
            if key in msg:
                msg_type = ctype
                item = msg[key][-1] if isinstance(msg[key], list) else msg[key]
                media_items.append(
                    MediaItem(
                        id=item.get("file_id"),
                        file_name=item.get("file_name"),
                        mime_type=item.get("mime_type"),
                    )
                )
        return [
            NormalizedInboundMessage(
                provider=self.provider,
                external_update_id=str(payload.get("update_id")),
                external_message_id=str(msg.get("message_id") or callback.get("id")),
                external_chat_id=str(chat.get("id")),
                external_user_id=str(user.get("id")),
                username=user.get("username"),
                display_name=" ".join(filter(None, [user.get("first_name"), user.get("last_name")]))
                or None,
                message_type=ChannelMessageType.BUTTON_CALLBACK if callback else msg_type,
                text=text,
                caption=msg.get("caption"),
                media_items=media_items,
                button_id=callback.get("data") if callback else None,
                button_text=callback.get("data") if callback else None,
                raw_payload=payload,
                received_at=datetime.fromtimestamp(
                    msg.get("date", datetime.now(UTC).timestamp()), tz=UTC
                ),
            )
        ]

    async def send_message(self, message: NormalizedOutboundMessage) -> ProviderSendResult:
        if not self.token:
            return ProviderSendResult(
                provider=self.provider,
                success=False,
                error_code="missing_bot_token",
                error_message="Bot token is missing",
            )
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{self.api_base}/bot{self.token}/sendMessage",
                json={"chat_id": message.external_chat_id, "text": message.text or ""},
            )
        data = response.json()
        return ProviderSendResult(
            provider=self.provider,
            success=response.is_success and data.get("ok", False),
            external_message_id=str(data.get("result", {}).get("message_id"))
            if data.get("result")
            else None,
            raw_response=data,
            error_code=None if response.is_success else str(response.status_code),
            error_message=None if response.is_success else data.get("description"),
            retryable=response.status_code >= 500,
        )

    def get_capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            supports_long_polling=True,
            supports_images=True,
            supports_video=True,
            supports_voice=True,
            supports_files=True,
            supports_buttons=True,
            supports_reply_keyboard=True,
            supports_inline_keyboard=True,
            supports_message_edit=True,
            supports_delete_message=True,
            supports_typing_indicator=True,
            max_text_length=4096,
            webhook_security_type=WebhookSecurityType.SECRET_TOKEN_HEADER,
        )


class BaleProviderAdapter(TelegramProviderAdapter):
    provider = ChannelProvider.BALE
    api_base = "https://tapi.bale.ai"


class RubikaProviderAdapter(TelegramProviderAdapter):
    provider = ChannelProvider.RUBIKA
    api_base = "https://botapi.rubika.ir"

    def parse_inbound_update(
        self, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> list[NormalizedInboundMessage]:
        update = (
            payload.get("receiveUpdate")
            or payload.get("receiveInlineMessage")
            or payload.get("update")
            or payload
        )
        if "message" in update or "update_id" in update:
            return super().parse_inbound_update(update, headers)
        chat_id = str(
            update.get("chat_id")
            or update.get("chat", {}).get("id")
            or update.get("sender_id")
            or ""
        )
        user_id = str(update.get("sender_id") or update.get("from", {}).get("id") or chat_id)
        if not chat_id:
            return []
        return [
            NormalizedInboundMessage(
                provider=self.provider,
                external_update_id=str(update.get("update_id") or update.get("message_id")),
                external_message_id=str(update.get("message_id") or update.get("id")),
                external_chat_id=chat_id,
                external_user_id=user_id,
                message_type=ChannelMessageType.TEXT
                if update.get("text")
                else ChannelMessageType.UNKNOWN,
                text=update.get("text"),
                raw_payload=payload,
            )
        ]

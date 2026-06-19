from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import Request

from app.channels.base import ChannelProviderAdapter
from app.core.config import get_settings
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
        if not self.webhook_secret:
            return False
        return (
            request.headers.get("X-Telegram-Bot-Api-Secret-Token") == self.webhook_secret
            or request.headers.get("X-Webhook-Secret") == self.webhook_secret
        )


class InstagramProviderAdapter(StaticTokenAdapter):
    provider = ChannelProvider.INSTAGRAM

    def __init__(
        self,
        access_token: str | None = None,
        app_secret: str | None = None,
        api_version: str | None = None,
        api_base_url: str | None = None,
    ) -> None:
        settings = get_settings()
        self.token = access_token
        self.webhook_secret = app_secret
        self.api_version = api_version or settings.meta_graph_api_version
        self.api_base_url = (api_base_url or settings.meta_graph_api_base_url).rstrip("/")

    async def verify_webhook(self, request: Request) -> bool:
        if not self.webhook_secret:
            return False
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

    async def send_message(
        self, message: NormalizedOutboundMessage, account: Any | None = None
    ) -> ProviderSendResult:
        if not self.token:
            return ProviderSendResult(
                provider=self.provider,
                success=False,
                error_code="missing_credentials",
                error_message="Instagram access token is missing",
            )
        if message.message_type != ChannelMessageType.TEXT:
            return ProviderSendResult(
                provider=self.provider,
                success=False,
                error_code="unsupported_provider_capability",
                error_message="Instagram outbound currently supports text messages only",
            )
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.api_base_url}/{self.api_version}/me/messages",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={
                        "recipient": {"id": message.external_chat_id},
                        "message": {"text": message.text or ""},
                    },
                )
            data = response.json()
        except httpx.RequestError:
            return ProviderSendResult(
                provider=self.provider,
                success=False,
                error_code="network_error",
                error_message="Instagram request failed",
                retryable=True,
            )
        error = data.get("error", {}) if isinstance(data, dict) else {}
        success = response.is_success and isinstance(data, dict) and bool(data.get("message_id"))
        return ProviderSendResult(
            provider=self.provider,
            success=success,
            external_message_id=data.get("message_id") if success else None,
            raw_response=data if isinstance(data, dict) else {"status_code": response.status_code},
            error_code=None if success else str(error.get("code") or response.status_code),
            error_message=None if success else error.get("message", "Instagram send failed"),
            retryable=response.status_code == 429 or response.status_code >= 500,
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

    async def validate_credentials(self) -> bool:
        if not self.token:
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.api_base_url}/{self.api_version}/me",
                    params={"access_token": self.token, "fields": "id"},
                )
            if not response.is_success:
                return False
            data = response.json()
            return isinstance(data, dict) and bool(data.get("id"))
        except httpx.RequestError:
            return False


class WhatsAppProviderAdapter(StaticTokenAdapter):
    provider = ChannelProvider.WHATSAPP

    def __init__(
        self,
        access_token: str | None = None,
        phone_number_id: str | None = None,
        verify_token: str | None = None,
        app_secret: str | None = None,
        webhook_secret: str | None = None,
        api_version: str | None = None,
        api_base_url: str | None = None,
    ) -> None:
        settings = get_settings()
        self.token = access_token
        self.phone_number_id = phone_number_id
        self.verify_token = verify_token
        self.webhook_secret = app_secret or webhook_secret
        self.api_version = api_version or settings.meta_graph_api_version
        self.api_base_url = (api_base_url or settings.meta_graph_api_base_url).rstrip("/")

    async def verify_webhook(self, request: Request) -> bool:
        if not self.webhook_secret:
            return False
        body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256")
        if not signature or not signature.startswith("sha256="):
            return False
        digest = hmac.new(self.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, f"sha256={digest}")

    def parse_inbound_update(
        self, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> list[NormalizedInboundMessage]:
        result: list[NormalizedInboundMessage] = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                metadata = value.get("metadata", {})
                phone_id = metadata.get("phone_number_id")
                contacts = {c.get("wa_id"): c for c in value.get("contacts", [])}
                for status_item in value.get("statuses", []):
                    result.append(
                        NormalizedInboundMessage(
                            provider=self.provider,
                            external_update_id=status_item.get("id"),
                            external_message_id=status_item.get("id") or "status",
                            external_chat_id=str(status_item.get("recipient_id") or phone_id or ""),
                            external_user_id=str(status_item.get("recipient_id") or ""),
                            message_type=ChannelMessageType.UNKNOWN,
                            raw_payload={
                                "event_type": "delivery_status",
                                "status": status_item,
                                "phone_number_id": phone_id,
                                "metadata": metadata,
                            },
                            received_at=_dt_from_ms(
                                int(status_item.get("timestamp", 0)) * 1000
                                if status_item.get("timestamp")
                                else None
                            ),
                        )
                    )
                for msg in value.get("messages", []):
                    sender = str(msg.get("from"))
                    msg_type = msg.get("type", "unknown")
                    text = (msg.get("text") or {}).get("body")
                    caption = None
                    media_items: list[MediaItem] = []
                    location = msg.get("location") if msg_type == "location" else None
                    contact_payload = (
                        (msg.get("contacts") or msg.get("contact"))
                        if msg_type == "contacts"
                        else None
                    )
                    button_id = button_text = None
                    order = msg.get("order") if msg_type == "order" else None
                    if msg_type in {"image", "video", "audio", "voice", "document"}:
                        media_key = (
                            "audio" if msg_type == "voice" and "voice" not in msg else msg_type
                        )
                        media = msg.get(media_key, {})
                        caption = media.get("caption")
                        media_items.append(
                            MediaItem(
                                id=media.get("id"),
                                mime_type=media.get("mime_type"),
                                file_name=media.get("filename"),
                            )
                        )
                    if msg_type == "interactive":
                        interactive = msg.get("interactive", {})
                        reply = (
                            interactive.get("button_reply") or interactive.get("list_reply") or {}
                        )
                        button_id = reply.get("id")
                        button_text = reply.get("title") or reply.get("text")
                    elif msg_type == "button":
                        button = msg.get("button", {})
                        button_id = button.get("payload") or button.get("id")
                        button_text = button.get("text")
                    contact = contacts.get(sender, {})
                    normalized_type = "contact" if msg_type == "contacts" else msg_type
                    result.append(
                        NormalizedInboundMessage(
                            provider=self.provider,
                            external_update_id=msg.get("id"),
                            external_message_id=msg.get("id"),
                            external_chat_id=sender,
                            external_user_id=sender,
                            display_name=(contact.get("profile") or {}).get("name"),
                            phone=sender,
                            message_type=(
                                ChannelMessageType(normalized_type)
                                if normalized_type in ChannelMessageType._value2member_map_
                                else ChannelMessageType.UNKNOWN
                            ),
                            text=text,
                            caption=caption,
                            media_items=media_items,
                            button_id=button_id,
                            button_text=button_text,
                            location=location,
                            contact=({"contacts": contact_payload} if contact_payload else None),
                            raw_payload={
                                "message": msg,
                                "phone_number_id": phone_id,
                                "contact": contact,
                                "metadata": metadata,
                                "order": order,
                            },
                            received_at=_dt_from_ms(
                                int(msg.get("timestamp", 0)) * 1000
                                if msg.get("timestamp")
                                else None
                            ),
                        )
                    )
        return result

    def _payload_for_message(self, message: NormalizedOutboundMessage) -> dict[str, Any]:
        base: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": message.external_chat_id,
        }
        if message.template_name:
            language = message.metadata.get("language_code") or "en_US"
            base.update(
                {
                    "type": "template",
                    "template": {
                        "name": message.template_name,
                        "language": {"code": language},
                    },
                }
            )
            if message.template_params:
                base["template"]["components"] = message.template_params.get("components", [])
            return base
        if message.buttons:
            base.update(
                {
                    "type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": message.text or ""},
                        "action": {
                            "buttons": [
                                {
                                    "type": "reply",
                                    "reply": {"id": b.id, "title": b.text},
                                }
                                for b in message.buttons[:3]
                            ]
                        },
                    },
                }
            )
            return base
        if (
            message.message_type
            in {
                ChannelMessageType.IMAGE,
                ChannelMessageType.VIDEO,
                ChannelMessageType.AUDIO,
                ChannelMessageType.DOCUMENT,
            }
            and message.media_items
        ):
            media = message.media_items[0]
            key = message.message_type.value
            media_payload = {"id": media.id} if media.id else {"link": media.url}
            if message.text and key in {"image", "video", "document"}:
                media_payload["caption"] = message.text
            base.update({"type": key, key: media_payload})
            return base
        base.update({"type": "text", "text": {"body": message.text or ""}})
        return base

    async def send_message(
        self, message: NormalizedOutboundMessage, account: Any | None = None
    ) -> ProviderSendResult:
        if not self.token or not self.phone_number_id:
            return ProviderSendResult(
                provider=self.provider,
                success=False,
                error_code="missing_credentials",
                error_message="WhatsApp access token or phone_number_id is missing",
            )
        if message.message_type == ChannelMessageType.ORDER:
            return ProviderSendResult(
                provider=self.provider,
                success=False,
                error_code="unsupported_catalog_message",
                error_message="WhatsApp product/catalog outbound requires catalog integration",
                retryable=False,
            )
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.api_base_url}/{self.api_version}/{self.phone_number_id}/messages",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json=self._payload_for_message(message),
                )
            data = response.json()
        except httpx.RequestError as exc:
            return ProviderSendResult(
                provider=self.provider,
                success=False,
                error_code="network_error",
                error_message=str(exc),
                retryable=True,
            )
        retryable = response.status_code == 429 or response.status_code >= 500
        error = data.get("error", {}) if isinstance(data, dict) else {}
        return ProviderSendResult(
            provider=self.provider,
            success=response.is_success,
            external_message_id=(
                ((data.get("messages") or [{}])[0]).get("id") if isinstance(data, dict) else None
            ),
            raw_response=data if isinstance(data, dict) else {"text": response.text},
            error_code=(
                None if response.is_success else str(error.get("code") or response.status_code)
            ),
            error_message=(None if response.is_success else error.get("message", response.text)),
            retryable=retryable,
        )

    def get_capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            supports_images=True,
            supports_video=True,
            supports_voice=True,
            supports_files=True,
            supports_buttons=True,
            supports_templates=True,
            supports_catalog_messages=False,
            max_text_length=4096,
            webhook_security_type=WebhookSecurityType.SIGNATURE,
            supports_customer_service_window=True,
            default_customer_service_window_hours=24,
        )


class TelegramProviderAdapter(StaticTokenAdapter):
    provider = ChannelProvider.TELEGRAM
    api_base = "https://api.telegram.org"

    def __init__(
        self,
        bot_token: str | None = None,
        webhook_secret: str | None = None,
        local_base_url: str | None = None,
    ) -> None:
        self.token = bot_token
        self.webhook_secret = webhook_secret
        self.api_base = (local_base_url or self.api_base).rstrip("/")

    def parse_inbound_update(
        self, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> list[NormalizedInboundMessage]:
        edited = payload.get("edited_message")
        business = payload.get("business_message")
        msg = (
            payload.get("message")
            or edited
            or business
            or payload.get("callback_query", {}).get("message")
            or {}
        )
        callback = payload.get("callback_query")
        if not msg and not callback:
            return []
        user = callback.get("from") if callback else msg.get("from", {})
        chat = msg.get("chat", {})
        text = callback.get("data") if callback else (msg.get("text") or msg.get("caption"))
        media_items: list[MediaItem] = []
        msg_type = ChannelMessageType.TEXT if msg.get("text") else ChannelMessageType.UNKNOWN
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
                        metadata={
                            "file_unique_id": item.get("file_unique_id"),
                            "file_size": item.get("file_size"),
                        },
                    )
                )
        if msg.get("location"):
            msg_type = ChannelMessageType.LOCATION
        if msg.get("contact"):
            msg_type = ChannelMessageType.CONTACT
        external_message_id = str(callback.get("id") if callback else msg.get("message_id"))
        raw_payload = {
            **payload,
            "is_edited_message": bool(edited),
            "is_business_message": bool(business),
            "chat_type": chat.get("type"),
        }
        return [
            NormalizedInboundMessage(
                provider=self.provider,
                external_update_id=str(payload.get("update_id")),
                external_message_id=external_message_id,
                external_chat_id=str(chat.get("id")),
                external_user_id=str(user.get("id")),
                username=user.get("username"),
                display_name=" ".join(filter(None, [user.get("first_name"), user.get("last_name")]))
                or None,
                message_type=(ChannelMessageType.BUTTON_CALLBACK if callback else msg_type),
                text=text,
                caption=msg.get("caption"),
                media_items=media_items,
                button_id=callback.get("data") if callback else None,
                button_text=callback.get("data") if callback else None,
                location=msg.get("location"),
                contact=msg.get("contact"),
                raw_payload=raw_payload,
                received_at=datetime.fromtimestamp(
                    msg.get("date", datetime.now(UTC).timestamp()), tz=UTC
                ),
            )
        ]

    def _method_url(self, method: str) -> str:
        return f"{self.api_base}/bot{self.token}/{method}"

    async def _post_method(self, method: str, payload: dict[str, Any]) -> ProviderSendResult:
        if not self.token:
            return ProviderSendResult(
                provider=self.provider,
                success=False,
                error_code="missing_bot_token",
                error_message="Bot token is missing",
            )
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(self._method_url(method), json=payload)
            data = response.json()
        except httpx.RequestError as exc:
            return ProviderSendResult(
                provider=self.provider,
                success=False,
                error_code="network_error",
                error_message=str(exc),
                retryable=True,
            )
        retryable = (
            response.status_code == 429
            or response.status_code >= 500
            or (
                isinstance(data, dict) and data.get("parameters", {}).get("retry_after") is not None
            )
        )
        ok = response.is_success and isinstance(data, dict) and data.get("ok", False)
        return ProviderSendResult(
            provider=self.provider,
            success=ok,
            external_message_id=(
                str(data.get("result", {}).get("message_id"))
                if ok
                and isinstance(data.get("result"), dict)
                and data.get("result", {}).get("message_id") is not None
                else None
            ),
            raw_response=data if isinstance(data, dict) else {"text": response.text},
            error_code=(
                None
                if ok
                else (
                    str(data.get("error_code", response.status_code))
                    if isinstance(data, dict)
                    else str(response.status_code)
                )
            ),
            error_message=(
                None
                if ok
                else (
                    data.get("description", response.text)
                    if isinstance(data, dict)
                    else response.text
                )
            ),
            retryable=retryable,
        )

    async def send_message(
        self, message: NormalizedOutboundMessage, account: Any | None = None
    ) -> ProviderSendResult:
        if message.message_type == ChannelMessageType.BUTTON_CALLBACK and message.metadata.get(
            "callback_query_id"
        ):
            return await self._post_method(
                "answerCallbackQuery",
                {
                    "callback_query_id": message.metadata["callback_query_id"],
                    "text": message.text or "",
                },
            )
        if message.metadata.get("chat_action"):
            return await self._post_method(
                "sendChatAction",
                {
                    "chat_id": message.external_chat_id,
                    "action": message.metadata.get("chat_action", "typing"),
                },
            )
        if message.message_type == ChannelMessageType.IMAGE and message.media_items:
            media = message.media_items[0]
            return await self._post_method(
                "sendPhoto",
                {
                    "chat_id": message.external_chat_id,
                    "photo": media.id or media.url,
                    "caption": message.text,
                },
            )
        if message.message_type == ChannelMessageType.DOCUMENT and message.media_items:
            media = message.media_items[0]
            return await self._post_method(
                "sendDocument",
                {
                    "chat_id": message.external_chat_id,
                    "document": media.id or media.url,
                    "caption": message.text,
                },
            )
        payload: dict[str, Any] = {
            "chat_id": message.external_chat_id,
            "text": message.text or "",
        }
        if message.buttons:
            payload["reply_markup"] = {
                "inline_keyboard": [
                    [{"text": button.text, "callback_data": button.id}]
                    for button in message.buttons
                ]
            }
        return await self._post_method("sendMessage", payload)

    async def send_typing_or_chat_action(
        self, external_chat_id: str, action: str = "typing"
    ) -> ProviderSendResult:
        return await self._post_method(
            "sendChatAction", {"chat_id": external_chat_id, "action": action}
        )

    async def configure_webhook(
        self, webhook_url: str, secret: str | None = None
    ) -> dict[str, Any]:
        result = await self._post_method(
            "setWebhook",
            {"url": webhook_url, **({"secret_token": secret} if secret else {})},
        )
        return result.raw_response or {"ok": result.success}

    async def delete_webhook(self) -> dict[str, Any]:
        result = await self._post_method("deleteWebhook", {})
        return result.raw_response or {"ok": result.success}

    async def get_webhook_info(self) -> dict[str, Any]:
        result = await self._post_method("getWebhookInfo", {})
        return result.raw_response or {"ok": result.success}

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

    def __init__(
        self,
        bot_token: str | None = None,
        webhook_secret: str | None = None,
        local_base_url: str | None = None,
    ) -> None:
        super().__init__(
            bot_token=bot_token,
            webhook_secret=webhook_secret,
            local_base_url=local_base_url,
        )


class RubikaProviderAdapter(TelegramProviderAdapter):
    provider = ChannelProvider.RUBIKA
    api_base = "https://botapi.rubika.ir/v3"

    def __init__(
        self,
        bot_token: str | None = None,
        webhook_secret: str | None = None,
        local_base_url: str | None = None,
    ) -> None:
        super().__init__(
            bot_token=bot_token,
            webhook_secret=webhook_secret,
            local_base_url=local_base_url,
        )

    def _method_url(self, method: str) -> str:
        return f"{self.api_base}/{self.token}/{method}"

    def parse_inbound_update(
        self, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> list[NormalizedInboundMessage]:
        update = (
            payload.get("receiveUpdate")
            or payload.get("receiveInlineMessage")
            or payload.get("update")
            or payload
        )
        if "message" in update or "callback_query" in update:
            return super().parse_inbound_update(update, headers)
        button = update.get("button") or update.get("button_event") or {}
        text = update.get("text") or button.get("text") or button.get("title")
        button_id = button.get("id") or button.get("button_id") or update.get("button_id")
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
                message_type=(
                    ChannelMessageType.BUTTON_CALLBACK
                    if button_id
                    else ChannelMessageType.TEXT
                    if text
                    else ChannelMessageType.UNKNOWN
                ),
                text=text,
                button_id=button_id,
                button_text=button.get("text") or button.get("title"),
                raw_payload=payload,
            )
        ]

    async def send_message(
        self, message: NormalizedOutboundMessage, account: Any | None = None
    ) -> ProviderSendResult:
        payload: dict[str, Any] = {
            "chat_id": message.external_chat_id,
            "text": message.text or "",
        }
        if message.buttons:
            payload["inline_keypad"] = {
                "rows": [
                    {
                        "buttons": [
                            {
                                "id": button.id,
                                "type": "Simple",
                                "button_text": button.text,
                            }
                        ]
                    }
                    for button in message.buttons
                ]
            }
        return await self._post_method("sendMessage", payload)

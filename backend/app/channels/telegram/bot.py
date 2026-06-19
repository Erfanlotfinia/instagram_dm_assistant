from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.channels.telegram.base import TelegramAdapterBase
from app.domain.enums import ChannelMessageType, ChannelProvider, WebhookSecurityType
from app.schemas.channels import (
    ChannelCapabilities,
    MediaItem,
    NormalizedInboundMessage,
    NormalizedOutboundMessage,
    ProviderSendResult,
)

DEFAULT_ALLOWED_UPDATES = [
    "message",
    "edited_message",
    "callback_query",
    "business_connection",
    "business_message",
    "edited_business_message",
    "deleted_business_messages",
]


def _normalize_message_payload(
    payload: dict[str, Any],
    msg: dict[str, Any],
    callback: dict[str, Any] | None,
    edited: dict[str, Any] | None,
    business: dict[str, Any] | None,
    provider: ChannelProvider = ChannelProvider.TELEGRAM,
) -> NormalizedInboundMessage | None:
    if not msg and not callback:
        return None
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
    business_connection_id = msg.get("business_connection_id")
    raw_payload = {
        **payload,
        "is_edited_message": bool(edited),
        "is_business_message": bool(business),
        "chat_type": chat.get("type"),
        "business_connection_id": business_connection_id,
    }
    return NormalizedInboundMessage(
        provider=provider,
        external_update_id=str(payload.get("update_id")),
        external_message_id=external_message_id,
        external_chat_id=str(chat.get("id")),
        external_user_id=str(user.get("id")),
        username=user.get("username"),
        display_name=" ".join(filter(None, [user.get("first_name"), user.get("last_name")])) or None,
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


class TelegramBotAdapter(TelegramAdapterBase):
    def receive_message(
        self, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> list[NormalizedInboundMessage]:
        return self.parse_inbound_update(payload, headers)

    def parse_inbound_update(
        self, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> list[NormalizedInboundMessage]:
        if payload.get("business_connection") or payload.get("deleted_business_messages"):
            return []
        edited = payload.get("edited_message")
        business = payload.get("business_message")
        edited_business = payload.get("edited_business_message")
        msg = (
            payload.get("message")
            or edited
            or payload.get("callback_query", {}).get("message")
            or {}
        )
        callback = payload.get("callback_query")
        if business or edited_business:
            return []
        normalized = _normalize_message_payload(
            payload, msg, callback, edited, business, provider=self.provider
        )
        return [normalized] if normalized else []

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

    async def mark_read(
        self,
        external_chat_id: str,
        external_message_id: str,
        business_connection_id: str | None = None,
    ) -> ProviderSendResult:
        return ProviderSendResult(
            provider=self.provider,
            success=True,
            raw_response={"skipped": "bot_mode_no_read_api"},
        )

    async def sync_metadata(self, account: Any) -> dict[str, Any]:
        me = await self._get_me()
        if me and account is not None:
            account.bot_username = me.get("username") or account.bot_username
            account.bot_id = str(me.get("id")) if me.get("id") is not None else account.bot_id
            account.external_account_id = account.bot_id
        return {"bot": me}

    async def validate_connection(self, account: Any | None = None) -> bool:
        me = await self._get_me()
        return bool(me.get("id"))

    async def validate_credentials(self) -> bool:
        return await self.validate_connection()

    def get_capabilities(self, account: Any | None = None) -> ChannelCapabilities:
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
            supports_private_chats=True,
            supports_groups=True,
            supports_supergroups=True,
            supports_channels=False,
            supports_business_chats=False,
            chat_types=["private", "group", "supergroup"],
        )

    async def send_typing_or_chat_action(
        self, external_chat_id: str, action: str = "typing"
    ) -> ProviderSendResult:
        return await self._post_method(
            "sendChatAction", {"chat_id": external_chat_id, "action": action}
        )

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.channels.telegram.bot import _normalize_message_payload, TelegramBotAdapter
from app.domain.enums import ChannelMessageType, WebhookSecurityType
from app.schemas.channels import (
    ChannelCapabilities,
    NormalizedInboundMessage,
    NormalizedOutboundMessage,
    ProviderSendResult,
)


class TelegramBusinessAdapter(TelegramBotAdapter):
    def receive_message(
        self, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> list[NormalizedInboundMessage]:
        return self.parse_inbound_update(payload, headers)

    def parse_inbound_update(
        self, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> list[NormalizedInboundMessage]:
        if payload.get("business_connection") or payload.get("deleted_business_messages"):
            return []
        if payload.get("edited_business_message"):
            return []
        business = payload.get("business_message")
        if not business:
            return []
        normalized = _normalize_message_payload(
            payload, business, None, None, business, provider=self.provider
        )
        return [normalized] if normalized else []

    async def send_message(
        self, message: NormalizedOutboundMessage, account: Any | None = None
    ) -> ProviderSendResult:
        from app.schemas.channels import ProviderSendResult

        business_connection_id = (
            message.metadata.get("business_connection_id")
            or (account.telegram_business_connection_id if account else None)
        )
        if not business_connection_id:
            return ProviderSendResult(
                provider=self.provider,
                success=False,
                error_code="missing_business_connection_id",
                error_message="Business connection id is required",
            )
        if message.message_type == ChannelMessageType.IMAGE and message.media_items:
            media = message.media_items[0]
            return await self._post_method(
                "sendPhoto",
                {
                    "chat_id": message.external_chat_id,
                    "photo": media.id or media.url,
                    "caption": message.text,
                    "business_connection_id": business_connection_id,
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
                    "business_connection_id": business_connection_id,
                },
            )
        payload: dict[str, Any] = {
            "chat_id": message.external_chat_id,
            "text": message.text or "",
            "business_connection_id": business_connection_id,
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
        if not business_connection_id:
            return ProviderSendResult(
                provider=self.provider,
                success=False,
                error_code="missing_business_connection_id",
                error_message="Business connection id is required",
            )
        return await self._post_method(
            "readBusinessMessage",
            {
                "business_connection_id": business_connection_id,
                "chat_id": int(external_chat_id),
                "message_id": int(external_message_id),
            },
        )

    async def sync_metadata(self, account: Any) -> dict[str, Any]:
        result = await super().sync_metadata(account)
        if account and account.telegram_business_connection_id:
            conn_result = await self._post_method(
                "getBusinessConnection",
                {"business_connection_id": account.telegram_business_connection_id},
            )
            if conn_result.success and isinstance(conn_result.raw_response, dict):
                conn = conn_result.raw_response.get("result", {})
                result["business_connection"] = conn
                rights = conn.get("rights", {})
                account.telegram_rights_json = rights
                account.telegram_business_enabled = bool(conn.get("is_enabled"))
                user = conn.get("user", {})
                if user.get("id"):
                    account.telegram_user_id = str(user.get("id"))
                if user.get("username"):
                    account.telegram_username = user.get("username")
        if account:
            account.telegram_last_sync_at = datetime.now(UTC)
            caps = self.get_capabilities(account)
            account.telegram_capabilities_json = caps.model_dump(mode="json")
        return result

    async def validate_connection(self, account: Any | None = None) -> bool:
        if not await super().validate_connection(account):
            return False
        if account is None:
            return True
        if not account.telegram_business_connection_id:
            return False
        conn_result = await self._post_method(
            "getBusinessConnection",
            {"business_connection_id": account.telegram_business_connection_id},
        )
        return conn_result.success

    def get_capabilities(self, account: Any | None = None) -> ChannelCapabilities:
        base = super().get_capabilities(account)
        rights = account.telegram_rights_json if account else {}
        merged = base.model_dump()
        merged.update(
            {
                "supports_business_chats": True,
                "chat_types": ["private", "group", "supergroup", "business"],
                "rights": rights,
            }
        )
        return ChannelCapabilities(**merged)

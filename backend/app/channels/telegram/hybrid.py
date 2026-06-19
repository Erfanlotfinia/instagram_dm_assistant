from __future__ import annotations

from typing import Any

from app.channels.telegram.bot import TelegramBotAdapter
from app.channels.telegram.business import TelegramBusinessAdapter
from app.schemas.channels import (
    ChannelCapabilities,
    NormalizedInboundMessage,
    NormalizedOutboundMessage,
    ProviderSendResult,
)


class TelegramHybridAdapter(TelegramBotAdapter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._bot = TelegramBotAdapter(*args, **kwargs)
        self._business = TelegramBusinessAdapter(*args, **kwargs)

    def receive_message(
        self, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> list[NormalizedInboundMessage]:
        business_msgs = self._business.receive_message(payload, headers)
        bot_msgs = self._bot.receive_message(payload, headers)
        if business_msgs:
            return business_msgs
        return bot_msgs

    def parse_inbound_update(
        self, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> list[NormalizedInboundMessage]:
        return self.receive_message(payload, headers)

    async def send_message(
        self, message: NormalizedOutboundMessage, account: Any | None = None
    ) -> ProviderSendResult:
        if account and account.telegram_business_enabled and account.telegram_business_connection_id:
            business_result = await self._business.send_message(message, account)
            if business_result.success:
                return business_result
            if not business_result.retryable:
                return business_result
        return await self._bot.send_message(message, account)

    async def mark_read(
        self,
        external_chat_id: str,
        external_message_id: str,
        business_connection_id: str | None = None,
    ) -> ProviderSendResult:
        if business_connection_id:
            return await self._business.mark_read(
                external_chat_id, external_message_id, business_connection_id
            )
        return await self._bot.mark_read(external_chat_id, external_message_id)

    async def sync_metadata(self, account: Any) -> dict[str, Any]:
        bot_meta = await self._bot.sync_metadata(account)
        if account and account.telegram_business_connection_id:
            business_meta = await self._business.sync_metadata(account)
            bot_meta.update(business_meta)
        return bot_meta

    async def validate_connection(self, account: Any | None = None) -> bool:
        if not await self._bot.validate_connection(account):
            return False
        if account and account.telegram_business_connection_id:
            return await self._business.validate_connection(account)
        return True

    def get_capabilities(self, account: Any | None = None) -> ChannelCapabilities:
        bot_caps = self._bot.get_capabilities(account)
        if account and account.telegram_business_enabled:
            biz_caps = self._business.get_capabilities(account)
            merged = bot_caps.model_dump()
            merged.update(
                {
                    "supports_business_chats": True,
                    "chat_types": list(
                        set(bot_caps.chat_types + biz_caps.chat_types)
                    ),
                    "rights": biz_caps.rights,
                }
            )
            return ChannelCapabilities(**merged)
        return bot_caps

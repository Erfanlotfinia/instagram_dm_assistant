from __future__ import annotations

from typing import Any

from app.domain.enums import ChannelProvider, TelegramConnectionMode
from app.domain.models import ChannelAccount
from app.schemas.channels import NormalizedOutboundMessage, ProviderSendResult
from app.services.telegram_business_connection_service import TelegramBusinessConnectionService


class TelegramOutboundRouter:
    @staticmethod
    async def send(
        account: ChannelAccount,
        message: NormalizedOutboundMessage,
        db: Any,
    ) -> ProviderSendResult:
        return await TelegramBusinessConnectionService(db).send_message(account, message)

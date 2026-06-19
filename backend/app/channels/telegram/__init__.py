from __future__ import annotations

from typing import Any

from app.channels.telegram.bot import DEFAULT_ALLOWED_UPDATES, TelegramBotAdapter
from app.channels.telegram.business import TelegramBusinessAdapter
from app.channels.telegram.hybrid import TelegramHybridAdapter
from app.domain.enums import TelegramConnectionMode

TelegramProviderAdapter = TelegramBotAdapter


def telegram_adapter_for_mode(
    mode: TelegramConnectionMode | None,
    bot_token: str | None = None,
    webhook_secret: str | None = None,
    local_base_url: str | None = None,
) -> Any:
    kwargs = {
        "bot_token": bot_token,
        "webhook_secret": webhook_secret,
        "local_base_url": local_base_url,
    }
    if mode == TelegramConnectionMode.BUSINESS:
        return TelegramBusinessAdapter(**kwargs)
    if mode == TelegramConnectionMode.HYBRID:
        return TelegramHybridAdapter(**kwargs)
    return TelegramBotAdapter(**kwargs)


DEFAULT_TELEGRAM_ALLOWED_UPDATES = DEFAULT_ALLOWED_UPDATES

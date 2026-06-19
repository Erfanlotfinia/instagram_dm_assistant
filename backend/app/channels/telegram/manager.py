from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


class TelegramManagerBotClient:
    """Client for Telegram Bot API methods available only to manager bots."""

    api_base = "https://api.telegram.org"

    def __init__(self, bot_token: str | None = None) -> None:
        settings = get_settings()
        self.token = bot_token or settings.telegram_manager_bot_token
        self.api_base = self.api_base.rstrip("/")

    def _method_url(self, method: str) -> str:
        return f"{self.api_base}/bot{self.token}/{method}"

    async def call_method(self, method: str, payload: dict[str, Any] | None = None) -> Any:
        if not self.token:
            raise RuntimeError("Telegram manager bot token is not configured")
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(self._method_url(method), json=payload or {})
            data = response.json()
        except httpx.RequestError as exc:
            raise RuntimeError(f"Telegram manager bot API network error: {exc}") from exc
        if not response.is_success or not isinstance(data, dict) or not data.get("ok"):
            description = data.get("description", response.text) if isinstance(data, dict) else response.text
            raise RuntimeError(f"Telegram manager bot API error: {description}")
        return data.get("result")

    async def get_managed_bot_token(self, user_id: int) -> str:
        result = await self.call_method("getManagedBotToken", {"user_id": user_id})
        if not isinstance(result, str) or not result:
            raise RuntimeError("getManagedBotToken returned an invalid token")
        return result

    async def replace_managed_bot_token(self, user_id: int) -> str:
        result = await self.call_method("replaceManagedBotToken", {"user_id": user_id})
        if not isinstance(result, str) or not result:
            raise RuntimeError("replaceManagedBotToken returned an invalid token")
        return result

    async def get_me(self) -> dict[str, Any]:
        result = await self.call_method("getMe")
        return result if isinstance(result, dict) else {}

    @staticmethod
    def is_configured() -> bool:
        settings = get_settings()
        return bool(
            settings.telegram_manager_bot_token
            and settings.telegram_manager_bot_username
            and settings.telegram_manager_bot_id
        )

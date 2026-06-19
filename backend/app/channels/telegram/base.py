from __future__ import annotations

import httpx
from fastapi import Request

from app.domain.enums import ChannelProvider


class TelegramAdapterBase:
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

    async def verify_webhook(self, request: Request) -> bool:
        if not self.webhook_secret:
            return False
        return (
            request.headers.get("X-Telegram-Bot-Api-Secret-Token") == self.webhook_secret
            or request.headers.get("X-Webhook-Secret") == self.webhook_secret
        )

    def _method_url(self, method: str) -> str:
        return f"{self.api_base}/bot{self.token}/{method}"

    async def _post_method(self, method: str, payload: dict) -> "ProviderSendResult":
        from app.schemas.channels import ProviderSendResult

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

    async def configure_webhook(
        self, webhook_url: str, secret: str | None = None, allowed_updates: list[str] | None = None
    ) -> dict:
        payload: dict = {"url": webhook_url}
        if secret:
            payload["secret_token"] = secret
        if allowed_updates:
            payload["allowed_updates"] = allowed_updates
        result = await self._post_method("setWebhook", payload)
        return result.raw_response or {"ok": result.success}

    async def delete_webhook(self) -> dict:
        result = await self._post_method("deleteWebhook", {})
        return result.raw_response or {"ok": result.success}

    async def get_webhook_info(self) -> dict:
        result = await self._post_method("getWebhookInfo", {})
        return result.raw_response or {"ok": result.success}

    async def _get_me(self) -> dict:
        result = await self._post_method("getMe", {})
        if result.success and isinstance(result.raw_response, dict):
            return result.raw_response.get("result", {})
        return {}

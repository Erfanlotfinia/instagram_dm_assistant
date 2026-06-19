from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import decrypt_secret, encrypt_secret
from app.domain.enums import ChannelAccountStatus, ChannelProvider
from app.domain.models import ChannelAccount, ChannelConnectionSession
from app.services.channel_account_service import adapter_for_provider
from app.services.legacy_channel_compat import sync_legacy_instagram_account_from_channel


@dataclass(frozen=True)
class InstagramCandidateAccount:
    page_id: str
    page_name: str
    instagram_business_account_id: str
    instagram_username: str | None = None
    instagram_profile_picture_url: str | None = None


@dataclass(frozen=True)
class MetaTokenResult:
    access_token: str
    token_type: str | None = None
    expires_in: int | None = None
    scopes: list[str] | None = None


class InstagramMetaConnectError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class InstagramMetaConnectService:
    ERROR_MESSAGES = {
        "no_business_account": "No Instagram Business account found. Connect Instagram to a Facebook Page in Meta Business settings.",
        "no_page_connected": "Please connect your Instagram account to a Facebook Page.",
        "missing_permissions": "Missing required permissions. Reconnect and grant all requested permissions.",
        "app_not_approved": "Meta app review may be required before Instagram messaging works in live mode.",
        "token_exchange_failed": "Could not complete Meta authorization. Try connecting again.",
        "webhook_setup_failed": "Instagram connected but webhook setup could not be confirmed.",
        "validation_failed": "Connected account could not be validated with Meta.",
    }

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()

    def build_authorization_url(self, session: ChannelConnectionSession) -> str:
        if not self.settings.meta_app_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Instagram OAuth is not configured (META_APP_ID missing)",
            )
        params = {
            "client_id": self.settings.meta_app_id,
            "redirect_uri": session.redirect_uri,
            "state": session.state,
            "scope": ",".join(session.requested_scopes_json or self.settings.meta_oauth_scopes),
            "response_type": "code",
        }
        return (
            f"https://www.facebook.com/{self.settings.meta_graph_api_version}/dialog/oauth?"
            f"{urlencode(params)}"
        )

    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> MetaTokenResult:
        data = await self._graph_get(
            "/oauth/access_token",
            {
                "client_id": self.settings.meta_app_id,
                "client_secret": self.settings.meta_app_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        token = data.get("access_token")
        if not token:
            raise InstagramMetaConnectError("token_exchange_failed", self.ERROR_MESSAGES["token_exchange_failed"])
        return MetaTokenResult(
            access_token=str(token),
            token_type=data.get("token_type"),
            expires_in=data.get("expires_in"),
        )

    async def exchange_for_long_lived_token(self, short_lived_token: str) -> MetaTokenResult:
        data = await self._graph_get(
            "/oauth/access_token",
            {
                "grant_type": "fb_exchange_token",
                "client_id": self.settings.meta_app_id,
                "client_secret": self.settings.meta_app_secret,
                "fb_exchange_token": short_lived_token,
            },
        )
        token = data.get("access_token")
        if not token:
            raise InstagramMetaConnectError("token_exchange_failed", self.ERROR_MESSAGES["token_exchange_failed"])
        return MetaTokenResult(
            access_token=str(token),
            token_type=data.get("token_type"),
            expires_in=data.get("expires_in"),
        )

    async def fetch_user_pages(self, user_token: str) -> list[dict[str, Any]]:
        data = await self._graph_get(
            "/me/accounts",
            {
                "access_token": user_token,
                "fields": "id,name,access_token,instagram_business_account{id,username,profile_picture_url}",
            },
        )
        return [entry for entry in data.get("data", []) if isinstance(entry, dict)]

    async def fetch_instagram_profile(self, ig_id: str, access_token: str) -> dict[str, Any]:
        return await self._graph_get(
            f"/{ig_id}",
            {
                "access_token": access_token,
                "fields": "id,username,profile_picture_url",
            },
        )

    def extract_candidate_accounts(self, pages: list[dict[str, Any]]) -> list[InstagramCandidateAccount]:
        candidates: list[InstagramCandidateAccount] = []
        for page in pages:
            ig_account = page.get("instagram_business_account") or {}
            if not isinstance(ig_account, dict) or not ig_account.get("id"):
                continue
            candidates.append(
                InstagramCandidateAccount(
                    page_id=str(page["id"]),
                    page_name=str(page.get("name") or "Facebook Page"),
                    instagram_business_account_id=str(ig_account["id"]),
                    instagram_username=ig_account.get("username"),
                    instagram_profile_picture_url=ig_account.get("profile_picture_url"),
                )
            )
        return candidates

    def redact_candidate_accounts(
        self, candidates: list[InstagramCandidateAccount]
    ) -> list[dict[str, Any]]:
        return [
            {
                "page_id": candidate.page_id,
                "page_name": candidate.page_name,
                "instagram_business_account_id": candidate.instagram_business_account_id,
                "instagram_username": candidate.instagram_username,
                "instagram_profile_picture_url": candidate.instagram_profile_picture_url,
            }
            for candidate in candidates
        ]

    async def validate_required_permissions(
        self, access_token: str, required_scopes: list[str] | None = None
    ) -> list[str]:
        required = set(required_scopes or self.settings.meta_oauth_scopes)
        data = await self._graph_get(
            "/debug_token",
            {
                "input_token": access_token,
                "access_token": f"{self.settings.meta_app_id}|{self.settings.meta_app_secret}",
            },
        )
        token_data = data.get("data") or {}
        granted = set(token_data.get("scopes") or [])
        missing = sorted(required - granted)
        if token_data.get("is_valid") is False:
            raise InstagramMetaConnectError(
                "missing_permissions",
                self.ERROR_MESSAGES["missing_permissions"],
            )
        return missing

    def instagram_webhook_url(self, channel_account_id: UUID) -> str:
        return (
            f"{self.settings.public_api_base_url.rstrip('/')}"
            f"/api/v1/channels/instagram/{channel_account_id}/webhook"
        )

    def generate_webhook_credentials(self, account: ChannelAccount) -> None:
        account.webhook_verify_token = secrets.token_urlsafe(32)
        if self.settings.meta_app_secret:
            account.webhook_secret_encrypted = encrypt_secret(self.settings.meta_app_secret)
        account.webhook_url = self.instagram_webhook_url(account.id)

    async def configure_webhook_if_supported(self) -> dict[str, Any]:
        if not self.settings.meta_app_id or not self.settings.meta_app_secret:
            return {"configured": False, "reason": "missing_app_credentials"}
        app_token = f"{self.settings.meta_app_id}|{self.settings.meta_app_secret}"
        callback_url = (
            f"{self.settings.public_api_base_url.rstrip('/')}/api/v1/channels/instagram/webhook"
        )
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.settings.meta_graph_api_base_url.rstrip('/')}/"
                    f"{self.settings.meta_graph_api_version}/{self.settings.meta_app_id}/subscriptions",
                    params={
                        "access_token": app_token,
                        "object": "instagram",
                        "callback_url": callback_url,
                        "verify_token": "modira-webhook",
                        "fields": "messages,messaging_postbacks",
                    },
                )
            payload = response.json() if response.content else {}
            return {
                "configured": response.is_success and payload.get("success", False),
                "status_code": response.status_code,
                "response": self.redact_meta_payload(payload),
            }
        except httpx.RequestError as exc:
            return {"configured": False, "reason": "network_error", "error": str(exc)}

    async def validate_connection(self, account: ChannelAccount) -> bool:
        token = decrypt_secret(account.access_token_encrypted) if account.access_token_encrypted else None
        if not token or not account.external_account_id:
            return False
        try:
            await self.fetch_instagram_profile(account.external_account_id, token)
            return True
        except InstagramMetaConnectError:
            return False

    async def create_or_update_channel_account(
        self,
        *,
        shop_id: UUID,
        candidate: InstagramCandidateAccount,
        page_access_token: str,
        user_token_scopes: list[str] | None,
        token_expires_at: datetime | None,
        existing_account_id: UUID | None = None,
    ) -> ChannelAccount:
        display_name = (
            f"@{candidate.instagram_username}"
            if candidate.instagram_username
            else candidate.page_name
        )
        account: ChannelAccount | None = None
        if existing_account_id:
            account = self.db.scalar(
                select(ChannelAccount).where(
                    ChannelAccount.id == existing_account_id,
                    ChannelAccount.shop_id == shop_id,
                    ChannelAccount.provider == ChannelProvider.INSTAGRAM,
                )
            )
        if account is None:
            account = self.db.scalar(
                select(ChannelAccount).where(
                    ChannelAccount.shop_id == shop_id,
                    ChannelAccount.provider == ChannelProvider.INSTAGRAM,
                    ChannelAccount.external_account_id == candidate.instagram_business_account_id,
                )
            )
        capabilities = (
            adapter_for_provider(ChannelProvider.INSTAGRAM).get_capabilities().model_dump(mode="json")
        )
        if account is None:
            account = ChannelAccount(
                shop_id=shop_id,
                provider=ChannelProvider.INSTAGRAM,
                display_name=display_name,
                external_account_id=candidate.instagram_business_account_id,
                bot_username=candidate.instagram_username,
                capabilities_json=capabilities,
                settings_json={
                    "page_id": candidate.page_id,
                    "page_name": candidate.page_name,
                    "instagram_username": candidate.instagram_username,
                    "instagram_profile_picture_url": candidate.instagram_profile_picture_url,
                },
            )
            self.db.add(account)
            self.db.flush()
        else:
            account.display_name = display_name
            account.external_account_id = candidate.instagram_business_account_id
            account.bot_username = candidate.instagram_username
            settings = dict(account.settings_json or {})
            settings.update(
                {
                    "page_id": candidate.page_id,
                    "page_name": candidate.page_name,
                    "instagram_username": candidate.instagram_username,
                    "instagram_profile_picture_url": candidate.instagram_profile_picture_url,
                }
            )
            account.settings_json = settings
            account.status = ChannelAccountStatus.CONNECTED

        account.access_token_encrypted = encrypt_secret(page_access_token)
        account.token_expires_at = token_expires_at
        account.scopes_json = user_token_scopes
        self.generate_webhook_credentials(account)
        account.webhook_url = self.instagram_webhook_url(account.id)

        webhook_result = await self.configure_webhook_if_supported()
        valid = await self.validate_connection(account)
        account.last_validation_at = datetime.now(UTC)
        if valid and webhook_result.get("configured"):
            account.status = ChannelAccountStatus.WEBHOOK_CONFIGURED
            account.last_error = None
        elif valid:
            account.status = ChannelAccountStatus.CONNECTED
            if not webhook_result.get("configured"):
                account.last_error = self.ERROR_MESSAGES["webhook_setup_failed"]
        else:
            account.status = ChannelAccountStatus.ERROR
            account.last_error = self.ERROR_MESSAGES["validation_failed"]

        self.db.commit()
        self.db.refresh(account)
        sync_legacy_instagram_account_from_channel(self.db, account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def resolve_page_access_token(
        self, pages: list[dict[str, Any]], candidate: InstagramCandidateAccount
    ) -> str | None:
        for page in pages:
            if str(page.get("id")) != candidate.page_id:
                continue
            token = page.get("access_token")
            return str(token) if token else None
        return None

    def token_expires_at_from_result(self, token_result: MetaTokenResult) -> datetime | None:
        if not token_result.expires_in:
            return None
        return datetime.now(UTC) + timedelta(seconds=int(token_result.expires_in))

    async def revoke_token_if_supported(self, access_token: str | None) -> None:
        if not access_token:
            return
        try:
            await self._graph_delete("/me/permissions", {"access_token": access_token})
        except InstagramMetaConnectError:
            return

    @staticmethod
    def redact_meta_payload(payload: dict[str, Any]) -> dict[str, Any]:
        redacted = dict(payload)
        for key in ("access_token", "token", "page_access_token"):
            if key in redacted:
                redacted[key] = "[REDACTED]"
        if "data" in redacted and isinstance(redacted["data"], list):
            redacted["data"] = [
                InstagramMetaConnectService.redact_meta_payload(item)
                if isinstance(item, dict)
                else item
                for item in redacted["data"]
            ]
        return redacted

    def normalize_meta_errors(self, response: httpx.Response) -> InstagramMetaConnectError:
        try:
            payload = response.json()
        except Exception:
            payload = {}
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        code = str(error.get("code") or response.status_code)
        message = str(error.get("message") or "Meta API request failed")
        if code in {"10", "200"} or "permission" in message.lower():
            return InstagramMetaConnectError("missing_permissions", self.ERROR_MESSAGES["missing_permissions"])
        if "app" in message.lower() and "review" in message.lower():
            return InstagramMetaConnectError("app_not_approved", self.ERROR_MESSAGES["app_not_approved"])
        if response.status_code in {400, 401, 403}:
            return InstagramMetaConnectError("token_exchange_failed", self.ERROR_MESSAGES["token_exchange_failed"])
        return InstagramMetaConnectError("validation_failed", message)

    async def _graph_get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.settings.meta_graph_api_base_url.rstrip('/')}/{self.settings.meta_graph_api_version}{path}"
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params)
        if response.is_success:
            data = response.json()
            return data if isinstance(data, dict) else {}
        raise self.normalize_meta_errors(response)

    async def _graph_delete(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.settings.meta_graph_api_base_url.rstrip('/')}/{self.settings.meta_graph_api_version}{path}"
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.delete(url, params=params)
        if response.is_success:
            data = response.json()
            return data if isinstance(data, dict) else {}
        raise self.normalize_meta_errors(response)

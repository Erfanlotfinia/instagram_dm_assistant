from __future__ import annotations

import logging
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.channels.telegram.manager import TelegramManagerBotClient
from app.core.config import get_settings
from app.core.security import encrypt_secret
from app.domain.enums import (
    ChannelAccountStatus,
    ChannelProvider,
    TelegramConnectionMode,
    TelegramConnectionSessionStatus,
)
from app.domain.models import ChannelAccount, TelegramConnectionSession
from app.repositories.telegram_connection_session_repository import (
    TelegramConnectionSessionRepository,
)
from app.services.audit_service import AuditService
from app.services.channel_account_service import ChannelAccountService
from app.services.telegram_connect_service import TelegramConnectService

logger = logging.getLogger(__name__)

SESSION_TTL_MINUTES = 30


def _sanitize_username_part(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_]", "", value.lower().replace("-", "_").replace(" ", "_"))
    return cleaned.strip("_")


def suggest_bot_username(shop_id: UUID, display_name: str) -> str:
    base = _sanitize_username_part(display_name) or "modira"
    suffix = secrets.token_hex(3)
    shop_part = str(shop_id).replace("-", "")[:6]
    username = f"{base}_{shop_part}_{suffix}_bot"
    if len(username) > 32:
        username = f"{base[:8]}_{suffix}_bot"
    if len(username) < 5:
        username = f"modira_{suffix}_bot"
    return username[:32]


def build_newbot_deep_link(suggested_username: str, display_name: str) -> str:
    settings = get_settings()
    manager_username = settings.telegram_manager_bot_username.lstrip("@")
    encoded_name = quote(display_name or "Modira Bot")
    return f"https://t.me/newbot/{manager_username}/{suggested_username}?name={encoded_name}"


class TelegramManagedBotService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = TelegramConnectionSessionRepository(db)
        self.account_service = ChannelAccountService(db)
        self.connect_service = TelegramConnectService(db)

    def _assert_manager_configured(self) -> None:
        if not TelegramManagerBotClient.is_configured():
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Telegram managed bot provisioning is not configured",
            )

    async def start_managed_session(
        self,
        shop_id: UUID,
        created_by: UUID,
        display_name: str | None = None,
        channel_account_id: UUID | None = None,
    ) -> TelegramConnectionSession:
        self._assert_manager_configured()
        self.repo.expire_stale()
        if channel_account_id:
            account = self.account_service.get(shop_id, channel_account_id)
            if account is None or account.provider != ChannelProvider.TELEGRAM:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Telegram account not found")

        label = display_name or "Telegram"
        suggested_username = suggest_bot_username(shop_id, label)
        deep_link = build_newbot_deep_link(suggested_username, label)
        settings = get_settings()

        session = TelegramConnectionSession(
            shop_id=shop_id,
            channel_account_id=channel_account_id,
            mode=TelegramConnectionMode.BOT,
            status=TelegramConnectionSessionStatus.WAITING_MANAGED_BOT_APPROVAL,
            state=self.repo.new_state(),
            expires_at=datetime.now(UTC) + timedelta(minutes=SESSION_TTL_MINUTES),
            created_by=created_by,
            metadata_json={
                "display_name": label,
                "managed_bot": True,
                "suggested_bot_username": suggested_username,
                "deep_link": deep_link,
                "reconnect": bool(channel_account_id),
            },
        )
        session = self.repo.create(session)
        account = await self.connect_service._ensure_account(session, created_by)
        account.connection_mode = TelegramConnectionMode.BOT
        account.managed_bot = True
        account.manager_bot_id = settings.telegram_manager_bot_id
        self.db.commit()
        self.db.refresh(session)
        return session

    def _find_waiting_session(self, bot_username: str) -> TelegramConnectionSession | None:
        sessions = list(
            self.db.scalars(
                select(TelegramConnectionSession).where(
                    TelegramConnectionSession.status
                    == TelegramConnectionSessionStatus.WAITING_MANAGED_BOT_APPROVAL,
                    TelegramConnectionSession.expires_at >= datetime.now(UTC),
                )
            ).all()
        )
        normalized = bot_username.lower().lstrip("@")
        for session in sessions:
            suggested = (session.metadata_json or {}).get("suggested_bot_username", "")
            if suggested.lower() == normalized:
                return session
        return None

    async def handle_managed_bot_update(self, payload: dict[str, Any]) -> bool:
        bot = payload.get("bot") or {}
        bot_id = bot.get("id")
        bot_username = bot.get("username")
        if not bot_id or not bot_username:
            logger.warning("Managed bot update missing bot id or username")
            return False

        managed_bot_id = str(bot_id)
        session = self._find_waiting_session(bot_username)
        if session is None:
            existing = self.db.scalar(
                select(ChannelAccount).where(
                    ChannelAccount.managed_bot_id == managed_bot_id,
                    ChannelAccount.managed_bot.is_(True),
                )
            )
            if existing is not None:
                return True
            logger.info(
                "No waiting managed bot session for username=%s bot_id=%s",
                bot_username,
                managed_bot_id,
            )
            return False

        if session.channel_account_id:
            account = self.account_service.get(session.shop_id, session.channel_account_id)
            if (
                account
                and account.managed_bot
                and account.managed_bot_id == managed_bot_id
                and account.bot_token_encrypted
            ):
                session.status = TelegramConnectionSessionStatus.CONNECTED
                session.completed_at = datetime.now(UTC)
                self.repo.save(session)
                return True

        try:
            manager_client = TelegramManagerBotClient()
            token = await manager_client.get_managed_bot_token(int(bot_id))
        except RuntimeError as exc:
            logger.exception("Failed to fetch managed bot token for bot_id=%s", bot_id)
            session.status = TelegramConnectionSessionStatus.FAILED
            session.error_message = str(exc)
            self.repo.save(session)
            return False

        account = await self.connect_service._ensure_account(session, session.created_by)
        settings = get_settings()
        account.managed_bot = True
        account.manager_bot_id = settings.telegram_manager_bot_id
        account.managed_bot_id = managed_bot_id
        account.bot_token_encrypted = encrypt_secret(token)
        if not account.webhook_secret_encrypted:
            account.webhook_secret_encrypted = encrypt_secret(secrets.token_urlsafe(32))
        account.connection_mode = TelegramConnectionMode.BOT

        from app.channels.telegram import telegram_adapter_for_mode
        from app.core.security import decrypt_secret

        webhook_secret = decrypt_secret(account.webhook_secret_encrypted)
        bot_adapter = telegram_adapter_for_mode(
            TelegramConnectionMode.BOT,
            bot_token=token,
            webhook_secret=webhook_secret,
            local_base_url=(account.settings_json or {}).get("local_bot_api_base_url"),
        )
        valid = await bot_adapter.validate_connection(account)
        if not valid:
            session.status = TelegramConnectionSessionStatus.FAILED
            session.error_message = "Managed bot validation failed"
            self.repo.save(session)
            return False

        await bot_adapter.sync_metadata(account)
        await self.connect_service._register_webhook(account)
        adapter = bot_adapter
        caps = adapter.get_capabilities(account)
        account.capabilities_json = caps.model_dump(mode="json")
        account.telegram_capabilities_json = caps.model_dump(mode="json")
        account.status = ChannelAccountStatus.WEBHOOK_CONFIGURED
        account.last_validation_at = datetime.now(UTC)
        account.last_error = None

        session.channel_account_id = account.id
        session.status = TelegramConnectionSessionStatus.CONNECTED
        session.completed_at = datetime.now(UTC)
        session.metadata_json = {
            **session.metadata_json,
            "bot_username": account.bot_username,
            "bot_id": account.bot_id,
            "managed_bot_id": managed_bot_id,
        }
        self.db.commit()

        AuditService(self.db).log(
            action="telegram_managed_bot_connected",
            entity_type="channel_account",
            shop_id=session.shop_id,
            actor_user_id=session.created_by,
            entity_id=str(account.id),
            metadata={"managed_bot_id": managed_bot_id, "bot_username": account.bot_username},
        )
        return True

    def _get_managed_account(self, shop_id: UUID, channel_account_id: UUID) -> ChannelAccount:
        account = self.account_service.get(shop_id, channel_account_id)
        if account is None or account.provider != ChannelProvider.TELEGRAM:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Telegram account not found")
        if not account.managed_bot or not account.managed_bot_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Channel account is not a managed Telegram bot",
            )
        return account

    async def _apply_managed_token(
        self, account: ChannelAccount, token: str
    ) -> ChannelAccount:
        from app.channels.telegram import telegram_adapter_for_mode
        from app.core.security import decrypt_secret

        account.bot_token_encrypted = encrypt_secret(token)
        if not account.webhook_secret_encrypted:
            account.webhook_secret_encrypted = encrypt_secret(secrets.token_urlsafe(32))
        webhook_secret = decrypt_secret(account.webhook_secret_encrypted)
        bot_adapter = telegram_adapter_for_mode(
            TelegramConnectionMode.BOT,
            bot_token=token,
            webhook_secret=webhook_secret,
            local_base_url=(account.settings_json or {}).get("local_bot_api_base_url"),
        )
        valid = await bot_adapter.validate_connection(account)
        if not valid:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Managed bot token validation failed",
            )
        await bot_adapter.sync_metadata(account)
        await self.connect_service._register_webhook(account)
        caps = bot_adapter.get_capabilities(account)
        account.capabilities_json = caps.model_dump(mode="json")
        account.telegram_capabilities_json = caps.model_dump(mode="json")
        account.status = ChannelAccountStatus.WEBHOOK_CONFIGURED
        account.last_validation_at = datetime.now(UTC)
        account.last_error = None
        self.db.commit()
        self.db.refresh(account)
        return account

    async def rotate_token(
        self, shop_id: UUID, channel_account_id: UUID, actor_user_id: UUID
    ) -> ChannelAccount:
        self._assert_manager_configured()
        account = self._get_managed_account(shop_id, channel_account_id)
        manager_client = TelegramManagerBotClient()
        try:
            new_token = await manager_client.replace_managed_bot_token(int(account.managed_bot_id))
        except RuntimeError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        account = await self._apply_managed_token(account, new_token)
        AuditService(self.db).log(
            action="telegram_managed_bot_token_rotated",
            entity_type="channel_account",
            shop_id=shop_id,
            actor_user_id=actor_user_id,
            entity_id=str(account.id),
            metadata={"managed_bot_id": account.managed_bot_id},
        )
        return account

    async def reconnect_managed_bot(
        self, shop_id: UUID, channel_account_id: UUID, actor_user_id: UUID
    ) -> ChannelAccount:
        self._assert_manager_configured()
        account = self._get_managed_account(shop_id, channel_account_id)
        manager_client = TelegramManagerBotClient()
        try:
            token = await manager_client.get_managed_bot_token(int(account.managed_bot_id))
        except RuntimeError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        account = await self._apply_managed_token(account, token)
        AuditService(self.db).log(
            action="telegram_managed_bot_reconnected",
            entity_type="channel_account",
            shop_id=shop_id,
            actor_user_id=actor_user_id,
            entity_id=str(account.id),
            metadata={"managed_bot_id": account.managed_bot_id},
        )
        return account

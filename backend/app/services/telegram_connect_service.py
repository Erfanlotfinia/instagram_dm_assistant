from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

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
from app.services.channel_account_service import ChannelAccountService, adapter_for_provider

logger = logging.getLogger(__name__)

SESSION_TTL_MINUTES = 30


class TelegramConnectService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = TelegramConnectionSessionRepository(db)
        self.account_service = ChannelAccountService(db)

    def start_session(
        self,
        shop_id: UUID,
        created_by: UUID,
        mode: TelegramConnectionMode,
        display_name: str | None = None,
        channel_account_id: UUID | None = None,
    ) -> TelegramConnectionSession:
        self.repo.expire_stale()
        if channel_account_id:
            account = self.account_service.get(shop_id, channel_account_id)
            if account is None or account.provider != ChannelProvider.TELEGRAM:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Telegram account not found")
        session = TelegramConnectionSession(
            shop_id=shop_id,
            channel_account_id=channel_account_id,
            mode=mode,
            status=TelegramConnectionSessionStatus.WAITING_BOT_TOKEN,
            state=self.repo.new_state(),
            expires_at=datetime.now(UTC) + timedelta(minutes=SESSION_TTL_MINUTES),
            created_by=created_by,
            metadata_json={
                "display_name": display_name or "Telegram",
                "reconnect": bool(channel_account_id),
            },
        )
        return self.repo.create(session)

    def get_session(self, shop_id: UUID, session_id: UUID) -> TelegramConnectionSession:
        session = self.repo.get_for_shop(shop_id, session_id)
        if session is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Connect session not found")
        return session

    def get_actionable_session(self, shop_id: UUID, session_id: UUID) -> TelegramConnectionSession:
        session = self.get_session(shop_id, session_id)
        self._assert_actionable(session)
        return session

    def _assert_actionable(self, session: TelegramConnectionSession) -> None:
        if session.status in {
            TelegramConnectionSessionStatus.CONNECTED,
            TelegramConnectionSessionStatus.FAILED,
            TelegramConnectionSessionStatus.EXPIRED,
        }:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Connect session is not active")
        if session.expires_at < datetime.now(UTC):
            session.status = TelegramConnectionSessionStatus.EXPIRED
            self.repo.save(session)
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Connect session expired")

    async def submit_bot_token(
        self,
        shop_id: UUID,
        session_id: UUID,
        bot_token: str,
        webhook_secret: str | None,
        actor_user_id: UUID,
    ) -> TelegramConnectionSession:
        session = self.get_actionable_session(shop_id, session_id)
        account = await self._ensure_account(session, actor_user_id)
        account.bot_token_encrypted = encrypt_secret(bot_token)
        if webhook_secret:
            account.webhook_secret_encrypted = encrypt_secret(webhook_secret)
        account.connection_mode = session.mode

        from app.channels.telegram import telegram_adapter_for_mode

        bot_adapter = telegram_adapter_for_mode(
            TelegramConnectionMode.BOT,
            bot_token=bot_token,
            webhook_secret=webhook_secret,
            local_base_url=(account.settings_json or {}).get("local_bot_api_base_url"),
        )
        valid = await bot_adapter.validate_connection(account)
        if not valid:
            session.status = TelegramConnectionSessionStatus.FAILED
            session.error_message = "Bot token validation failed"
            self.repo.save(session)
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid bot token")
        await bot_adapter.sync_metadata(account)

        session.channel_account_id = account.id
        session.metadata_json = {
            **session.metadata_json,
            "bot_username": account.bot_username,
            "bot_id": account.bot_id,
        }
        if session.mode == TelegramConnectionMode.BOT:
            session.status = TelegramConnectionSessionStatus.CONNECTED
            account.status = ChannelAccountStatus.CONNECTED
        else:
            session.status = TelegramConnectionSessionStatus.WAITING_BUSINESS_CONNECTION
            account.status = ChannelAccountStatus.CONNECTED
            await self._register_webhook(account)
        self.db.commit()
        self.db.refresh(session)
        return session

    async def complete_session(
        self, shop_id: UUID, session_id: UUID, actor_user_id: UUID
    ) -> ChannelAccount:
        session = self.get_session(shop_id, session_id)
        if session.status == TelegramConnectionSessionStatus.CONNECTED:
            account = self.account_service.get(shop_id, session.channel_account_id)
            if account is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Channel account not found")
            return account

        self._assert_actionable(session)
        if session.status == TelegramConnectionSessionStatus.WAITING_BUSINESS_CONNECTION:
            account = self.account_service.get(shop_id, session.channel_account_id)
            if account is None or not account.telegram_business_enabled:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail="Business connection not established yet",
                )
        account = await self.finalize_account_if_needed(session)
        session.status = TelegramConnectionSessionStatus.CONNECTED
        session.completed_at = datetime.now(UTC)
        self.repo.save(session)
        AuditService(self.db).log(
            action="telegram_connected",
            entity_type="channel_account",
            shop_id=shop_id,
            actor_user_id=actor_user_id,
            entity_id=str(account.id),
            metadata={"mode": session.mode.value},
        )
        return account

    async def cancel_session(
        self, shop_id: UUID, session_id: UUID, actor_user_id: UUID
    ) -> TelegramConnectionSession:
        session = self.repo.get_for_shop(shop_id, session_id)
        if session is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Connect session not found")
        session.status = TelegramConnectionSessionStatus.FAILED
        session.error_message = "Cancelled by user"
        self.repo.save(session)
        AuditService(self.db).log(
            action="telegram_connect_cancelled",
            entity_type="telegram_connection_session",
            shop_id=shop_id,
            actor_user_id=actor_user_id,
            entity_id=str(session.id),
        )
        return session

    async def _ensure_account(
        self, session: TelegramConnectionSession, actor_user_id: UUID
    ) -> ChannelAccount:
        if session.channel_account_id:
            account = self.account_service.get(session.shop_id, session.channel_account_id)
            if account is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Channel account not found")
            return account
        from app.schemas.channels import ChannelAccountCreate

        display_name = session.metadata_json.get("display_name") or "Telegram"
        account = self.account_service.create(
            session.shop_id,
            ChannelAccountCreate(
                provider=ChannelProvider.TELEGRAM,
                display_name=display_name,
                connection_mode=session.mode,
            ),
        )
        session.channel_account_id = account.id
        self.db.commit()
        return account

    async def _register_webhook(self, account: ChannelAccount) -> None:
        settings = get_settings()
        webhook_url = (
            f"{settings.public_api_base_url.rstrip('/')}"
            f"/api/v1/channels/telegram/{account.id}/webhook"
        )
        adapter = adapter_for_provider(ChannelProvider.TELEGRAM, account)
        from app.core.security import decrypt_secret
        from app.channels.telegram.bot import DEFAULT_ALLOWED_UPDATES

        secret = (
            decrypt_secret(account.webhook_secret_encrypted) if account.webhook_secret_encrypted else None
        )
        await adapter.configure_webhook(webhook_url, secret)
        if hasattr(adapter, "_post_method"):
            await adapter._post_method(
                "setWebhook",
                {
                    "url": webhook_url,
                    **({"secret_token": secret} if secret else {}),
                    "allowed_updates": DEFAULT_ALLOWED_UPDATES,
                },
            )
        account.webhook_url = webhook_url
        if account.status not in {
            ChannelAccountStatus.WEBHOOK_CONFIGURED,
            ChannelAccountStatus.DISABLED,
        }:
            account.status = ChannelAccountStatus.WEBHOOK_CONFIGURED

    async def finalize_account_if_needed(
        self, session: TelegramConnectionSession
    ) -> ChannelAccount:
        account = self.account_service.get(session.shop_id, session.channel_account_id)
        if account is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Channel account not found")
        if account.status == ChannelAccountStatus.WEBHOOK_CONFIGURED and account.webhook_url:
            adapter = adapter_for_provider(ChannelProvider.TELEGRAM, account)
            await adapter.sync_metadata(account)
            self.db.commit()
            self.db.refresh(account)
            return account

        await self._register_webhook(account)
        adapter = adapter_for_provider(ChannelProvider.TELEGRAM, account)
        if account.telegram_business_enabled or session.mode == TelegramConnectionMode.BOT:
            account.status = ChannelAccountStatus.WEBHOOK_CONFIGURED
        caps = adapter.get_capabilities(account)
        account.capabilities_json = caps.model_dump(mode="json")
        account.telegram_capabilities_json = caps.model_dump(mode="json")
        await adapter.sync_metadata(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def handle_business_connection_update(
        self, account: ChannelAccount, connection: dict[str, Any]
    ) -> None:
        from app.services.telegram_business_connection_service import (
            TelegramBusinessConnectionService,
        )

        TelegramBusinessConnectionService(self.db).connect(account, connection)

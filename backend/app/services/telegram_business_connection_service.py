from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.enums import (
    ChannelAccountStatus,
    ChannelProvider,
    TelegramConnectionMode,
    TelegramConnectionSessionStatus,
)
from app.domain.models import ChannelAccount
from app.repositories.telegram_connection_session_repository import (
    TelegramConnectionSessionRepository,
)
from app.schemas.channels import NormalizedOutboundMessage, ProviderSendResult
from app.services.audit_service import AuditService
from app.services.channel_account_service import adapter_for_provider

logger = logging.getLogger(__name__)


class TelegramBusinessConnectionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.session_repo = TelegramConnectionSessionRepository(db)

    def connect(self, account: ChannelAccount, connection: dict[str, Any]) -> None:
        previous_enabled = account.telegram_business_enabled
        was_disabled = account.status == ChannelAccountStatus.DISABLED
        connection_id = connection.get("id")
        if connection_id is not None:
            account.telegram_business_connection_id = str(connection_id)
        account.telegram_business_enabled = bool(connection.get("is_enabled"))
        account.telegram_rights_json = connection.get("rights") or {}
        user = connection.get("user") or {}
        if user.get("id"):
            account.telegram_user_id = str(user.get("id"))
        if user.get("username"):
            account.telegram_username = user.get("username")
        user_chat_id = connection.get("user_chat_id")
        if user_chat_id is not None:
            account.telegram_chat_id = str(user_chat_id)

        adapter = adapter_for_provider(ChannelProvider.TELEGRAM, account)
        caps = adapter.get_capabilities(account)
        account.telegram_capabilities_json = caps.model_dump(mode="json")
        account.telegram_last_sync_at = datetime.now(UTC)

        if account.telegram_business_enabled:
            if account.status in {ChannelAccountStatus.DISABLED, ChannelAccountStatus.CONNECTED}:
                account.status = ChannelAccountStatus.WEBHOOK_CONFIGURED
                account.last_error = None
            if was_disabled and not previous_enabled:
                AuditService(self.db).log(
                    action="telegram_business_reconnected",
                    entity_type="channel_account",
                    shop_id=account.shop_id,
                    actor_user_id=None,
                    entity_id=str(account.id),
                    metadata={
                        "business_connection_id": account.telegram_business_connection_id,
                    },
                )
            session = self.session_repo.get_waiting_business_for_account(account.id)
            if session and connection.get("is_enabled"):
                session.status = TelegramConnectionSessionStatus.CONNECTED
                session.completed_at = datetime.now(UTC)
                session.metadata_json = {
                    **session.metadata_json,
                    "business_connection_id": account.telegram_business_connection_id,
                }
            AuditService(self.db).log(
                action="telegram_business_connected",
                entity_type="channel_account",
                shop_id=account.shop_id,
                actor_user_id=None,
                entity_id=str(account.id),
                metadata={
                    "business_connection_id": account.telegram_business_connection_id,
                    "enabled": True,
                },
            )
        else:
            account.status = ChannelAccountStatus.DISABLED
            account.last_error = "Telegram Business connection disabled"
            AuditService(self.db).log(
                action="telegram_business_disabled",
                entity_type="channel_account",
                shop_id=account.shop_id,
                actor_user_id=None,
                entity_id=str(account.id),
                metadata={
                    "business_connection_id": account.telegram_business_connection_id,
                },
            )

        self.db.commit()

    async def disconnect(
        self,
        account: ChannelAccount,
        actor_user_id: UUID,
        *,
        clear_credentials: bool = False,
    ) -> ChannelAccount:
        account.telegram_business_enabled = False
        if clear_credentials:
            account.telegram_business_connection_id = None
            account.telegram_user_id = None
            account.telegram_username = None
            account.telegram_chat_id = None
            account.telegram_rights_json = {}
            account.telegram_capabilities_json = {}
            account.telegram_last_sync_at = None
        AuditService(self.db).log(
            action="telegram_business_disconnected",
            entity_type="channel_account",
            shop_id=account.shop_id,
            actor_user_id=actor_user_id,
            entity_id=str(account.id),
            metadata={"clear_credentials": clear_credentials},
        )
        self.db.commit()
        self.db.refresh(account)
        return account

    async def sync(self, account: ChannelAccount) -> dict[str, Any]:
        adapter = adapter_for_provider(ChannelProvider.TELEGRAM, account)
        result = await adapter.sync_metadata(account)
        self.db.commit()
        self.db.refresh(account)
        return result

    async def validate(self, account: ChannelAccount) -> bool:
        mode = account.connection_mode or TelegramConnectionMode.BOT
        from app.channels.telegram import telegram_adapter_for_mode
        from app.core.security import decrypt_secret

        bot_token = decrypt_secret(account.bot_token_encrypted) if account.bot_token_encrypted else None
        webhook_secret = (
            decrypt_secret(account.webhook_secret_encrypted) if account.webhook_secret_encrypted else None
        )
        local_base_url = (account.settings_json or {}).get("local_bot_api_base_url")
        bot_adapter = telegram_adapter_for_mode(
            TelegramConnectionMode.BOT,
            bot_token=bot_token,
            webhook_secret=webhook_secret,
            local_base_url=local_base_url,
        )
        if not await bot_adapter.validate_connection(account):
            return False
        if mode in {TelegramConnectionMode.BUSINESS, TelegramConnectionMode.HYBRID}:
            if not account.telegram_business_connection_id:
                return False
            if not account.telegram_business_enabled:
                return False
            adapter = adapter_for_provider(ChannelProvider.TELEGRAM, account)
            return await adapter.validate_connection(account)
        return True

    async def send_message(
        self,
        account: ChannelAccount,
        message: NormalizedOutboundMessage,
    ) -> ProviderSendResult:
        if message.metadata.get("business_connection_id") is None and account.telegram_business_connection_id:
            message.metadata["business_connection_id"] = account.telegram_business_connection_id
        adapter = adapter_for_provider(ChannelProvider.TELEGRAM, account)
        mode = account.connection_mode or TelegramConnectionMode.BOT
        if mode == TelegramConnectionMode.BOT:
            return await adapter.send_message(message, account)
        if mode == TelegramConnectionMode.BUSINESS:
            return await adapter.send_message(message, account)
        from app.channels.telegram.hybrid import TelegramHybridAdapter

        if isinstance(adapter, TelegramHybridAdapter):
            return await adapter.send_message(message, account)
        return await adapter.send_message(message, account)

    async def mark_read(
        self,
        account: ChannelAccount,
        external_chat_id: str,
        external_message_id: str,
        *,
        connection_id: str | None = None,
    ) -> ProviderSendResult:
        mode = account.connection_mode or TelegramConnectionMode.BOT
        if mode == TelegramConnectionMode.BOT:
            return ProviderSendResult(
                provider=ChannelProvider.TELEGRAM,
                success=True,
                raw_response={"skipped": "bot_mode_no_read_api"},
            )
        rights = account.telegram_rights_json or {}
        if not rights.get("can_read_messages", True):
            return ProviderSendResult(
                provider=ChannelProvider.TELEGRAM,
                success=True,
                raw_response={"skipped": "no_read_permission"},
            )
        business_connection_id = connection_id or account.telegram_business_connection_id
        if not business_connection_id:
            return ProviderSendResult(
                provider=ChannelProvider.TELEGRAM,
                success=False,
                error_code="missing_business_connection_id",
                error_message="Business connection id is required",
            )
        adapter = adapter_for_provider(ChannelProvider.TELEGRAM, account)
        return await adapter.mark_read(
            external_chat_id,
            external_message_id,
            business_connection_id=business_connection_id,
        )

    async def refresh(self, account: ChannelAccount) -> ChannelAccount:
        await self.sync(account)
        if account.telegram_business_enabled and account.status == ChannelAccountStatus.DISABLED:
            account.status = ChannelAccountStatus.WEBHOOK_CONFIGURED
            account.last_error = None
            AuditService(self.db).log(
                action="telegram_business_reconnected",
                entity_type="channel_account",
                shop_id=account.shop_id,
                actor_user_id=None,
                entity_id=str(account.id),
                metadata={
                    "business_connection_id": account.telegram_business_connection_id,
                    "source": "refresh",
                },
            )
        elif not account.telegram_business_enabled and account.connection_mode in {
            TelegramConnectionMode.BUSINESS,
            TelegramConnectionMode.HYBRID,
        }:
            account.status = ChannelAccountStatus.DISABLED
            account.last_error = "Telegram Business connection disabled"
        self.db.commit()
        self.db.refresh(account)
        return account

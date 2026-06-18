from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.channels.adapters import BaleProviderAdapter, InstagramProviderAdapter, RubikaProviderAdapter, TelegramProviderAdapter, WhatsAppProviderAdapter
from app.core.security import decrypt_secret, encrypt_secret
from app.domain.enums import ChannelAccountStatus, ChannelProvider
from app.domain.models import ChannelAccount
from app.schemas.channels import ChannelAccountCreate, ChannelAccountCredentials, ChannelAccountUpdate
from app.services.audit_service import AuditService


def _decrypt(value: str | None) -> str | None:
    return decrypt_secret(value) if value else None


def adapter_for_provider(provider: ChannelProvider, account: ChannelAccount | None = None):
    access_token = _decrypt(account.access_token_encrypted) if account else None
    bot_token = _decrypt(account.bot_token_encrypted) if account else None
    webhook_secret = _decrypt(account.webhook_secret_encrypted) if account else None
    return {
        ChannelProvider.INSTAGRAM: InstagramProviderAdapter(webhook_secret),
        ChannelProvider.WHATSAPP: WhatsAppProviderAdapter(access_token=access_token, phone_number_id=account.phone_number_id if account else None, verify_token=account.webhook_verify_token if account else None, app_secret=webhook_secret),
        ChannelProvider.TELEGRAM: TelegramProviderAdapter(bot_token=bot_token, webhook_secret=webhook_secret, local_base_url=(account.settings_json or {}).get("local_bot_api_base_url") if account else None),
        ChannelProvider.BALE: BaleProviderAdapter(bot_token=bot_token, webhook_secret=webhook_secret, local_base_url=(account.settings_json or {}).get("local_bot_api_base_url") if account else None),
        ChannelProvider.RUBIKA: RubikaProviderAdapter(bot_token=bot_token, webhook_secret=webhook_secret, local_base_url=(account.settings_json or {}).get("local_bot_api_base_url") if account else None),
    }[provider]


class ChannelAccountService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_shop(self, shop_id: UUID) -> list[ChannelAccount]:
        return list(self.db.scalars(select(ChannelAccount).where(ChannelAccount.shop_id == shop_id).order_by(ChannelAccount.created_at.desc())).all())

    def get(self, shop_id: UUID, account_id: UUID) -> ChannelAccount | None:
        return self.db.scalar(select(ChannelAccount).where(ChannelAccount.shop_id == shop_id, ChannelAccount.id == account_id))

    def create(self, shop_id: UUID, payload: ChannelAccountCreate) -> ChannelAccount:
        capabilities = adapter_for_provider(payload.provider).get_capabilities().model_dump(mode="json")
        account = ChannelAccount(shop_id=shop_id, provider=payload.provider, display_name=payload.display_name, external_account_id=payload.external_account_id, phone_number_id=payload.phone_number_id, bot_username=payload.bot_username, bot_id=payload.bot_id, webhook_url=payload.webhook_url, webhook_verify_token=payload.webhook_verify_token, token_expires_at=payload.token_expires_at, scopes_json=payload.scopes, capabilities_json=payload.capabilities or capabilities, settings_json=payload.settings)
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def update(self, account: ChannelAccount, payload: ChannelAccountUpdate) -> ChannelAccount:
        values = payload.model_dump(exclude_unset=True)
        if "capabilities" in values:
            values["capabilities_json"] = values.pop("capabilities")
        if "settings" in values:
            values["settings_json"] = values.pop("settings")
        if "scopes" in values:
            values["scopes_json"] = values.pop("scopes")
        for key, value in values.items():
            setattr(account, key, value)
        self.db.commit()
        self.db.refresh(account)
        return account

    def save_credentials(self, account: ChannelAccount, payload: ChannelAccountCredentials, actor_user_id: UUID) -> ChannelAccount:
        for raw_name, encrypted_name in (("access_token", "access_token_encrypted"), ("refresh_token", "refresh_token_encrypted"), ("bot_token", "bot_token_encrypted"), ("webhook_secret", "webhook_secret_encrypted")):
            value = getattr(payload, raw_name)
            if value is not None:
                setattr(account, encrypted_name, encrypt_secret(value) if value else None)
        if payload.webhook_verify_token is not None:
            account.webhook_verify_token = payload.webhook_verify_token or None
        if payload.token_expires_at is not None:
            account.token_expires_at = payload.token_expires_at
        account.status = ChannelAccountStatus.CONNECTED if (account.access_token_encrypted or account.bot_token_encrypted) else ChannelAccountStatus.DRAFT
        AuditService(self.db).log(action="channel_credentials_updated", entity_type="channel_account", shop_id=account.shop_id, actor_user_id=actor_user_id, entity_id=str(account.id), metadata={"provider": account.provider.value, "credential_fields": sorted(payload.model_fields_set)})
        self.db.commit()
        self.db.refresh(account)
        return account

    def decrypt_access_token(self, account: ChannelAccount) -> str | None:
        return _decrypt(account.access_token_encrypted)

    async def validate(self, account: ChannelAccount) -> ChannelAccount:
        try:
            valid = await adapter_for_provider(account.provider, account).validate_credentials()
            account.status = ChannelAccountStatus.CONNECTED if valid else ChannelAccountStatus.ERROR
            account.last_error = None if valid else "Provider rejected the configured credentials"
        except Exception:
            valid = False
            account.status = ChannelAccountStatus.ERROR
            account.last_error = "Credential validation failed"
        account.last_validation_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(account)
        return account

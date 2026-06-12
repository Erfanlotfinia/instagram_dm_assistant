from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.channels.adapters import (
    BaleProviderAdapter,
    InstagramProviderAdapter,
    RubikaProviderAdapter,
    TelegramProviderAdapter,
    WhatsAppProviderAdapter,
)
from app.core.security import decrypt_secret, encrypt_secret
from app.domain.enums import ChannelAccountStatus, ChannelProvider
from app.domain.models import ChannelAccount
from app.schemas.channels import ChannelAccountCreate


def adapter_for_provider(
    provider: ChannelProvider, account: ChannelAccount | None = None
):
    access_token = (
        decrypt_secret(account.encrypted_access_token)
        if account and account.encrypted_access_token
        else None
    )
    bot_token = (
        decrypt_secret(account.encrypted_bot_token)
        if account and account.encrypted_bot_token
        else None
    )
    return {
        ChannelProvider.INSTAGRAM: InstagramProviderAdapter(
            account.webhook_secret if account else None
        ),
        ChannelProvider.WHATSAPP: WhatsAppProviderAdapter(
            access_token=access_token,
            phone_number_id=account.phone_number_id if account else None,
            verify_token=account.webhook_verify_token if account else None,
            app_secret=account.webhook_secret if account else None,
        ),
        ChannelProvider.TELEGRAM: TelegramProviderAdapter(
            bot_token=bot_token,
            webhook_secret=account.webhook_secret if account else None,
            local_base_url=(
                (account.settings_json or {}).get("local_bot_api_base_url")
                if account
                else None
            ),
        ),
        ChannelProvider.BALE: BaleProviderAdapter(),
        ChannelProvider.RUBIKA: RubikaProviderAdapter(),
    }[provider]


class ChannelAccountService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_shop(self, shop_id: UUID) -> list[ChannelAccount]:
        return list(
            self.db.scalars(
                select(ChannelAccount)
                .where(ChannelAccount.shop_id == shop_id)
                .order_by(ChannelAccount.created_at.desc())
            ).all()
        )

    def create(self, shop_id: UUID, payload: ChannelAccountCreate) -> ChannelAccount:
        capabilities = (
            adapter_for_provider(payload.provider)
            .get_capabilities()
            .model_dump(mode="json")
        )
        account = ChannelAccount(
            shop_id=shop_id,
            provider=payload.provider,
            display_name=payload.display_name,
            external_account_id=payload.external_account_id,
            phone_number_id=payload.phone_number_id,
            bot_username=payload.bot_username,
            bot_id=payload.bot_id,
            webhook_verify_token=payload.webhook_verify_token,
            webhook_secret=payload.app_secret or payload.webhook_secret,
            encrypted_access_token=(
                encrypt_secret(payload.access_token) if payload.access_token else None
            ),
            encrypted_bot_token=(
                encrypt_secret(payload.bot_token) if payload.bot_token else None
            ),
            status=(
                ChannelAccountStatus.CONNECTED
                if (payload.access_token or payload.bot_token)
                else ChannelAccountStatus.DRAFT
            ),
            capabilities_json=capabilities,
            settings_json={
                **payload.settings_json,
                **(
                    {"default_language_code": payload.default_language_code}
                    if payload.default_language_code
                    else {}
                ),
            },
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def get(self, shop_id: UUID, account_id: UUID) -> ChannelAccount | None:
        return self.db.scalar(
            select(ChannelAccount).where(
                ChannelAccount.shop_id == shop_id, ChannelAccount.id == account_id
            )
        )

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import (
    ChannelAccountStatus,
    ChannelProvider,
    InstagramAccountStatus,
)
from app.domain.models import ChannelAccount, InstagramAccount


def _legacy_status_for_channel(status: ChannelAccountStatus) -> InstagramAccountStatus:
    if status == ChannelAccountStatus.DISABLED:
        return InstagramAccountStatus.DISCONNECTED
    if status in {ChannelAccountStatus.CONNECTED, ChannelAccountStatus.WEBHOOK_CONFIGURED}:
        return InstagramAccountStatus.CONNECTED
    if status == ChannelAccountStatus.ERROR:
        return InstagramAccountStatus.EXPIRED
    return InstagramAccountStatus.DISCONNECTED


def sync_legacy_instagram_account_from_channel(
    db: Session, channel_account: ChannelAccount
) -> InstagramAccount | None:
    """Mirror a connected Instagram ChannelAccount into the legacy instagram_accounts table.

    Runtime messaging uses ChannelAccount. Legacy rows exist so older features that still
    FK to instagram_accounts (DM simulator, triggers, product maps, settings) keep working.
    """
    if channel_account.provider != ChannelProvider.INSTAGRAM:
        return None
    if not channel_account.external_account_id:
        return None

    settings = dict(channel_account.settings_json or {})
    legacy_id = settings.get("legacy_instagram_account_id")
    legacy: InstagramAccount | None = None
    if legacy_id:
        legacy = db.get(InstagramAccount, UUID(str(legacy_id)))
    if legacy is None:
        legacy = db.scalar(
            select(InstagramAccount).where(
                InstagramAccount.shop_id == channel_account.shop_id,
                InstagramAccount.ig_user_id == channel_account.external_account_id,
            )
        )

    username = (
        settings.get("instagram_username")
        or channel_account.bot_username
        or channel_account.display_name.removeprefix("@")
        or channel_account.display_name
    )
    page_id = settings.get("page_id")
    legacy_status = _legacy_status_for_channel(channel_account.status)
    webhook_enabled = channel_account.status == ChannelAccountStatus.WEBHOOK_CONFIGURED

    if legacy is None:
        if channel_account.status == ChannelAccountStatus.DISABLED:
            return None
        if not channel_account.access_token_encrypted:
            return None
        legacy = InstagramAccount(
            shop_id=channel_account.shop_id,
            ig_user_id=channel_account.external_account_id,
            page_id=str(page_id) if page_id else None,
            username=str(username),
            access_token_encrypted=channel_account.access_token_encrypted,
            token_expires_at=channel_account.token_expires_at,
            webhook_enabled=webhook_enabled,
            status=legacy_status,
        )
        db.add(legacy)
        db.flush()
    else:
        legacy.page_id = str(page_id) if page_id else legacy.page_id
        legacy.username = str(username)
        legacy.token_expires_at = channel_account.token_expires_at
        legacy.webhook_enabled = webhook_enabled
        legacy.status = legacy_status
        if channel_account.access_token_encrypted:
            legacy.access_token_encrypted = channel_account.access_token_encrypted
        elif channel_account.status == ChannelAccountStatus.DISABLED:
            legacy.status = InstagramAccountStatus.DISCONNECTED

    if settings.get("legacy_instagram_account_id") != str(legacy.id):
        settings["legacy_instagram_account_id"] = str(legacy.id)
        channel_account.settings_json = settings

    return legacy


def ensure_legacy_instagram_accounts_for_shop(db: Session, shop_id: UUID) -> None:
    """Lazy-heal legacy rows for OAuth-connected shops on read paths."""
    channel_accounts = list(
        db.scalars(
            select(ChannelAccount).where(
                ChannelAccount.shop_id == shop_id,
                ChannelAccount.provider == ChannelProvider.INSTAGRAM,
                ChannelAccount.status != ChannelAccountStatus.DISABLED,
            )
        ).all()
    )
    for account in channel_accounts:
        sync_legacy_instagram_account_from_channel(db, account)
    if channel_accounts:
        db.commit()


def ensure_channel_account_for_legacy_instagram(
    db: Session, legacy: InstagramAccount
) -> ChannelAccount:
    """Ensure a canonical ChannelAccount exists for a legacy InstagramAccount row."""
    account_id = db.scalar(
        select(ChannelAccount.id).where(
            ChannelAccount.provider == ChannelProvider.INSTAGRAM,
            ChannelAccount.settings_json["legacy_instagram_account_id"].astext
            == str(legacy.id),
        )
    )
    if account_id is not None:
        return db.get(ChannelAccount, account_id)

    channel_account = db.scalar(
        select(ChannelAccount).where(
            ChannelAccount.shop_id == legacy.shop_id,
            ChannelAccount.provider == ChannelProvider.INSTAGRAM,
            ChannelAccount.external_account_id == legacy.ig_user_id,
        )
    )
    if channel_account is None:
        channel_account = ChannelAccount(
            shop_id=legacy.shop_id,
            provider=ChannelProvider.INSTAGRAM,
            display_name=legacy.username,
            external_account_id=legacy.ig_user_id,
            bot_username=legacy.username,
            access_token_encrypted=legacy.access_token_encrypted,
            token_expires_at=legacy.token_expires_at,
            status=(
                ChannelAccountStatus.WEBHOOK_CONFIGURED
                if legacy.webhook_enabled
                else ChannelAccountStatus.CONNECTED
            ),
            capabilities_json={
                "supports_webhook": True,
                "supports_text": True,
                "supports_images": True,
            },
            settings_json={"legacy_instagram_account_id": str(legacy.id)},
        )
        db.add(channel_account)
        db.flush()
    else:
        sync_legacy_instagram_account_from_channel(db, channel_account)

    settings = dict(channel_account.settings_json or {})
    if settings.get("legacy_instagram_account_id") != str(legacy.id):
        settings["legacy_instagram_account_id"] = str(legacy.id)
        channel_account.settings_json = settings
    if legacy.access_token_encrypted and not channel_account.access_token_encrypted:
        channel_account.access_token_encrypted = legacy.access_token_encrypted
    db.commit()
    db.refresh(channel_account)
    return channel_account


def get_instagram_channel_account_id(db: Session, instagram_account_id: UUID) -> UUID:
    account_id = db.scalar(
        select(ChannelAccount.id).where(
            ChannelAccount.provider == ChannelProvider.INSTAGRAM,
            ChannelAccount.settings_json["legacy_instagram_account_id"].astext
            == str(instagram_account_id),
        )
    )
    if account_id is not None:
        return account_id

    legacy = db.get(InstagramAccount, instagram_account_id)
    if legacy is None:
        raise ValueError(
            f"Instagram account {instagram_account_id} has no matching channel account"
        )
    channel_account = db.scalar(
        select(ChannelAccount).where(
            ChannelAccount.shop_id == legacy.shop_id,
            ChannelAccount.provider == ChannelProvider.INSTAGRAM,
            ChannelAccount.external_account_id == legacy.ig_user_id,
        )
    )
    if channel_account is None:
        return ensure_channel_account_for_legacy_instagram(db, legacy).id
    sync_legacy_instagram_account_from_channel(db, channel_account)
    db.commit()
    db.refresh(channel_account)
    return channel_account.id

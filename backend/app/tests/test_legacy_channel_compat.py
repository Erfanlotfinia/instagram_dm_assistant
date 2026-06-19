from sqlalchemy import select

from app.core.security import encrypt_secret
from app.domain.enums import ChannelAccountStatus, ChannelProvider, InstagramAccountStatus
from app.domain.models import ChannelAccount, InstagramAccount
from app.services.legacy_channel_compat import (
    ensure_legacy_instagram_accounts_for_shop,
    get_instagram_channel_account_id,
    sync_legacy_instagram_account_from_channel,
)


def test_sync_legacy_instagram_account_from_oauth_channel(db_session, demo_shop):
    channel = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.INSTAGRAM,
        display_name="@demo_shop",
        external_account_id="ig-biz-123",
        bot_username="demo_shop",
        access_token_encrypted=encrypt_secret("page-token"),
        status=ChannelAccountStatus.CONNECTED,
        capabilities_json={"supports_text": True},
        settings_json={
            "page_id": "page-1",
            "page_name": "Demo Page",
            "instagram_username": "demo_shop",
        },
    )
    db_session.add(channel)
    db_session.commit()

    legacy = sync_legacy_instagram_account_from_channel(db_session, channel)
    db_session.commit()
    db_session.refresh(channel)

    assert legacy is not None
    assert legacy.ig_user_id == "ig-biz-123"
    assert legacy.username == "demo_shop"
    assert legacy.page_id == "page-1"
    assert legacy.status == InstagramAccountStatus.CONNECTED
    assert channel.settings_json["legacy_instagram_account_id"] == str(legacy.id)


def test_list_heals_missing_legacy_rows(db_session, demo_shop):
    channel = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.INSTAGRAM,
        display_name="@healed",
        external_account_id="ig-healed",
        access_token_encrypted=encrypt_secret("token"),
        status=ChannelAccountStatus.WEBHOOK_CONFIGURED,
        capabilities_json={},
        settings_json={"instagram_username": "healed"},
    )
    db_session.add(channel)
    db_session.commit()

    ensure_legacy_instagram_accounts_for_shop(db_session, demo_shop.id)

    legacy = db_session.scalar(
        select(InstagramAccount).where(
            InstagramAccount.shop_id == demo_shop.id,
            InstagramAccount.ig_user_id == "ig-healed",
        )
    )
    assert legacy is not None
    assert legacy.webhook_enabled is True
    assert legacy.status == InstagramAccountStatus.CONNECTED


def test_get_instagram_channel_account_id_falls_back_to_external_account_id(db_session, demo_shop):
    legacy = InstagramAccount(
        shop_id=demo_shop.id,
        ig_user_id="ig-fallback",
        username="fallback",
        access_token_encrypted=encrypt_secret("token"),
        status=InstagramAccountStatus.CONNECTED,
    )
    channel = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.INSTAGRAM,
        display_name="@fallback",
        external_account_id="ig-fallback",
        access_token_encrypted=legacy.access_token_encrypted,
        status=ChannelAccountStatus.CONNECTED,
        capabilities_json={},
        settings_json={},
    )
    db_session.add_all([legacy, channel])
    db_session.commit()

    resolved = get_instagram_channel_account_id(db_session, legacy.id)
    assert resolved == channel.id
    db_session.refresh(channel)
    assert channel.settings_json["legacy_instagram_account_id"] == str(legacy.id)

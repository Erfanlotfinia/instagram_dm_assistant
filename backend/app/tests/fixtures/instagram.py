from __future__ import annotations

from app.core.security import encrypt_secret
from app.domain.enums import (
    ChannelAccountStatus,
    ChannelProvider,
    InstagramAccountStatus,
)
from app.domain.models import ChannelAccount, Conversation, Customer, InstagramAccount


def seed_instagram_channel_account(
    db_session,
    shop,
    *,
    ig_user_id: str = "17841400000000001",
    username: str = "demo_shop",
    token: str = "token",
    webhook_enabled: bool = True,
) -> tuple[InstagramAccount, ChannelAccount]:
    account = InstagramAccount(
        shop_id=shop.id,
        ig_user_id=ig_user_id,
        username=username,
        access_token_encrypted=encrypt_secret(token),
        webhook_enabled=webhook_enabled,
        status=InstagramAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.flush()

    channel_account = ChannelAccount(
        shop_id=shop.id,
        provider=ChannelProvider.INSTAGRAM,
        display_name=username,
        external_account_id=ig_user_id,
        bot_username=username,
        access_token_encrypted=account.access_token_encrypted,
        status=(
            ChannelAccountStatus.WEBHOOK_CONFIGURED
            if webhook_enabled
            else ChannelAccountStatus.CONNECTED
        ),
        capabilities_json={
            "supports_webhook": True,
            "supports_text": True,
            "supports_images": True,
        },
        settings_json={"legacy_instagram_account_id": str(account.id)},
    )
    db_session.add(channel_account)
    db_session.flush()
    return account, channel_account


def build_instagram_conversation(
    db_session,
    shop,
    account: InstagramAccount,
    channel_account: ChannelAccount,
    customer: Customer,
    *,
    external_id: str | None = None,
    **conversation_kwargs,
) -> Conversation:
    external = external_id or customer.instagram_user_id or "unknown"
    conversation = Conversation(
        shop_id=shop.id,
        instagram_account_id=account.id,
        channel_account_id=channel_account.id,
        channel_provider=ChannelProvider.INSTAGRAM.value,
        external_conversation_id=external,
        channel_conversation_id=external,
        channel_customer_id=external,
        customer_id=customer.id,
        **conversation_kwargs,
    )
    db_session.add(conversation)
    db_session.flush()
    return conversation

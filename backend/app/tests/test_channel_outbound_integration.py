from app.core.security import encrypt_secret
from app.domain.enums import (
    ChannelAccountStatus,
    ChannelProvider,
    InstagramAccountStatus,
    MessageDirection,
)
from app.domain.models import ChannelAccount, Conversation, Customer, InstagramAccount
from app.services.channel_outbound_service import ChannelOutboundService


def test_channel_outbound_stores_outbound_message(db_session, demo_shop) -> None:
    account = InstagramAccount(
        shop_id=demo_shop.id,
        ig_user_id="17841400000000001",
        username="demo_shop",
        access_token_encrypted=encrypt_secret("token"),
        status=InstagramAccountStatus.CONNECTED,
    )
    customer = Customer(shop_id=demo_shop.id, instagram_user_id="cust-1")
    db_session.add(account)
    db_session.flush()
    channel_account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.INSTAGRAM,
        display_name=account.username,
        external_account_id=account.ig_user_id,
        access_token_encrypted=account.access_token_encrypted,
        status=ChannelAccountStatus.CONNECTED,
        settings_json={"legacy_instagram_account_id": str(account.id)},
    )
    db_session.add_all([account, channel_account, customer])
    db_session.flush()

    conversation = Conversation(
        shop_id=demo_shop.id,
        instagram_account_id=account.id,
        channel_account_id=channel_account.id,
        channel_provider=ChannelProvider.INSTAGRAM.value,
        external_conversation_id=customer.instagram_user_id,
        customer_id=customer.id,
    )
    db_session.add(conversation)
    db_session.commit()

    message = ChannelOutboundService(db_session).send_text_message(conversation.id, "Thanks!")
    assert message.direction == MessageDirection.OUTBOUND
    assert message.text == "Thanks!"
    assert message.raw_payload["success"] is True
    assert message.raw_payload["raw_response"]["simulation"] is True

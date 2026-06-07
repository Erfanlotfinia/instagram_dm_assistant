from app.domain.enums import MessageDirection
from app.domain.models import Conversation, Customer, InstagramAccount
from app.core.security import encrypt_secret
from app.domain.enums import InstagramAccountStatus
from app.services.instagram_send_service import InstagramSendService


def test_placeholder_send_stores_outbound_message(db_session, demo_shop) -> None:
    account = InstagramAccount(
        shop_id=demo_shop.id,
        ig_user_id="17841400000000001",
        username="demo_shop",
        access_token_encrypted=encrypt_secret("token"),
        status=InstagramAccountStatus.CONNECTED,
    )
    customer = Customer(shop_id=demo_shop.id, instagram_user_id="cust-1")
    db_session.add_all([account, customer])
    db_session.flush()

    conversation = Conversation(
        shop_id=demo_shop.id,
        instagram_account_id=account.id,
        customer_id=customer.id,
    )
    db_session.add(conversation)
    db_session.commit()

    message = InstagramSendService(db_session).send_text_message(conversation.id, "Thanks!")
    assert message.direction == MessageDirection.OUTBOUND
    assert message.text == "Thanks!"
    assert message.raw_payload["mode"] == "placeholder"

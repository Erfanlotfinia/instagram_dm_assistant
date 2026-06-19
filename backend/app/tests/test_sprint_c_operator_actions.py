from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.core.security import encrypt_secret
from app.domain.enums import InstagramAccountStatus, OrderStatus
from app.domain.models import InstagramAccount
from app.services.order_service import OrderService
from app.services.webhook_ingestion_service import WebhookIngestionService
from app.tests.fixtures.agent import seed_order_flow_data
from app.tests.fixtures.instagram_webhook import SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD
from app.tests.fixtures.orders import seed_draft_order


def _create_conversation(client, auth_headers, db_session, demo_shop) -> str:
    account = InstagramAccount(
        shop_id=demo_shop.id,
        ig_user_id="17841400000000001",
        username="demo_shop",
        access_token_encrypted=encrypt_secret("token"),
        status=InstagramAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.commit()
    WebhookIngestionService(db_session, publisher=MagicMock()).handle_instagram_payload(
        SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD
    )
    response = client.get(f"/api/v1/shops/{demo_shop.id}/conversations", headers=auth_headers)
    return response.json()[0]["id"]


def test_assign_conversation(client, auth_headers, db_session, demo_shop, admin_user) -> None:
    conversation_id = _create_conversation(client, auth_headers, db_session, demo_shop)
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/conversations/{conversation_id}/assign",
        headers=auth_headers,
        json={"operator_id": str(admin_user.id)},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["assigned_operator_id"] == str(admin_user.id)


@patch("app.services.channel_outbound_service.ChannelOutboundService.send_text_message")
def test_manual_message_creates_audit_and_event(
    mock_send, client, auth_headers, db_session, demo_shop, admin_user
) -> None:
    from uuid import uuid4

    from app.domain.models import Message
    from app.domain.enums import MessageDirection, MessageType, MessageChannel

    conversation_id = _create_conversation(client, auth_headers, db_session, demo_shop)

    def _persist_outbound_message(conv_id, text, **_kwargs):
        message = Message(
            id=uuid4(),
            conversation_id=conv_id,
            direction=MessageDirection.OUTBOUND,
            channel=MessageChannel.INSTAGRAM,
            message_type=MessageType.TEXT,
            text=text,
        )
        db_session.add(message)
        db_session.flush()
        return message

    mock_send.side_effect = _persist_outbound_message
    client.post(
        f"/api/v1/shops/{demo_shop.id}/conversations/{conversation_id}/take-over",
        headers=auth_headers,
    )
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/conversations/{conversation_id}/send-manual-message",
        headers=auth_headers,
        json={"text": "Hello from operator"},
    )
    assert response.status_code == 201

    detail = client.get(
        f"/api/v1/shops/{demo_shop.id}/conversations/{conversation_id}",
        headers=auth_headers,
    ).json()
    event_types = [event["event_type"] for event in detail["events"]]
    assert "outbound_message_sent" in event_types


def test_customer_profile_patch(client, auth_headers, db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    response = client.patch(
        f"/api/v1/shops/{demo_shop.id}/customers/{data['customer'].id}",
        headers=auth_headers,
        json={"full_name": "Sara Ahmadi", "phone": "09120000000"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Sara Ahmadi"
    assert body["phone"] == "09120000000"


@patch("app.services.channel_outbound_service.ChannelOutboundService.send_text_message")
def test_send_payment_link(mock_send, client, auth_headers, db_session, demo_shop, admin_user) -> None:
    from datetime import UTC, datetime
    from app.domain.models import Message
    from app.domain.enums import MessageDirection, MessageType, MessageChannel

    data = seed_order_flow_data(db_session, demo_shop)
    mock_send.return_value = Message(
        conversation_id=data["conversation"].id,
        direction=MessageDirection.OUTBOUND,
        channel=MessageChannel.INSTAGRAM,
        message_type=MessageType.TEXT,
        text="pay",
    )
    order = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=data["product"],
        variant=data["variant"],
    )
    order.customer_confirmed_at = datetime.now(UTC)
    db_session.commit()

    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/orders/{order.id}/send-payment-link",
        headers=auth_headers,
        json={},
    )
    assert response.status_code == 200
    assert response.json()["payment_status"] == "pending"


def test_mark_paid_and_cancel_order(client, auth_headers, db_session, demo_shop, admin_user) -> None:
    from datetime import UTC, datetime
    from app.services.payment_service import PaymentService

    data = seed_order_flow_data(db_session, demo_shop)
    order = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=data["product"],
        variant=data["variant"],
    )
    order.customer_confirmed_at = datetime.now(UTC)
    db_session.commit()
    PaymentService(db_session).send_payment_link(demo_shop.id, order.id, admin_user)

    paid = client.post(
        f"/api/v1/shops/{demo_shop.id}/orders/{order.id}/mark-paid",
        headers=auth_headers,
    )
    assert paid.status_code == 200
    assert paid.json()["status"] == OrderStatus.PAID.value

    from app.domain.models import Conversation, Customer

    customer2 = Customer(shop_id=demo_shop.id, instagram_user_id="cust-cancel-2")
    db_session.add(customer2)
    db_session.flush()
    conversation2 = Conversation(
        shop_id=demo_shop.id,
        instagram_account_id=data["account"].id,
        customer_id=customer2.id,
    )
    db_session.add(conversation2)
    db_session.flush()
    order2 = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=customer2.id,
        conversation_id=conversation2.id,
        product=data["product"],
        variant=data["variant"],
    )
    cancelled = client.post(
        f"/api/v1/shops/{demo_shop.id}/orders/{order2.id}/cancel",
        headers=auth_headers,
        json={"reason": "Customer changed mind"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == OrderStatus.CANCELLED.value


def test_shop_isolation_for_assign(client, auth_headers, db_session, demo_shop, admin_user) -> None:
    from app.domain.models import Shop, ShopMember
    from app.domain.enums import UserRole

    other_shop = Shop(name="Other", slug="other-shop")
    db_session.add(other_shop)
    db_session.flush()
    db_session.add(ShopMember(shop_id=other_shop.id, user_id=admin_user.id, role=UserRole.OWNER))
    db_session.commit()

    conversation_id = _create_conversation(client, auth_headers, db_session, demo_shop)
    response = client.post(
        f"/api/v1/shops/{other_shop.id}/conversations/{conversation_id}/assign",
        headers=auth_headers,
        json={"operator_id": str(admin_user.id)},
    )
    assert response.status_code == 404

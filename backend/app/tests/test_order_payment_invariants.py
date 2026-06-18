from datetime import UTC, datetime
from unittest.mock import patch

from app.domain.enums import OrderStatus
from app.services.payment_service import PaymentService
from app.tests.fixtures.orders import seed_draft_order
from app.tests.fixtures.agent import seed_order_flow_data


def test_send_payment_link_requires_customer_confirmation(
    client, auth_headers, db_session, demo_shop, admin_user
) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=data["product"],
        variant=data["variant"],
    )

    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/orders/{order.id}/send-payment-link",
        headers=auth_headers,
        json={},
    )
    assert response.status_code == 400
    assert "Customer confirmation" in response.json()["detail"]


@patch("app.services.channel_outbound_service.ChannelOutboundService.send_text_message")
def test_send_payment_link_admin_override(
    mock_send, client, auth_headers, db_session, demo_shop, admin_user
) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=data["product"],
        variant=data["variant"],
    )

    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/orders/{order.id}/send-payment-link",
        headers=auth_headers,
        json={"admin_override_reason": "Customer confirmed by phone"},
    )
    assert response.status_code == 200


def test_mark_paid_without_reservation_fails(client, auth_headers, db_session, demo_shop, admin_user) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=data["product"],
        variant=data["variant"],
    )
    order.status = OrderStatus.PAYMENT_PENDING
    order.customer_confirmed_at = datetime.now(UTC)
    db_session.commit()

    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/orders/{order.id}/mark-paid",
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "reservation" in response.json()["detail"].lower()


@patch("app.services.channel_outbound_service.ChannelOutboundService.send_text_message")
def test_mark_paid_idempotent(mock_send, client, auth_headers, db_session, demo_shop, admin_user) -> None:
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

    first = client.post(
        f"/api/v1/shops/{demo_shop.id}/orders/{order.id}/mark-paid",
        headers=auth_headers,
    )
    assert first.status_code == 200
    second = client.post(
        f"/api/v1/shops/{demo_shop.id}/orders/{order.id}/mark-paid",
        headers=auth_headers,
    )
    assert second.status_code in {200, 400}

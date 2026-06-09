"""API contract tests for order correctness endpoints."""

from app.domain.enums import OrderStatus
from app.domain.models import Order
from app.tests.fixtures.orders import seed_draft_order, seed_order_flow_data


def test_get_order_correctness(client, auth_headers, demo_shop, db_session, order_product) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=order_product["product"],
        variant=order_product["variant"],
    )
    db_session.commit()

    response = client.get(f"/api/v1/orders/{order.id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(order.id)
    assert body["status"] == OrderStatus.READY_FOR_CONFIRMATION.value


def test_get_order_timeline(client, auth_headers, demo_shop, db_session, order_product) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=order_product["product"],
        variant=order_product["variant"],
    )
    db_session.commit()

    response = client.get(f"/api/v1/orders/{order.id}/timeline", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["order_id"] == str(order.id)


def test_cancel_order_correctness(client, auth_headers, demo_shop, db_session, order_product) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=order_product["product"],
        variant=order_product["variant"],
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/orders/{order.id}/cancel",
        headers=auth_headers,
        json={"reason": "test cancel"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == OrderStatus.CANCELLED.value

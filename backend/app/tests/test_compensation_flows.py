"""Compensation flow tests."""

from unittest.mock import MagicMock

from app.domain.enums import OrderPaymentStatus, OrderStatus
from app.domain.models import Order
from app.integrations.rabbitmq import NoOpPublisher
from app.services.compensation_service import CompensationService
from app.tests.fixtures.orders import seed_order_flow_data


def test_payment_failed_releases_and_fails(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order = Order(
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        status=OrderStatus.PAYMENT_PENDING,
        payment_status=OrderPaymentStatus.PENDING,
        customer_name="Test",
        phone="09120000000",
        city="Tehran",
        address="Test",
        postal_code="1234567890",
    )
    db_session.add(order)
    db_session.flush()

    publisher = NoOpPublisher()
    comp = CompensationService(db_session, publisher=publisher)
    result = comp.handle_payment_failed(order, reason="payment_failed")
    assert result.status == OrderStatus.FAILED


def test_enqueue_compensation_publishes(db_session, demo_shop) -> None:
    publisher = MagicMock()
    comp = CompensationService(db_session, publisher=publisher)
    from uuid import uuid4

    order_id = uuid4()
    shop_id = demo_shop.id
    comp.enqueue_compensation(order_id, shop_id, {"error": "test"})
    publisher.publish.assert_called_once()

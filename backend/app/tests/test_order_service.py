from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.domain.enums import OrderPaymentStatus, OrderStatus
from app.domain.models import Order, OrderItem, Product, ProductVariant
from app.services.order_expiration_service import OrderExpirationService
from app.services.order_service import OrderService
from app.tests.fixtures.orders import seed_complete_slots, seed_draft_order


@pytest.fixture()
def order_product(db_session, demo_shop):
    product = Product(
        shop_id=demo_shop.id,
        title="Order Test Product",
        base_price=Decimal("25.00"),
        currency="USD",
    )
    db_session.add(product)
    db_session.flush()
    variant = ProductVariant(
        product_id=product.id,
        sku="ORD-001",
        color="Red",
        size="M",
        price=Decimal("25.00"),
        stock_quantity=5,
        reserved_quantity=0,
    )
    db_session.add(variant)
    db_session.commit()
    db_session.refresh(product)
    db_session.refresh(variant)
    return {"product": product, "variant": variant}


def test_can_create_draft_requires_complete_slots(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    slots = seed_complete_slots(db_session, data["conversation"].id)
    slots.product_id = data["product"].id
    slots.product_variant_id = data["variant"].id
    db_session.commit()

    service = OrderService(db_session)
    assert service.can_create_draft(slots, data["variant"]) is True

    slots.phone = None
    assert service.can_create_draft(slots, data["variant"]) is False


def test_upsert_draft_order(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    slots = seed_complete_slots(db_session, data["conversation"].id)
    slots.product_id = data["product"].id
    slots.product_variant_id = data["variant"].id
    db_session.commit()

    service = OrderService(db_session)
    order = service.upsert_draft_from_conversation(
        data["conversation"], slots, data["product"], data["variant"]
    )
    assert order is not None
    assert order.status == OrderStatus.WAITING_FOR_CONFIRMATION
    assert len(order.items) == 1
    assert order.items[0].product_title_snapshot == data["product"].title
    assert order.items[0].sku_snapshot == data["variant"].sku


def test_confirm_reserves_inventory(db_session, admin_user, demo_shop, order_product) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=order_product["product"],
        variant=order_product["variant"],
    )

    service = OrderService(db_session)
    confirmed = service.confirm_order(demo_shop.id, order.id, admin_user)
    assert confirmed.status == OrderStatus.WAITING_FOR_PAYMENT
    assert confirmed.payment_status == OrderPaymentStatus.PENDING
    assert confirmed.expires_at is not None

    db_session.refresh(order_product["variant"])
    assert order_product["variant"].reserved_quantity == 1


def test_cancel_releases_inventory(db_session, admin_user, demo_shop, order_product) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=order_product["product"],
        variant=order_product["variant"],
    )
    service = OrderService(db_session)
    service.confirm_order(demo_shop.id, order.id, admin_user)

    cancelled = service.cancel_order(demo_shop.id, order.id, admin_user)
    assert cancelled.status == OrderStatus.CANCELLED

    db_session.refresh(order_product["variant"])
    assert order_product["variant"].reserved_quantity == 0


def test_expire_order_releases_inventory(db_session, admin_user, demo_shop, order_product) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=order_product["product"],
        variant=order_product["variant"],
    )
    service = OrderService(db_session)
    service.confirm_order(demo_shop.id, order.id, admin_user)
    order.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    expired_count = OrderExpirationService(db_session).expire_stale_orders()
    assert expired_count == 1

    db_session.refresh(order)
    assert order.status == OrderStatus.EXPIRED
    db_session.refresh(order_product["variant"])
    assert order_product["variant"].reserved_quantity == 0


def test_cannot_confirm_without_stock(db_session, admin_user, demo_shop, order_product) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order_product["variant"].stock_quantity = 0
    db_session.commit()

    order = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=order_product["product"],
        variant=order_product["variant"],
    )
    service = OrderService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        service.confirm_order(demo_shop.id, order.id, admin_user)
    assert exc_info.value.status_code == 400

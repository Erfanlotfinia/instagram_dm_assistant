"""Integration tests for inventory reservation service."""

from datetime import UTC, datetime, timedelta

from app.domain.enums import InventoryReservationStatus
from app.services.inventory_reservation_service import InventoryReservationService
from app.tests.fixtures.orders import seed_order_flow_data


def test_reserve_refresh_release_confirm(db_session, demo_shop, order_product) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    from app.domain.models import Order

    order = Order(
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        customer_name="Test",
        phone="09120000000",
        city="Tehran",
        address="Test",
        postal_code="1234567890",
    )
    db_session.add(order)
    db_session.flush()

    service = InventoryReservationService(db_session)
    variant = order_product["variant"]
    variant.stock_quantity = 10
    variant.reserved_quantity = 0
    db_session.commit()

    reservation = service.reserve(
        shop_id=demo_shop.id,
        order_id=order.id,
        product_variant_id=variant.id,
        quantity=2,
        ttl_seconds=3600,
    )
    assert reservation.status == InventoryReservationStatus.ACTIVE

    db_session.refresh(variant)
    assert variant.reserved_quantity == 2

    refreshed = service.refresh_reservation(reservation.id, 7200)
    assert refreshed.ttl_seconds == 7200

    confirmed = service.confirm_reservation(reservation.id)
    assert confirmed.status == InventoryReservationStatus.CONFIRMED

    reservation2 = service.reserve(
        shop_id=demo_shop.id,
        order_id=order.id,
        product_variant_id=variant.id,
        quantity=1,
        ttl_seconds=600,
    )
    released = service.release_reservation(reservation2.id, reason="test release")
    assert released.status == InventoryReservationStatus.RELEASED
    db_session.refresh(variant)
    assert variant.reserved_quantity == 2


def test_reserve_idempotent(db_session, demo_shop, order_product) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    from app.domain.models import Order

    order = Order(
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        customer_name="Test",
        phone="09120000000",
        city="Tehran",
        address="Test",
        postal_code="1234567890",
    )
    db_session.add(order)
    db_session.flush()

    service = InventoryReservationService(db_session)
    variant = order_product["variant"]
    variant.stock_quantity = 5
    variant.reserved_quantity = 0
    db_session.commit()

    r1 = service.reserve(
        shop_id=demo_shop.id,
        order_id=order.id,
        product_variant_id=variant.id,
        quantity=1,
        ttl_seconds=600,
    )
    r2 = service.reserve(
        shop_id=demo_shop.id,
        order_id=order.id,
        product_variant_id=variant.id,
        quantity=1,
        ttl_seconds=600,
    )
    assert r1.id == r2.id

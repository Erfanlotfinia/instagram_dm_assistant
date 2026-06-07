import pytest
from fastapi import HTTPException

from app.domain.enums import UserRole
from app.domain.models import Product, ProductVariant
from app.schemas.inventory import InventoryReleaseRequest, InventoryReserveRequest
from app.services.auth_service import AuthService
from app.services.inventory_service import InventoryService


@pytest.fixture()
def variant(db_session, demo_shop) -> ProductVariant:
    product = Product(
        shop_id=demo_shop.id,
        title="Inventory Test Product",
        base_price="10.00",
        currency="USD",
    )
    db_session.add(product)
    db_session.flush()
    variant = ProductVariant(
        product_id=product.id,
        sku="INV-001",
        price="10.00",
        stock_quantity=10,
        reserved_quantity=0,
    )
    db_session.add(variant)
    db_session.commit()
    db_session.refresh(variant)
    return variant


def test_available_stock_calculation() -> None:
    assert InventoryService.available_stock(10, 3) == 7
    assert InventoryService.available_stock(5, 5) == 0


def test_reserve_stock(db_session, admin_user, demo_shop, variant) -> None:
    service = InventoryService(db_session)
    result = service.reserve(
        demo_shop.id,
        variant.id,
        InventoryReserveRequest(quantity=3, reason="Draft order confirmation"),
        admin_user,
    )
    assert result.available_stock == 7
    assert result.reserved_quantity == 3

    db_session.refresh(variant)
    assert variant.reserved_quantity == 3


def test_release_reservation(db_session, admin_user, demo_shop, variant) -> None:
    service = InventoryService(db_session)
    service.reserve(
        demo_shop.id,
        variant.id,
        InventoryReserveRequest(quantity=4, reason="Draft order confirmation"),
        admin_user,
    )
    result = service.release(
        demo_shop.id,
        variant.id,
        InventoryReleaseRequest(quantity=4, reason="Order cancelled"),
        admin_user,
    )
    assert result.available_stock == 10
    assert result.reserved_quantity == 0


def test_cannot_reserve_more_than_available(db_session, admin_user, demo_shop, variant) -> None:
    service = InventoryService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        service.reserve(
            demo_shop.id,
            variant.id,
            InventoryReserveRequest(quantity=11, reason="Over-reserve attempt"),
            admin_user,
        )
    assert exc_info.value.status_code == 400


def test_cannot_release_more_than_reserved(db_session, admin_user, demo_shop, variant) -> None:
    service = InventoryService(db_session)
    service.reserve(
        demo_shop.id,
        variant.id,
        InventoryReserveRequest(quantity=2, reason="Draft order"),
        admin_user,
    )
    with pytest.raises(HTTPException) as exc_info:
        service.release(
            demo_shop.id,
            variant.id,
            InventoryReleaseRequest(quantity=5, reason="Over-release"),
            admin_user,
        )
    assert exc_info.value.status_code == 400


def test_inventory_access_denied_for_non_member(db_session, demo_shop, variant) -> None:
    outsider = AuthService.create_user(
        db_session,
        email="inventory-outsider@test.com",
        password="password123",
        full_name="Outsider",
        role=UserRole.OPERATOR,
    )
    service = InventoryService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        service.reserve(
            demo_shop.id,
            variant.id,
            InventoryReserveRequest(quantity=1, reason="Unauthorized"),
            outsider,
        )
    assert exc_info.value.status_code == 403

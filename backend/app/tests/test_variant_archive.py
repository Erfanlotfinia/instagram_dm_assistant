import pytest
from decimal import Decimal
from fastapi import HTTPException

from app.domain.models import Product, ProductVariant
from app.services.variant_service import VariantService


def test_archive_variant_success(db_session, demo_shop, admin_user) -> None:
    product = Product(shop_id=demo_shop.id, title="Shirt", base_price=Decimal("20.00"), currency="USD")
    db_session.add(product)
    db_session.flush()
    variant = ProductVariant(
        product_id=product.id,
        color="Blue",
        size="M",
        sku="SH-BLU-M",
        price=Decimal("20.00"),
        stock_quantity=5,
        reserved_quantity=0,
        is_active=True,
    )
    db_session.add(variant)
    db_session.commit()

    archived = VariantService(db_session).archive_variant(demo_shop.id, variant.id, admin_user)
    assert archived.is_active is False


def test_cannot_archive_variant_with_reserved_inventory(db_session, demo_shop, admin_user) -> None:
    product = Product(shop_id=demo_shop.id, title="Pants", base_price=Decimal("30.00"), currency="USD")
    db_session.add(product)
    db_session.flush()
    variant = ProductVariant(
        product_id=product.id,
        color="Black",
        size="L",
        sku="PN-BLK-L",
        price=Decimal("30.00"),
        stock_quantity=5,
        reserved_quantity=2,
        is_active=True,
    )
    db_session.add(variant)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        VariantService(db_session).archive_variant(demo_shop.id, variant.id, admin_user)
    assert exc.value.status_code == 400

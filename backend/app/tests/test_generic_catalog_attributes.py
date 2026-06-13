from decimal import Decimal

from app.domain.models import (
    AttributeAlias,
    CatalogAttributeDefinition,
    Product,
    ProductVariant,
    VariantAttribute,
)
from app.services.attribute_normalizer import AttributeNormalizer
from app.services.generic_variant_resolver import GenericVariantResolver


def test_attribute_normalizer_supports_electronics_persian_storage(db_session, demo_shop):
    storage = CatalogAttributeDefinition(shop_id=demo_shop.id, name="Storage", slug="storage", is_variant_defining=True, is_required=True)
    db_session.add(storage)
    db_session.flush()
    db_session.add(AttributeAlias(shop_id=demo_shop.id, attribute_definition_id=storage.id, raw_value="۱۲۸ گیگ", normalized_value="128GB", language="fa", confidence=0.96))
    db_session.commit()

    result = AttributeNormalizer(db_session).normalize(shop_id=demo_shop.id, category_id=None, attribute_slug="storage", raw_value="۱۲۸ گیگ")

    assert result.matched is True
    assert result.normalized_value == "128GB"
    assert result.source == "shop_alias"


def test_generic_variant_resolver_matches_variant_attributes(db_session, demo_shop):
    product = Product(shop_id=demo_shop.id, title="iPhone 13", base_price=Decimal("700.00"), currency="USD", category="electronics")
    db_session.add(product)
    db_session.flush()
    variant = ProductVariant(product_id=product.id, sku="IPH13-128-BLK", price=Decimal("700.00"), stock_quantity=3, reserved_quantity=0, is_active=True)
    storage = CatalogAttributeDefinition(shop_id=demo_shop.id, name="Storage", slug="storage", is_variant_defining=True, is_required=True)
    color = CatalogAttributeDefinition(shop_id=demo_shop.id, name="Color", slug="color", is_variant_defining=True, is_required=True)
    db_session.add_all([variant, storage, color])
    db_session.flush()
    db_session.add_all([
        AttributeAlias(shop_id=demo_shop.id, attribute_definition_id=storage.id, raw_value="۱۲۸", normalized_value="128GB", language="fa", confidence=0.96),
        AttributeAlias(shop_id=demo_shop.id, attribute_definition_id=color.id, raw_value="مشکی", normalized_value="black", language="fa", confidence=0.98),
        VariantAttribute(product_variant_id=variant.id, attribute_definition_id=storage.id, value_json="128GB", normalized_value_json="128GB"),
        VariantAttribute(product_variant_id=variant.id, attribute_definition_id=color.id, value_json="black", normalized_value_json="black"),
    ])
    db_session.commit()

    result = GenericVariantResolver(db_session).resolve(shop_id=demo_shop.id, product_id=product.id, raw_requested_attributes={"storage": "۱۲۸", "color": "مشکی"}, quantity=1)

    assert result.matched is True
    assert result.variant_id == variant.id
    assert result.normalized_attributes == {"storage": "128GB", "color": "black"}
    assert result.available_stock == 3


def test_generic_variant_resolver_reports_missing_required_attribute(db_session, demo_shop):
    product = Product(shop_id=demo_shop.id, title="Foundation", base_price=Decimal("30.00"), currency="USD", category="cosmetics")
    shade = CatalogAttributeDefinition(shop_id=demo_shop.id, name="Shade", slug="shade", is_variant_defining=True, is_required=True)
    db_session.add_all([product, shade])
    db_session.commit()

    result = GenericVariantResolver(db_session).resolve(shop_id=demo_shop.id, product_id=product.id, raw_requested_attributes={}, quantity=1)

    assert result.matched is False
    assert "missing_shade" in result.mismatch_reasons

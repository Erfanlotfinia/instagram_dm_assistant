from decimal import Decimal

from app.domain.models import (
    AttributeAlias,
    CatalogAttributeDefinition,
    Product,
    ProductCategory,
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


def test_generic_variant_resolver_scopes_required_attributes_to_product_category(db_session, demo_shop):
    electronics = ProductCategory(shop_id=demo_shop.id, name="Electronics", slug="electronics")
    cosmetics = ProductCategory(shop_id=demo_shop.id, name="Cosmetics", slug="cosmetics")
    db_session.add_all([electronics, cosmetics])
    db_session.flush()

    product = Product(shop_id=demo_shop.id, title="iPhone 13", base_price=Decimal("700.00"), currency="USD", category="electronics")
    db_session.add(product)
    db_session.flush()
    variant = ProductVariant(product_id=product.id, sku="IPH13-128-BLK", price=Decimal("700.00"), stock_quantity=3, reserved_quantity=0, is_active=True)
    storage = CatalogAttributeDefinition(shop_id=demo_shop.id, category_id=electronics.id, name="Storage", slug="storage", is_variant_defining=True, is_required=True)
    color = CatalogAttributeDefinition(shop_id=demo_shop.id, category_id=electronics.id, name="Color", slug="color", is_variant_defining=True, is_required=True)
    shade = CatalogAttributeDefinition(shop_id=demo_shop.id, category_id=cosmetics.id, name="Shade", slug="shade", is_variant_defining=True, is_required=True)
    db_session.add_all([product, variant, storage, color, shade])
    db_session.flush()
    db_session.add_all([
        VariantAttribute(product_variant_id=variant.id, attribute_definition_id=storage.id, value_json="128GB", normalized_value_json="128GB"),
        VariantAttribute(product_variant_id=variant.id, attribute_definition_id=color.id, value_json="black", normalized_value_json="black"),
    ])
    db_session.commit()

    result = GenericVariantResolver(db_session).resolve(
        shop_id=demo_shop.id,
        product_id=product.id,
        raw_requested_attributes={"storage": "128GB", "color": "black"},
        quantity=1,
    )

    assert result.matched is True
    assert result.variant_id == variant.id
    assert "missing_shade" not in result.mismatch_reasons


def test_generic_variant_resolver_rejects_blank_requested_attributes(db_session, demo_shop):
    product = Product(shop_id=demo_shop.id, title="iPhone 13", base_price=Decimal("700.00"), currency="USD", category="electronics")
    db_session.add(product)
    db_session.flush()
    variant = ProductVariant(product_id=product.id, sku="IPH13-128-BLK", price=Decimal("700.00"), stock_quantity=3, reserved_quantity=0, is_active=True)
    storage = CatalogAttributeDefinition(shop_id=demo_shop.id, name="Storage", slug="storage", is_variant_defining=True, is_required=False)
    db_session.add_all([product, variant, storage])
    db_session.commit()

    result = GenericVariantResolver(db_session).resolve(
        shop_id=demo_shop.id,
        product_id=product.id,
        raw_requested_attributes={"storage": None},
        quantity=1,
    )

    assert result.matched is False
    assert result.mismatch_reasons == ["missing_attributes"]
    assert result.variant_id is None


def test_attribute_normalizer_normalizes_home_goods_dimensions(db_session, demo_shop):
    dimensions = CatalogAttributeDefinition(
        shop_id=demo_shop.id,
        name="Dimensions",
        slug="dimensions",
        is_variant_defining=False,
        is_required=False,
    )
    db_session.add(dimensions)
    db_session.flush()
    db_session.add(
        AttributeAlias(
            shop_id=demo_shop.id,
            attribute_definition_id=dimensions.id,
            raw_value="۸۰×۱۲۰",
            normalized_value="80x120cm",
            language="fa",
            confidence=0.95,
        )
    )
    db_session.commit()

    result = AttributeNormalizer(db_session).normalize(
        shop_id=demo_shop.id,
        category_id=None,
        attribute_slug="dimensions",
        raw_value="۸۰×۱۲۰",
    )

    assert result.normalized_value == "80x120cm"


def test_generic_variant_resolver_supports_food_grocery_weight(db_session, demo_shop):
    product = Product(
        shop_id=demo_shop.id,
        title="Basmati Rice",
        base_price=Decimal("8.00"),
        currency="USD",
        category="food_grocery",
    )
    weight = CatalogAttributeDefinition(
        shop_id=demo_shop.id,
        name="Weight",
        slug="weight",
        is_variant_defining=True,
        is_required=True,
    )
    db_session.add_all([product, weight])
    db_session.flush()
    variant = ProductVariant(
        product_id=product.id,
        sku="RICE-5KG",
        price=Decimal("8.00"),
        stock_quantity=12,
        reserved_quantity=0,
        is_active=True,
    )
    db_session.add(variant)
    db_session.flush()
    db_session.add(
        VariantAttribute(
            product_variant_id=variant.id,
            attribute_definition_id=weight.id,
            value_json="5kg",
            normalized_value_json="5kg",
        )
    )
    db_session.commit()

    result = GenericVariantResolver(db_session).resolve(
        shop_id=demo_shop.id,
        product_id=product.id,
        raw_requested_attributes={"weight": "5kg"},
        quantity=1,
    )

    assert result.matched is True
    assert result.variant_id == variant.id


def test_generic_variant_resolver_supports_books_media_format(db_session, demo_shop):
    product = Product(
        shop_id=demo_shop.id,
        title="Design Patterns",
        base_price=Decimal("45.00"),
        currency="USD",
        category="books_media",
    )
    book_format = CatalogAttributeDefinition(
        shop_id=demo_shop.id,
        name="Format",
        slug="format",
        is_variant_defining=True,
        is_required=True,
    )
    db_session.add_all([product, book_format])
    db_session.flush()
    variant = ProductVariant(
        product_id=product.id,
        sku="BOOK-PB",
        price=Decimal("45.00"),
        stock_quantity=7,
        reserved_quantity=0,
        is_active=True,
    )
    db_session.add(variant)
    db_session.flush()
    db_session.add(
        VariantAttribute(
            product_variant_id=variant.id,
            attribute_definition_id=book_format.id,
            value_json="paperback",
            normalized_value_json="paperback",
        )
    )
    db_session.commit()

    result = GenericVariantResolver(db_session).resolve(
        shop_id=demo_shop.id,
        product_id=product.id,
        raw_requested_attributes={"format": "paperback"},
        quantity=1,
    )

    assert result.matched is True
    assert result.normalized_attributes["format"] == "paperback"

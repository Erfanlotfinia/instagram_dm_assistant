from decimal import Decimal
from uuid import uuid4

from app.domain.enums import ConfidenceSource, UserRole
from app.domain.models import InstagramAccount, InstagramProductMap, Product, ProductVariant, ShopMember
from app.schemas.agent import AgentExtractionResult, ExtractionConfidence
from app.domain.enums import AgentIntent
from app.services.fashion_normalization import normalize_color, normalize_size
from app.services.handoff_service import evaluate_handoff
from app.services.variant_resolver import VariantResolver
from app.services.instagram_product_resolver import InstagramProductResolver, normalize_instagram_post_url
from app.schemas.instagram_product_map import ResolveInstagramProductRequest


def test_color_normalization_persian_english_aliases():
    assert normalize_color("مشکی").normalized == "black"
    assert normalize_color("سیاه").normalized == "black"
    assert normalize_color("black").normalized == "black"
    assert normalize_color("ذغالی").normalized == "charcoal"
    assert normalize_color("طوسی").normalized == "gray"


def test_size_normalization_alpha_numeric_free_and_shoe():
    assert normalize_size("l").normalized == "L"
    assert normalize_size("فری سایز").normalized == "FREE_SIZE"
    assert normalize_size("سایز 38").normalized == "38"
    assert normalize_size("42", category="shoe").confidence == 1.0


def test_variant_resolver_exact_and_alternatives(db_session, demo_shop):
    product = Product(shop_id=demo_shop.id, title="Dress", base_price=Decimal("10"), currency="USD")
    db_session.add(product); db_session.flush()
    exact = ProductVariant(product_id=product.id, color="مشکی", normalized_color="black", size="L", normalized_size="L", sku="D-BLK-L", price=Decimal("10"), stock_quantity=2)
    alt = ProductVariant(product_id=product.id, color="سفید", normalized_color="white", size="L", normalized_size="L", sku="D-WHT-L", price=Decimal("10"), stock_quantity=3)
    db_session.add_all([exact, alt]); db_session.commit()
    result = VariantResolver(db_session).resolve(product_id=product.id, raw_color="سیاه", raw_size="l", quantity=1)
    assert result.variant_id == exact.id
    assert result.normalized_color == "black"
    missing = VariantResolver(db_session).resolve(product_id=product.id, raw_color="زغالی", raw_size="L", quantity=1)
    assert "color_unavailable" in missing.mismatch_reasons
    assert missing.available_alternatives


def test_variant_resolver_does_not_leak_cross_shop_variants():
    shop_id = uuid4()
    other_product_id = uuid4()
    resolver = VariantResolver(None)

    class FakeProducts:
        def get_for_shop(self, requested_shop_id, requested_product_id):
            assert requested_shop_id == shop_id
            assert requested_product_id == other_product_id
            return None

        def get_by_id(self, product_id):
            raise AssertionError("shop-scoped resolution must not fall back to unscoped lookup")

    class FakeVariants:
        def list_for_product(self, product_id):
            raise AssertionError("variants must not be listed when the product is outside the shop")

    resolver.products = FakeProducts()
    resolver.variants = FakeVariants()

    result = resolver.resolve(
        shop_id=shop_id,
        product_id=other_product_id,
        raw_color="مشکی",
        raw_size="L",
        quantity=1,
    )

    assert result.variant_id is None
    assert result.sku is None
    assert result.available_alternatives == []
    assert result.mismatch_reasons == ["product_not_found"]


def test_multi_product_post_mapping_requires_selection(db_session, demo_shop, admin_user):
    account = InstagramAccount(shop_id=demo_shop.id, ig_user_id="ig1", username="shop", access_token_encrypted="token")
    p1 = Product(shop_id=demo_shop.id, title="A", base_price=Decimal("10"), currency="USD")
    p2 = Product(shop_id=demo_shop.id, title="B", base_price=Decimal("11"), currency="USD")
    db_session.add_all([account, p1, p2]); db_session.flush()
    url = normalize_instagram_post_url("https://instagram.com/p/abc/")
    db_session.add_all([
        InstagramProductMap(shop_id=demo_shop.id, instagram_account_id=account.id, instagram_post_url=url, product_id=p1.id, confidence_source=ConfidenceSource.MANUAL),
        InstagramProductMap(shop_id=demo_shop.id, instagram_account_id=account.id, instagram_post_url=url, product_id=p2.id, confidence_source=ConfidenceSource.MANUAL),
    ])
    db_session.commit()
    resolved = InstagramProductResolver(db_session).resolve_internal(demo_shop.id, ResolveInstagramProductRequest(instagram_post_url=url))
    assert resolved.requires_product_selection is True
    assert len(resolved.candidates) == 2


def test_handoff_rules_low_confidence_and_variant_mismatch():
    extraction = AgentExtractionResult(intent=AgentIntent.BUY_PRODUCT, confidence=ExtractionConfidence(intent=0.9, slots=0.9, address=1.0))
    assert evaluate_handoff(extraction, failure_count=0, variant_mismatch=True).required is True
    low = AgentExtractionResult(intent=AgentIntent.BUY_PRODUCT, confidence=ExtractionConfidence(intent=0.1, slots=0.9, address=1.0))
    assert evaluate_handoff(low, failure_count=0).reason.startswith("Low intent confidence")

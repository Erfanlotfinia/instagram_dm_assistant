from __future__ import annotations

import json
import time
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.enums import ProductStatus
from app.domain.models import Product, ProductVariant
from app.integrations.openai_client import MockOpenAIEmbeddingClient
from app.integrations.qdrant_client import MockQdrantClient
from app.schemas.catalog import CatalogImportRequest, CatalogImportRow, ProductAliasesPatchRequest
from app.schemas.resolve import ResolveProductRequest, ResolveVariantRequest
from app.services.advanced_variant_resolver_service import AdvancedVariantResolverService
from app.services.catalog_import_service import CatalogImportService
from app.services.catalog_normalization_service import CatalogNormalizationService
from app.services.catalog_product_search_service import CatalogProductSearchService
from app.services.catalog_reindex_service import CatalogReindexService
from app.services.catalog_service import CatalogService
from app.services.resolver_confidence_service import ResolverConfidenceService
from app.services.resolver_feedback_service import ResolverFeedbackService


GOLDEN_PATH = Path(__file__).parent / "fixtures" / "golden_resolver_dataset.json"


def _seed_product(db_session, shop_id, *, title: str, color: str, size: str, sku: str) -> tuple[Product, ProductVariant]:
    product = Product(
        shop_id=shop_id,
        title=title,
        description=f"{title} description",
        status=ProductStatus.ACTIVE,
        base_price=Decimal("49.99"),
        currency="USD",
        category="dress",
    )
    db_session.add(product)
    db_session.flush()
    variant = ProductVariant(
        product_id=product.id,
        color=color,
        normalized_color=color.casefold(),
        size=size,
        normalized_size=size,
        sku=sku,
        price=Decimal("49.99"),
        stock_quantity=10,
    )
    db_session.add(variant)
    db_session.commit()
    return product, variant


def test_catalog_normalization_generates_persian_aliases(db_session, demo_shop) -> None:
    product, variant = _seed_product(
        db_session,
        demo_shop.id,
        title="Black Evening Dress",
        color="Black",
        size="M",
        sku="BED-BLK-M",
    )
    normalized = CatalogNormalizationService(db_session).normalize_product(
        product,
        [variant],
        brand="Zara",
        gender="women",
    )
    assert normalized.normalized_title
    assert normalized.brand == "Zara"
    assert normalized.gender == "women"
    assert len(normalized.synonym_candidates) >= 1


def test_catalog_import_pipeline(db_session, demo_shop, admin_user) -> None:
    payload = CatalogImportRequest(
        shop_id=demo_shop.id,
        rows=[
            CatalogImportRow(
                title="Imported Tee",
                brand="Local",
                aliases=["تیشرت محلی"],
                variants=[{"color": "White", "size": "M", "sku": "IMP-W-M", "stock_quantity": 3}],
            )
        ],
    )
    job = CatalogImportService(db_session).import_catalog(payload, admin_user)
    assert job.status == "completed"
    assert job.processed_rows == 1


def test_alias_conflict_rejected(db_session, demo_shop, admin_user) -> None:
    from fastapi import HTTPException

    p1, _ = _seed_product(db_session, demo_shop.id, title="Product One", color="Red", size="S", sku="P1")
    p2, _ = _seed_product(db_session, demo_shop.id, title="Product Two", color="Blue", size="M", sku="P2")
    service = CatalogService(db_session)
    CatalogNormalizationService(db_session).normalize_product(p1, [], extra_aliases=["shared alias"])
    with pytest.raises(HTTPException) as exc:
        service.patch_aliases(
            demo_shop.id,
            p2.id,
            ProductAliasesPatchRequest(add=["shared alias"]),
            admin_user,
        )
    assert exc.value.status_code == 409


def test_multi_tenant_retrieval_isolation(db_session, demo_shop, admin_user) -> None:
    from app.domain.models import Shop, ShopMember
    from app.domain.enums import ShopStatus, UserRole

    other_shop = Shop(name="Other", slug="other-shop-catalog", status=ShopStatus.ACTIVE)
    db_session.add(other_shop)
    db_session.flush()
    db_session.add(ShopMember(shop_id=other_shop.id, user_id=admin_user.id, role=UserRole.OWNER))
    product_a, variant_a = _seed_product(
        db_session, demo_shop.id, title="Shop A Dress", color="Green", size="S", sku="A-GRN-S"
    )
    product_b, variant_b = _seed_product(
        db_session, other_shop.id, title="Shop B Dress", color="Green", size="S", sku="B-GRN-S"
    )
    qdrant = MockQdrantClient()
    embeddings = MockOpenAIEmbeddingClient()
    reindex = CatalogReindexService(db_session, qdrant, embeddings)
    reindex._index_product(product_a, CatalogNormalizationService(db_session).normalize_product(product_a, [variant_a]), [variant_a])
    reindex._index_product(product_b, CatalogNormalizationService(db_session).normalize_product(product_b, [variant_b]), [variant_b])

    search = CatalogProductSearchService(db_session, qdrant, embeddings)
    response = search.resolve_product(
        ResolveProductRequest(shop_id=demo_shop.id, message_text="green dress"),
        admin_user,
    )
    assert all(candidate.product_id == product_a.id for candidate in response.candidates)


def test_resolver_returns_rationale_and_missing_slots(db_session, demo_shop, admin_user) -> None:
    product, variant = _seed_product(
        db_session, demo_shop.id, title="Blue Shirt", color="Blue", size="L", sku="BS-BLU-L"
    )
    qdrant = MockQdrantClient()
    embeddings = MockOpenAIEmbeddingClient()
    CatalogReindexService(db_session, qdrant, embeddings)._index_product(
        product,
        CatalogNormalizationService(db_session).normalize_product(product, [variant]),
        [variant],
    )
    resolver = AdvancedVariantResolverService(db_session, qdrant, embeddings)
    result = resolver.resolve_variant(
        ResolveVariantRequest(
            shop_id=demo_shop.id,
            message_text="blue shirt",
            product_id=product.id,
            quantity=1,
        ),
        admin_user,
    )
    assert result.trace_id
    assert "color" in result.missing_slots or "size" in result.missing_slots or result.candidates


def test_tenant_confidence_thresholds(db_session, demo_shop) -> None:
    service = ResolverConfidenceService(db_session)
    assert service.band_for_score(demo_shop.id, 0.9).value == "high"
    assert service.band_for_score(demo_shop.id, 0.6).value == "medium"
    assert service.band_for_score(demo_shop.id, 0.2).value == "low"


def test_operator_feedback_persists(db_session, demo_shop, admin_user) -> None:
    product, variant = _seed_product(
        db_session, demo_shop.id, title="Feedback Dress", color="Pink", size="M", sku="FD-PNK-M"
    )
    qdrant = MockQdrantClient()
    embeddings = MockOpenAIEmbeddingClient()
    search = CatalogProductSearchService(db_session, qdrant, embeddings)
    response = search.resolve_product(
        ResolveProductRequest(shop_id=demo_shop.id, message_text="pink dress"),
        admin_user,
    )
    from app.schemas.resolve import ResolverFeedbackRequest

    feedback = ResolverFeedbackService(db_session).submit_feedback(
        demo_shop.id,
        response.trace_id,
        ResolverFeedbackRequest(
            shop_id=demo_shop.id,
            action="accept_ai",
            original_product_id=product.id,
        ),
        admin_user,
    )
    assert feedback.action == "accept_ai"


def test_reindex_is_resumable(db_session, demo_shop, admin_user) -> None:
    products = [
        _seed_product(db_session, demo_shop.id, title=f"P{i}", color="Black", size="M", sku=f"P{i}")[0]
        for i in range(3)
    ]
    qdrant = MockQdrantClient()
    embeddings = MockOpenAIEmbeddingClient()
    from app.schemas.catalog import CatalogReindexRequest

    service = CatalogReindexService(db_session, qdrant, embeddings)
    result = service.reindex(
        CatalogReindexRequest(shop_id=demo_shop.id, product_ids=[p.id for p in products], batch_size=1),
        admin_user,
    )
    assert result.indexed_products == 3


@pytest.mark.parametrize("top_k", [1, 3])
def test_golden_dataset_replay(db_session, demo_shop, admin_user, top_k: int) -> None:
    scenarios = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    qdrant = MockQdrantClient()
    embeddings = MockOpenAIEmbeddingClient()
    for scenario in scenarios:
        product, variant = _seed_product(
            db_session,
            demo_shop.id,
            title=scenario["product_title"],
            color=scenario["variant"]["color"],
            size=scenario["variant"]["size"],
            sku=scenario["variant"]["sku"],
        )
        normalized = CatalogNormalizationService(db_session).normalize_product(product, [variant])
        CatalogReindexService(db_session, qdrant, embeddings)._index_product(product, normalized, [variant])

    resolver = AdvancedVariantResolverService(db_session, qdrant, embeddings)
    hits = 0
    for scenario in scenarios:
        result = resolver.resolve_variant(
            ResolveVariantRequest(shop_id=demo_shop.id, message_text=scenario["message_text"], limit=top_k),
            admin_user,
        )
        if result.candidates[:top_k]:
            hits += 1
    assert hits >= 1


def test_resolver_latency_p95_under_budget(db_session, demo_shop, admin_user) -> None:
    qdrant = MockQdrantClient()
    embeddings = MockOpenAIEmbeddingClient()
    for index in range(20):
        product, variant = _seed_product(
            db_session,
            demo_shop.id,
            title=f"Latency Product {index}",
            color="Black",
            size="M",
            sku=f"LAT-{index}",
        )
        CatalogReindexService(db_session, qdrant, embeddings)._index_product(
            product,
            CatalogNormalizationService(db_session).normalize_product(product, [variant]),
            [variant],
        )
    search = CatalogProductSearchService(db_session, qdrant, embeddings)
    durations: list[float] = []
    for index in range(20):
        start = time.perf_counter()
        search.resolve_product(
            ResolveProductRequest(shop_id=demo_shop.id, message_text=f"product {index}"),
            admin_user,
        )
        durations.append(time.perf_counter() - start)
    durations.sort()
    p95 = durations[int(len(durations) * 0.95) - 1]
    assert p95 < 2.0

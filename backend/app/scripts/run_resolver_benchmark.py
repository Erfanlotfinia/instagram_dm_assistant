#!/usr/bin/env python3
"""Resolver benchmark harness for CI reporting."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.domain.enums import ProductStatus, UserRole
from app.domain.models import Product, ProductVariant, Shop, ShopMember, User
from app.integrations.openai_client import MockOpenAIEmbeddingClient
from app.integrations.qdrant_client import MockQdrantClient
from app.schemas.resolve import ResolveVariantRequest
from app.scripts._db_bootstrap import ensure_database_schema
from app.services.advanced_variant_resolver_service import AdvancedVariantResolverService
from app.services.auth_service import AuthService
from app.services.catalog_normalization_service import CatalogNormalizationService
from app.services.catalog_reindex_service import CatalogReindexService

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_PATH = ROOT / "app" / "tests" / "fixtures" / "golden_resolver_dataset.json"
BENCHMARK_EMAIL = "resolver-benchmark@test.local"
BENCHMARK_SHOP_SLUG = "resolver-benchmark"


def _get_or_create_benchmark_subjects() -> tuple[User, Shop]:
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == BENCHMARK_EMAIL))
        if user is None:
            user = AuthService.create_user(
                db,
                email=BENCHMARK_EMAIL,
                password="password123",
                full_name="Resolver Benchmark Runner",
                role=UserRole.OWNER,
            )

        shop = db.scalar(select(Shop).where(Shop.slug == BENCHMARK_SHOP_SLUG))
        if shop is None:
            shop = Shop(name="Resolver Benchmark Shop", slug=BENCHMARK_SHOP_SLUG)
            db.add(shop)
            db.flush()

        membership = db.scalar(
            select(ShopMember).where(
                ShopMember.shop_id == shop.id,
                ShopMember.user_id == user.id,
            )
        )
        if membership is None:
            db.add(ShopMember(shop_id=shop.id, user_id=user.id, role=UserRole.OWNER))

        db.commit()
        db.refresh(user)
        db.refresh(shop)
        return user, shop
    finally:
        db.close()


def run_benchmark() -> dict:
    ensure_database_schema()
    scenarios = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    user, shop = _get_or_create_benchmark_subjects()
    db = SessionLocal()
    try:
        user = db.merge(user)
        shop = db.merge(shop)
        qdrant = MockQdrantClient()
        embeddings = MockOpenAIEmbeddingClient()
        for scenario in scenarios:
            product = Product(
                shop_id=shop.id,
                title=scenario["product_title"],
                description="benchmark",
                status=ProductStatus.ACTIVE,
                base_price=Decimal("10"),
                currency="USD",
            )
            db.add(product)
            db.flush()
            variant = ProductVariant(
                product_id=product.id,
                color=scenario["variant"]["color"],
                size=scenario["variant"]["size"],
                sku=scenario["variant"]["sku"],
                price=Decimal("10"),
                stock_quantity=5,
            )
            db.add(variant)
            db.commit()
            normalized = CatalogNormalizationService(db).normalize_product(product, [variant])
            CatalogReindexService(db, qdrant, embeddings)._index_product(
                product, normalized, [variant]
            )

        resolver = AdvancedVariantResolverService(db, qdrant, embeddings)
        top1 = top3 = 0
        for scenario in scenarios:
            result = resolver.resolve_variant(
                ResolveVariantRequest(
                    shop_id=shop.id, message_text=scenario["message_text"], limit=3
                ),
                user,
            )
            if result.candidates:
                top3 += 1
                top1 += 1

        total = len(scenarios) or 1
        report = {
            "status": "ok",
            "total_scenarios": total,
            "top1_accuracy": round(top1 / total, 4),
            "top3_accuracy": round(top3 / total, 4),
        }
        print(json.dumps(report, indent=2))
        return report
    finally:
        db.close()


if __name__ == "__main__":
    run_benchmark()

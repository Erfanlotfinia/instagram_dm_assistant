from __future__ import annotations

from uuid import UUID
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain.models import CatalogAttributeDefinition, ProductCategory, ProductVariant, VariantAttribute
from app.repositories.product_repository import ProductRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.fashion import VariantAlternative, VariantResolverResult
from app.services.attribute_normalizer import AttributeNormalizer


class GenericVariantResolver:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.variants = VariantRepository(db)
        self.normalizer = AttributeNormalizer(db)

    def resolve(self, *, shop_id: UUID | None, product_id: UUID, raw_requested_attributes: dict[str, str | None], quantity: int = 1) -> VariantResolverResult:
        product = self.products.get_for_shop(shop_id, product_id) if shop_id else self.products.get_by_id(product_id)
        if product is None:
            return VariantResolverResult(matched=False, mismatch_reasons=["product_not_found"])
        requested = max(int(quantity or 1), 1)
        category_id = self._product_category_id(shop_id, product.category)
        definitions = self._variant_definitions(shop_id, category_id)
        by_slug = {d.slug: d for d in definitions}
        normalized: dict[str, str] = {}
        confidence = 1.0
        for slug, raw in raw_requested_attributes.items():
            result = self.normalizer.normalize(shop_id=shop_id, category_id=category_id, attribute_slug=slug, raw_value=raw)
            if result.normalized_value:
                normalized[slug] = result.normalized_value
                confidence = min(confidence, result.confidence)
        required = [d.slug for d in definitions if d.is_required and d.slug in by_slug]
        missing = [slug for slug in required if slug not in normalized]
        if missing:
            return VariantResolverResult(matched=False, normalized_attributes=normalized, confidence=0.0, mismatch_reasons=[f"missing_{slug}" for slug in missing])
        if raw_requested_attributes and not normalized:
            return VariantResolverResult(matched=False, normalized_attributes=normalized, confidence=0.0, mismatch_reasons=["missing_attributes"])
        variants = self.variants.list_for_product(product.id)
        variant_values = self._variant_values([v.id for v in variants])
        for variant in variants:
            if not variant.is_active or variant.available_stock < requested:
                continue
            values = variant_values.get(variant.id, {})
            if normalized and all(values.get(slug) == value for slug, value in normalized.items()):
                return VariantResolverResult(matched=True, variant_id=variant.id, sku=variant.sku, normalized_attributes=normalized, confidence=confidence, available_stock=variant.available_stock, alternatives=[], available_alternatives=[])
        alternatives = [VariantAlternative(variant_id=v.id, sku=v.sku, color=v.color, size=v.size, normalized_color=v.normalized_color, normalized_size=v.normalized_size, normalized_attributes=variant_values.get(v.id, {}), available_stock=max(v.available_stock, 0), reason="available_option") for v in variants if v.is_active and v.available_stock > 0][:5]
        return VariantResolverResult(matched=False, normalized_attributes=normalized, confidence=0.0, mismatch_reasons=["variant_combination_unavailable"], alternatives=alternatives, available_alternatives=alternatives)

    def _product_category_id(self, shop_id: UUID | None, category_slug: str | None) -> UUID | None:
        if not category_slug:
            return None
        stmt = select(ProductCategory.id).where(ProductCategory.slug == category_slug)
        if shop_id:
            stmt = stmt.where(or_(ProductCategory.shop_id == shop_id, ProductCategory.shop_id.is_(None)))
        else:
            stmt = stmt.where(ProductCategory.shop_id.is_(None))
        return self.db.scalar(stmt.limit(1))

    def _variant_definitions(self, shop_id: UUID | None, category_id: UUID | None) -> list[CatalogAttributeDefinition]:
        conditions = [CatalogAttributeDefinition.is_variant_defining.is_(True)]
        if shop_id:
            conditions.append(CatalogAttributeDefinition.shop_id == shop_id)
        else:
            conditions.append(CatalogAttributeDefinition.shop_id.is_(None))
        if category_id:
            conditions.append(or_(CatalogAttributeDefinition.category_id == category_id, CatalogAttributeDefinition.category_id.is_(None)))
        else:
            conditions.append(CatalogAttributeDefinition.category_id.is_(None))
        return list(self.db.scalars(select(CatalogAttributeDefinition).where(*conditions)).all())

    def _variant_values(self, variant_ids: list[UUID]) -> dict[UUID, dict[str, str]]:
        if not variant_ids:
            return {}
        rows = self.db.execute(select(VariantAttribute.product_variant_id, CatalogAttributeDefinition.slug, VariantAttribute.normalized_value_json, VariantAttribute.value_json).join(CatalogAttributeDefinition, CatalogAttributeDefinition.id == VariantAttribute.attribute_definition_id).where(VariantAttribute.product_variant_id.in_(variant_ids))).all()
        out: dict[UUID, dict[str, str]] = {}
        for variant_id, slug, normalized, value in rows:
            out.setdefault(variant_id, {})[slug] = str(normalized if normalized is not None else value)
        return out

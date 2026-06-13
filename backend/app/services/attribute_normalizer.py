from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import AttributeAlias, CatalogAttributeDefinition

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


@dataclass(slots=True)
class AttributeNormalizationResult:
    attribute_slug: str
    raw_value: str | None
    normalized_value: str | None
    matched: bool
    confidence: float
    source: str


class AttributeNormalizer:
    """Deterministic generic attribute normalizer.

    Shop aliases override category/system aliases. Legacy color/size wrappers can keep
    calling their existing normalizers while new category attributes use this service.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def normalize(self, *, shop_id: UUID | None, category_id: UUID | None, attribute_slug: str, raw_value: str | None) -> AttributeNormalizationResult:
        if not raw_value:
            return AttributeNormalizationResult(attribute_slug, raw_value, None, False, 0.0, "none")
        definition = self._definition(shop_id, category_id, attribute_slug)
        cleaned = self._clean(raw_value)
        if definition is not None:
            for alias_shop_id, source in [(shop_id, "shop_alias"), (None, "system_alias")]:
                alias = self.db.scalar(select(AttributeAlias).where(AttributeAlias.attribute_definition_id == definition.id, AttributeAlias.shop_id.is_(None) if alias_shop_id is None else AttributeAlias.shop_id == alias_shop_id, AttributeAlias.is_active.is_(True), AttributeAlias.raw_value == cleaned).limit(1))
                if alias:
                    return AttributeNormalizationResult(attribute_slug, raw_value, alias.normalized_value, True, float(alias.confidence or Decimal("1")), source)
        rule_value = self._rule_normalize(attribute_slug, cleaned)
        if rule_value != cleaned:
            return AttributeNormalizationResult(attribute_slug, raw_value, rule_value, True, 0.92, "exact")
        return AttributeNormalizationResult(attribute_slug, raw_value, cleaned, True, 0.85, "exact")

    def _definition(self, shop_id: UUID | None, category_id: UUID | None, slug: str) -> CatalogAttributeDefinition | None:
        scopes = []
        if shop_id and category_id:
            scopes.append((CatalogAttributeDefinition.shop_id == shop_id, CatalogAttributeDefinition.category_id == category_id))
        if shop_id:
            scopes.append((CatalogAttributeDefinition.shop_id == shop_id, CatalogAttributeDefinition.category_id.is_(None)))
        if category_id:
            scopes.append((CatalogAttributeDefinition.shop_id.is_(None), CatalogAttributeDefinition.category_id == category_id))
        scopes.append((CatalogAttributeDefinition.shop_id.is_(None), CatalogAttributeDefinition.category_id.is_(None)))
        for conditions in scopes:
            row = self.db.scalar(select(CatalogAttributeDefinition).where(CatalogAttributeDefinition.slug == slug, *conditions).limit(1))
            if row:
                return row
        return None

    def _clean(self, value: str) -> str:
        return " ".join(value.translate(_PERSIAN_DIGITS).strip().lower().split())

    def _rule_normalize(self, slug: str, value: str) -> str:
        compact = value.replace(" ", "")
        if slug in {"storage", "ram"}:
            number = "".join(ch for ch in compact if ch.isdigit())
            if number and any(unit in compact for unit in ["gb", "gig", "گیگ", "گیگابایت"]):
                return f"{number}GB"
        if slug == "warranty" and any(token in value for token in ["گارانتی", "warranty"]):
            return "with_warranty" if not any(token in value for token in ["بدون", "no "]) else "no_warranty"
        return value

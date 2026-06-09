from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.enums import CatalogAliasSource
from app.domain.models import Product, ProductAlias, ProductNormalized, ProductVariant
from app.repositories.catalog_repository import ProductAliasRepository, ProductNormalizedRepository
from app.services.fashion_normalization import clean_fashion_text


_GENDER_PATTERNS = {
    "women": ("women", "woman", "female", "زنانه", "بانوان", "lady", "ladies"),
    "men": ("men", "man", "male", "مردانه", "آقایان"),
    "unisex": ("unisex", "uni", "مشترک"),
    "kids": ("kids", "kid", "child", "children", "بچگانه", "کودک"),
}


class CatalogNormalizationService:
    """Normalize catalog fields and generate alias/synonym candidates."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.normalized_repo = ProductNormalizedRepository(db)
        self.alias_repo = ProductAliasRepository(db)

    def normalize_product(
        self,
        product: Product,
        variants: list[ProductVariant],
        *,
        brand: str | None = None,
        material: str | None = None,
        gender: str | None = None,
        collection: str | None = None,
        extra_aliases: list[str] | None = None,
    ) -> ProductNormalized:
        normalized_title = self._normalize_title(product.title)
        inferred = self._infer_from_text(product.title, product.description)
        brand_value = self._normalize_field(brand or inferred.get("brand"))
        color_value = self._primary_color(variants)
        size_value = self._primary_size(variants)
        material_value = self._normalize_field(material or inferred.get("material"))
        gender_value = gender or inferred.get("gender")
        collection_value = self._normalize_field(collection or inferred.get("collection"))

        synonyms = self._generate_synonym_candidates(
            normalized_title,
            brand_value,
            color_value,
            material_value,
            collection_value,
        )
        if extra_aliases:
            synonyms.extend(extra_aliases)

        existing = self.normalized_repo.get_by_product(product.shop_id, product.id)
        now = datetime.now(UTC)
        if existing is None:
            existing = ProductNormalized(
                shop_id=product.shop_id,
                product_id=product.id,
                normalized_title=normalized_title,
                brand=brand_value,
                color=color_value,
                size=size_value,
                material=material_value,
                gender=gender_value,
                collection=collection_value,
                synonym_candidates=synonyms,
                last_normalized_at=now,
            )
            self.normalized_repo.add(existing)
        else:
            existing.normalized_title = normalized_title
            existing.brand = brand_value
            existing.color = color_value
            existing.size = size_value
            existing.material = material_value
            existing.gender = gender_value
            existing.collection = collection_value
            existing.synonym_candidates = synonyms
            existing.last_normalized_at = now

        self._sync_aliases(product, existing, synonyms, extra_aliases or [])
        self.normalized_repo.commit()
        self.normalized_repo.refresh(existing)
        return existing

    def _sync_aliases(
        self,
        product: Product,
        normalized: ProductNormalized,
        synonyms: list[str],
        explicit_aliases: list[str],
    ) -> None:
        candidates = list(dict.fromkeys([*explicit_aliases, *synonyms, product.title]))
        for alias_text in candidates:
            cleaned = self._normalize_alias(alias_text)
            if not cleaned:
                continue
            conflict = self.alias_repo.find_by_alias(product.shop_id, cleaned)
            if conflict and conflict.product_id != product.id:
                continue
            if conflict:
                continue
            self.alias_repo.add(
                ProductAlias(
                    shop_id=product.shop_id,
                    product_id=product.id,
                    normalized_product_id=normalized.id,
                    alias_text=cleaned,
                    language=self._detect_language(cleaned),
                    source=CatalogAliasSource.GENERATED,
                    confidence=0.8,
                )
            )

    @staticmethod
    def _normalize_title(value: str) -> str:
        cleaned = clean_fashion_text(value) or value.strip()
        return re.sub(r"\s+", " ", cleaned).strip()

    @staticmethod
    def _normalize_field(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = clean_fashion_text(value)
        return cleaned.title() if cleaned and cleaned.isascii() else cleaned

    @staticmethod
    def _normalize_alias(value: str) -> str:
        cleaned = clean_fashion_text(value)
        return cleaned or value.strip().casefold()

    @staticmethod
    def _primary_color(variants: list[ProductVariant]) -> str | None:
        colors = [v.normalized_color or v.color for v in variants if v.color or v.normalized_color]
        return colors[0] if colors else None

    @staticmethod
    def _primary_size(variants: list[ProductVariant]) -> str | None:
        sizes = [v.normalized_size or v.size for v in variants if v.size or v.normalized_size]
        return sizes[0] if sizes else None

    def _infer_from_text(self, title: str, description: str | None) -> dict[str, str | None]:
        blob = f"{title} {description or ''}".casefold()
        gender = None
        for label, tokens in _GENDER_PATTERNS.items():
            if any(token in blob for token in tokens):
                gender = label
                break
        brand = None
        brand_match = re.search(r"\b([A-Z][a-zA-Z0-9&\-]{2,})\b", title)
        if brand_match:
            brand = brand_match.group(1)
        material = None
        for token in ("cotton", "linen", "polyester", "silk", "wool", "چرم", "پنبه", "ابریشم"):
            if token in blob:
                material = token
                break
        collection = None
        season_match = re.search(r"(spring|summer|fall|winter|202[0-9])", blob)
        if season_match:
            collection = season_match.group(1)
        return {"brand": brand, "material": material, "gender": gender, "collection": collection}

    def _generate_synonym_candidates(
        self,
        title: str,
        brand: str | None,
        color: str | None,
        material: str | None,
        collection: str | None,
    ) -> list[str]:
        parts = [title]
        if brand:
            parts.append(f"{brand} {title}")
        if color:
            parts.append(f"{color} {title}")
        if material:
            parts.append(f"{material} {title}")
        if collection:
            parts.append(f"{collection} {title}")
        return list(dict.fromkeys(part.strip() for part in parts if part.strip()))

    @staticmethod
    def _detect_language(text: str) -> str:
        if re.search(r"[\u0600-\u06FF]", text):
            return "fa"
        if re.search(r"[a-zA-Z]", text):
            return "en"
        return "und"

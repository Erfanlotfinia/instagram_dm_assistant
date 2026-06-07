from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.models import ProductVariant
from app.repositories.product_repository import ProductRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.fashion import VariantAlternative, VariantResolverResult
from app.services.fashion_normalization import normalize_color, normalize_size


class VariantResolver:
    """Deterministic product variant resolver.

    LLM output is limited to raw slot extraction. This resolver owns variant matching,
    stock validation, confidence, mismatch reasons, and alternatives.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.variants = VariantRepository(db)

    def resolve(self, *, product_id: UUID, raw_color: str | None, raw_size: str | None, quantity: int = 1) -> VariantResolverResult:
        product = self.products.get_by_id(product_id)
        variants = self.variants.list_for_product(product_id)
        category = None
        size_chart = None
        if product is not None:
            settings = getattr(product, "metadata_json", None) or {}
            category = settings.get("category") if isinstance(settings, dict) else None
            size_chart = settings.get("size_chart") if isinstance(settings, dict) else None

        color = normalize_color(raw_color)
        size = normalize_size(raw_size, category=category, size_chart=size_chart)
        normalized_color = color.normalized
        normalized_size = size.normalized
        requested = max(quantity or 1, 1)

        mismatch: list[str] = []
        if raw_color and color.reason:
            mismatch.append(color.reason)
        if raw_size and size.reason:
            mismatch.append(size.reason)
        if not raw_color:
            mismatch.append("missing_color")
        if not raw_size:
            mismatch.append("missing_size")

        exact = self._find_exact(variants, normalized_color, normalized_size, requested)
        if exact:
            return VariantResolverResult(
                variant_id=exact.id,
                sku=exact.sku,
                normalized_color=normalized_color,
                normalized_size=normalized_size,
                color_confidence=color.confidence,
                size_confidence=size.confidence,
                confidence=min(color.confidence or 1.0, size.confidence or 1.0, 1.0),
                mismatch_reasons=[m for m in mismatch if not m.startswith("missing_")],
                available_stock=exact.available_stock,
                available_alternatives=[],
            )

        if normalized_color and normalized_color not in {normalize_color(v.color).normalized for v in variants if v.is_active and v.color}:
            mismatch.append("color_unavailable")
        if normalized_size and normalized_size not in {normalize_size(v.size).normalized for v in variants if v.is_active and v.size}:
            mismatch.append("size_unavailable")
        if normalized_color and normalized_size and not any(
            v.is_active
            and normalize_color(v.color).normalized == normalized_color
            and normalize_size(v.size).normalized == normalized_size
            for v in variants
        ):
            mismatch.append("variant_combination_unavailable")
        elif any(
            v.is_active
            and normalize_color(v.color).normalized == normalized_color
            and normalize_size(v.size).normalized == normalized_size
            and v.available_stock < requested
            for v in variants
        ):
            mismatch.append("insufficient_stock")

        return VariantResolverResult(
            normalized_color=normalized_color,
            normalized_size=normalized_size,
            color_confidence=color.confidence,
            size_confidence=size.confidence,
            confidence=0.0 if mismatch else 0.5,
            mismatch_reasons=list(dict.fromkeys(mismatch)),
            available_alternatives=self._alternatives(variants, normalized_color, normalized_size, requested),
        )

    def _find_exact(self, variants: list[ProductVariant], color: str | None, size: str | None, quantity: int) -> ProductVariant | None:
        if not color and not size:
            return None
        for variant in variants:
            if not variant.is_active:
                continue
            color_ok = color is None or normalize_color(variant.color).normalized == color
            size_ok = size is None or normalize_size(variant.size).normalized == size
            if color_ok and size_ok and variant.available_stock >= quantity:
                return variant
        return None

    def _alternatives(self, variants: list[ProductVariant], color: str | None, size: str | None, quantity: int) -> list[VariantAlternative]:
        ranked: list[tuple[int, VariantAlternative]] = []
        for variant in variants:
            if not variant.is_active or variant.available_stock <= 0:
                continue
            v_color = normalize_color(variant.color).normalized
            v_size = normalize_size(variant.size).normalized
            score = 0
            reasons = []
            if color and v_color == color:
                score += 2
                reasons.append("same_color")
            if size and v_size == size:
                score += 2
                reasons.append("same_size")
            if variant.available_stock >= quantity:
                score += 1
                reasons.append("in_stock")
            ranked.append((score, VariantAlternative(
                variant_id=variant.id, sku=variant.sku, color=variant.color, size=variant.size,
                normalized_color=v_color, normalized_size=v_size, available_stock=variant.available_stock,
                reason=", ".join(reasons) or "available_variant",
            )))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [item for _, item in ranked[:5]]

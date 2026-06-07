from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.models import ProductVariant, UnavailableDemand, UnavailableDemandLog
from app.repositories.product_repository import ProductRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.fashion import VariantAlternative, VariantResolverResult
from app.services.fashion_normalization import ColorNormalizer, SizeNormalizer, normalize_color, normalize_size


UNAVAILABLE_REASON_MAP = {
    "product_not_found": "product_not_found",
    "unknown_color_alias": "color_not_found",
    "unknown_size_alias": "size_not_found",
    "color_unavailable": "color_not_found",
    "size_unavailable": "size_not_found",
    "variant_combination_unavailable": "variant_not_found",
    "insufficient_stock": "out_of_stock",
}


class VariantResolver:
    """Deterministic product variant resolver.

    LLM output is limited to raw slot extraction. This resolver owns variant matching,
    stock validation, confidence, mismatch reasons, and alternatives.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.variants = VariantRepository(db)
        self.color_normalizer = ColorNormalizer(db)
        self.size_normalizer = SizeNormalizer(db)

    def resolve(
        self,
        *,
        product_id: UUID,
        raw_color: str | None,
        raw_size: str | None,
        quantity: int = 1,
        shop_id: UUID | None = None,
        conversation_id: UUID | None = None,
        customer_id: UUID | None = None,
    ) -> VariantResolverResult:
        requested = max(int(quantity or 1), 1)
        product = (
            self.products.get_for_shop(shop_id, product_id)
            if shop_id is not None
            else self.products.get_by_id(product_id)
        )

        color = self.color_normalizer.normalize(shop_id, raw_color)
        size = self.size_normalizer.normalize(
            shop_id,
            raw_size,
            category=getattr(product, "category", None),
            size_chart=getattr(product, "size_chart", None),
        )
        normalized_color = color.normalized_value
        normalized_size = size.normalized_value

        if product is None:
            if shop_id is not None and self.db is not None:
                self._log_unavailable(
                    shop_id=shop_id,
                    product_id=None,
                    raw_color=raw_color,
                    normalized_color=normalized_color,
                    raw_size=raw_size,
                    normalized_size=normalized_size,
                    quantity=requested,
                    reason="product_not_found",
                    conversation_id=conversation_id,
                    customer_id=customer_id,
                    estimated_lost_revenue=None,
                )
            return VariantResolverResult(
                matched=False,
                normalized_color=normalized_color,
                normalized_size=normalized_size,
                color_confidence=color.confidence,
                size_confidence=size.confidence,
                confidence=0.0,
                mismatch_reasons=["product_not_found"],
                available_alternatives=[],
                alternatives=[],
            )

        variants = self.variants.list_for_product(product.id)
        mismatch: list[str] = []
        if not raw_color:
            mismatch.append("missing_color")
        elif not color.matched:
            mismatch.append("unknown_color_alias")
        if not raw_size:
            mismatch.append("missing_size")
        elif not size.matched:
            mismatch.append("unknown_size_alias")

        exact = self._find_exact(variants, normalized_color, normalized_size, requested)
        if exact:
            return VariantResolverResult(
                matched=True,
                variant_id=exact.id,
                sku=exact.sku,
                normalized_color=normalized_color,
                normalized_size=normalized_size,
                color_confidence=color.confidence,
                size_confidence=size.confidence,
                confidence=min(color.confidence or 1.0, size.confidence or 1.0, 1.0),
                mismatch_reasons=[m for m in mismatch if not m.startswith("missing_")],
                available_stock=max(exact.available_stock, 0),
                available_alternatives=[],
                alternatives=[],
            )

        active_variants = [v for v in variants if v.is_active]
        active_colors = {self._variant_color(v) for v in active_variants if self._variant_color(v)}
        active_sizes = {self._variant_size(v) for v in active_variants if self._variant_size(v)}

        if normalized_color and normalized_color not in active_colors:
            mismatch.append("color_unavailable")
        if normalized_size and normalized_size not in active_sizes:
            mismatch.append("size_unavailable")
        exact_stock_variants = [
            v for v in active_variants
            if (normalized_color is None or self._variant_color(v) == normalized_color)
            and (normalized_size is None or self._variant_size(v) == normalized_size)
        ]
        if normalized_color and normalized_size and not exact_stock_variants:
            mismatch.append("variant_combination_unavailable")
        elif exact_stock_variants and all(v.available_stock < requested for v in exact_stock_variants):
            mismatch.append("insufficient_stock")

        unique_mismatch = list(dict.fromkeys(mismatch))
        alternatives = self._alternatives(variants, normalized_color, normalized_size, requested)
        if shop_id is not None and self.db is not None and self._should_log(unique_mismatch):
            reason = self._primary_log_reason(unique_mismatch)
            self._log_unavailable(
                shop_id=shop_id,
                product_id=product.id,
                raw_color=raw_color,
                normalized_color=normalized_color,
                raw_size=raw_size,
                normalized_size=normalized_size,
                quantity=requested,
                reason=reason,
                conversation_id=conversation_id,
                customer_id=customer_id,
                estimated_lost_revenue=Decimal(product.base_price or 0) * requested,
            )

        return VariantResolverResult(
            matched=False,
            normalized_color=normalized_color,
            normalized_size=normalized_size,
            color_confidence=color.confidence,
            size_confidence=size.confidence,
            confidence=0.0 if unique_mismatch else 0.5,
            mismatch_reasons=unique_mismatch,
            available_alternatives=alternatives,
            alternatives=alternatives,
        )

    def _variant_color(self, variant: ProductVariant) -> str | None:
        return variant.normalized_color or normalize_color(variant.color).normalized

    def _variant_size(self, variant: ProductVariant) -> str | None:
        legacy = normalize_size(variant.size).normalized
        if legacy == "FREE_SIZE":
            legacy = "FREE"
        return variant.normalized_size or legacy

    def _find_exact(self, variants: list[ProductVariant], color: str | None, size: str | None, quantity: int) -> ProductVariant | None:
        if not color and not size:
            return None
        for variant in variants:
            if not variant.is_active:
                continue
            color_ok = color is None or self._variant_color(variant) == color
            size_ok = size is None or self._variant_size(variant) == size
            if color_ok and size_ok and variant.available_stock >= quantity:
                return variant
        return None

    def _alternatives(self, variants: list[ProductVariant], color: str | None, size: str | None, quantity: int) -> list[VariantAlternative]:
        ranked: list[tuple[int, VariantAlternative]] = []
        for variant in variants:
            if not variant.is_active or variant.available_stock <= 0:
                continue
            v_color = self._variant_color(variant)
            v_size = self._variant_size(variant)
            score = 0
            reasons = []
            if color and v_color == color:
                score += 3
                reasons.append("same_color")
            if size and v_size == size:
                score += 3
                reasons.append("same_size")
            if variant.available_stock >= quantity:
                score += 1
                reasons.append("in_stock")
            ranked.append((score, VariantAlternative(
                variant_id=variant.id, sku=variant.sku, color=variant.color, size=variant.size,
                normalized_color=v_color, normalized_size=v_size, available_stock=max(variant.available_stock, 0),
                reason=", ".join(reasons) or "available_variant",
            )))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [item for _, item in ranked[:5]]

    def _should_log(self, mismatch_reasons: list[str]) -> bool:
        return bool(set(UNAVAILABLE_REASON_MAP).intersection(mismatch_reasons))

    def _primary_log_reason(self, mismatch_reasons: list[str]) -> str:
        for reason in mismatch_reasons:
            if reason in UNAVAILABLE_REASON_MAP:
                return UNAVAILABLE_REASON_MAP[reason]
        return "variant_not_found"

    def _log_unavailable(self, *, shop_id: UUID, product_id: UUID | None, raw_color: str | None, normalized_color: str | None, raw_size: str | None, normalized_size: str | None, quantity: int, reason: str, conversation_id: UUID | None, customer_id: UUID | None, estimated_lost_revenue: Decimal | None) -> None:
        # Keep the legacy aggregate table populated for existing analytics while writing
        # the Sprint A audit table with raw and normalized request data.
        if product_id is not None:
            self.db.add(UnavailableDemand(shop_id=shop_id, product_id=product_id, requested_color=normalized_color, requested_size=normalized_size, quantity=quantity, lost_revenue_estimate=estimated_lost_revenue or 0))
        self.db.add(UnavailableDemandLog(
            shop_id=shop_id,
            product_id=product_id,
            requested_color_raw=raw_color,
            requested_color_normalized=normalized_color,
            requested_size_raw=raw_size,
            requested_size_normalized=normalized_size,
            requested_quantity=quantity,
            reason=reason,
            conversation_id=conversation_id,
            customer_id=customer_id,
            estimated_lost_revenue=estimated_lost_revenue,
        ))
        self.db.commit()

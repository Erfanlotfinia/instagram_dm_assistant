from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import ColorAlias, SizeAlias

_PERSIAN_CHARS = str.maketrans({
    "ي": "ی", "ى": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه", "ؤ": "و", "أ": "ا", "إ": "ا",
    "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4", "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4", "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
})

COLOR_ALIASES: dict[str, str] = {
    "black": "black", "مشکی": "black", "سیاه": "black", "mshki": "black", "meshki": "black",
    "white": "white", "سفید": "white", "sefid": "white",
    "cream": "cream", "کرم": "cream", "creme": "cream", "کِرم": "cream",
    "charcoal": "charcoal", "ذغالی": "charcoal", "زغالی": "charcoal", "دودی": "charcoal",
    "navy": "navy", "سرمه ای": "navy", "سرمه‌ای": "navy", "سورمه ای": "navy", "سرمه": "navy",
    "gray": "gray", "grey": "gray", "طوسی": "gray", "توسی": "gray", "خاکستری": "gray", "طوسى": "gray",
    "brown": "brown", "قهوه ای": "brown", "قهوه‌ای": "brown",
    "coffee": "coffee", "نسکافه ای": "coffee", "نسکافه‌ای": "coffee",
    "red": "red", "قرمز": "red", "ghermez": "red",
    "blue": "blue", "آبی": "blue", "ابی": "blue",
    "green": "green", "سبز": "green",
    "pink": "pink", "صورتی": "pink",
    "beige": "beige", "بژ": "beige",
}

SIZE_ALIASES: dict[str, str] = {
    "اس": "S", "s": "S", "small": "S",
    "ام": "M", "m": "M", "medium": "M",
    "ال": "L", "l": "L", "large": "L",
    "ایکس لارج": "XL", "ایکس‌لارج": "XL", "xl": "XL",
    "فری سایز": "FREE", "فری‌سایز": "FREE", "تک سایز": "FREE", "one size": "FREE", "free size": "FREE", "freesize": "FREE", "onesize": "FREE", "فری": "FREE", "تک": "FREE",
    "36": "36", "38": "38", "40": "40", "42": "42",
}
STANDARD_ALPHA_SIZES = {"XS", "S", "M", "L", "XL", "XXL", "XXXL"}

NormalizationSource = Literal["shop_alias", "global_alias", "exact", "fuzzy", "none"]


def clean_fashion_text(value: str | int | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip().casefold().translate(_PERSIAN_CHARS)
    text = text.replace("‌", " ").replace("-", " ").replace("_", " ")
    text = re.sub(r"[^\w\sآ-ی]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


@dataclass(frozen=True)
class NormalizerOutput:
    raw_value: str | None
    normalized_value: str | None
    matched: bool
    confidence: float
    source: NormalizationSource


@dataclass(frozen=True)
class NormalizedValue:
    raw: str | None
    normalized: str | None
    confidence: float
    reason: str | None = None
    source: NormalizationSource = "none"


def _to_legacy(result: NormalizerOutput, missing_reason: str, unknown_reason: str) -> NormalizedValue:
    if result.normalized_value is None:
        return NormalizedValue(raw=result.raw_value, normalized=None, confidence=result.confidence, reason=missing_reason, source=result.source)
    return NormalizedValue(
        raw=result.raw_value,
        normalized=result.normalized_value,
        confidence=result.confidence,
        reason=None if result.matched else unknown_reason,
        source=result.source,
    )


class ColorNormalizer:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def normalize(self, shop_id: UUID | None, raw_value: str | None) -> NormalizerOutput:
        cleaned = clean_fashion_text(raw_value)
        if not cleaned:
            return NormalizerOutput(raw_value=raw_value, normalized_value=None, matched=False, confidence=0.0, source="none")
        alias = self._alias(shop_id, cleaned, shop_only=True)
        if alias:
            return NormalizerOutput(raw_value=raw_value, normalized_value=alias.normalized_value, matched=True, confidence=0.98, source="shop_alias")
        alias = self._alias(None, cleaned, shop_only=False)
        if alias:
            return NormalizerOutput(raw_value=raw_value, normalized_value=alias.normalized_value, matched=True, confidence=0.95, source="global_alias")
        if cleaned in COLOR_ALIASES:
            return NormalizerOutput(raw_value=raw_value, normalized_value=COLOR_ALIASES[cleaned], matched=True, confidence=0.95, source="global_alias")
        if cleaned in set(COLOR_ALIASES.values()):
            return NormalizerOutput(raw_value=raw_value, normalized_value=cleaned, matched=True, confidence=1.0, source="exact")
        compact = cleaned.replace(" ", "")
        for alias_value, canonical in COLOR_ALIASES.items():
            if alias_value.replace(" ", "") == compact:
                return NormalizerOutput(raw_value=raw_value, normalized_value=canonical, matched=True, confidence=0.9, source="fuzzy")
        fuzzy = difflib.get_close_matches(cleaned, COLOR_ALIASES.keys(), n=1, cutoff=0.86)
        if fuzzy:
            return NormalizerOutput(raw_value=raw_value, normalized_value=COLOR_ALIASES[fuzzy[0]], matched=True, confidence=0.8, source="fuzzy")
        return NormalizerOutput(raw_value=raw_value, normalized_value=cleaned, matched=False, confidence=0.55, source="none")

    def _alias(self, shop_id: UUID | None, cleaned: str, *, shop_only: bool) -> ColorAlias | None:
        if self.db is None:
            return None
        if shop_id is None and shop_only:
            return None
        stmt = select(ColorAlias).where(ColorAlias.raw_value == cleaned, ColorAlias.is_active.is_(True))
        stmt = stmt.where(ColorAlias.shop_id == shop_id if shop_id is not None else ColorAlias.shop_id.is_(None))
        return self.db.scalar(stmt.order_by(ColorAlias.updated_at.desc() if hasattr(ColorAlias, "updated_at") else ColorAlias.raw_value))


class SizeNormalizer:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def normalize(self, shop_id: UUID | None, raw_value: str | int | None, *, category: str | None = None, size_chart: dict[str, Any] | None = None) -> NormalizerOutput:
        cleaned = clean_fashion_text(raw_value)
        if not cleaned:
            return NormalizerOutput(raw_value=None if raw_value is None else str(raw_value), normalized_value=None, matched=False, confidence=0.0, source="none")
        alias = self._alias(shop_id, cleaned, category, shop_only=True)
        if alias:
            return NormalizerOutput(raw_value=str(raw_value), normalized_value=alias.normalized_value, matched=True, confidence=0.98, source="shop_alias")
        alias = self._alias(None, cleaned, category, shop_only=False)
        if alias:
            return NormalizerOutput(raw_value=str(raw_value), normalized_value=alias.normalized_value, matched=True, confidence=0.95, source="global_alias")
        alpha = cleaned.upper().replace(" ", "")
        if alpha in STANDARD_ALPHA_SIZES:
            return NormalizerOutput(raw_value=str(raw_value), normalized_value=alpha, matched=True, confidence=1.0, source="exact")
        numeric_match = re.fullmatch(r"(?:سایز\s*)?(\d{2,3})(?:\s*(?:shoe|کفش))?", cleaned)
        if numeric_match:
            size = numeric_match.group(1)
            conf = 1.0
            if category and any(token in category.casefold() for token in ("shoe", "shoes", "کفش")):
                conf = 1.0 if 34 <= int(size) <= 48 else 0.65
            return NormalizerOutput(raw_value=str(raw_value), normalized_value=size, matched=True, confidence=conf, source="exact")
        if cleaned in SIZE_ALIASES:
            return NormalizerOutput(raw_value=str(raw_value), normalized_value=SIZE_ALIASES[cleaned], matched=True, confidence=0.95, source="global_alias")
        if size_chart:
            aliases = size_chart.get("aliases", {})
            normalized = aliases.get(cleaned) or aliases.get(alpha)
            if normalized:
                return NormalizerOutput(raw_value=str(raw_value), normalized_value=str(normalized), matched=True, confidence=0.98, source="shop_alias")
        fuzzy = difflib.get_close_matches(cleaned, SIZE_ALIASES.keys(), n=1, cutoff=0.86)
        if fuzzy:
            return NormalizerOutput(raw_value=str(raw_value), normalized_value=SIZE_ALIASES[fuzzy[0]], matched=True, confidence=0.8, source="fuzzy")
        return NormalizerOutput(raw_value=str(raw_value), normalized_value=alpha, matched=False, confidence=0.55, source="none")

    def _alias(self, shop_id: UUID | None, cleaned: str, category: str | None, *, shop_only: bool) -> SizeAlias | None:
        if self.db is None:
            return None
        if shop_id is None and shop_only:
            return None
        stmt = select(SizeAlias).where(SizeAlias.raw_value == cleaned, SizeAlias.is_active.is_(True))
        stmt = stmt.where(SizeAlias.shop_id == shop_id if shop_id is not None else SizeAlias.shop_id.is_(None))
        stmt = stmt.where((SizeAlias.category == category) | (SizeAlias.category.is_(None)))
        return self.db.scalar(stmt.order_by(SizeAlias.category.desc().nullslast()))


def normalize_color(raw: str | None) -> NormalizedValue:
    return _to_legacy(ColorNormalizer().normalize(None, raw), "missing_color", "unknown_color_alias")


def normalize_size(raw: str | int | None, *, category: str | None = None, size_chart: dict[str, Any] | None = None) -> NormalizedValue:
    result = SizeNormalizer().normalize(None, raw, category=category, size_chart=size_chart)
    # Backward compatible alias expected by existing tests/UI.
    normalized = "FREE_SIZE" if result.normalized_value == "FREE" else result.normalized_value
    result = NormalizerOutput(result.raw_value, normalized, result.matched, result.confidence, result.source)
    return _to_legacy(result, "missing_size", "unknown_size_alias")

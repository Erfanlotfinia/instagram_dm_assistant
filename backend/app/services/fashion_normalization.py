from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_PERSIAN_CHARS = str.maketrans({"ي": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه", "ؤ": "و", "أ": "ا", "إ": "ا"})


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower().translate(_PERSIAN_CHARS)
    text = text.replace("‌", " ").replace("-", " ").replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    return text or None

COLOR_ALIASES: dict[str, str] = {
    "black": "black", "مشکی": "black", "سیاه": "black", "mshki": "black", "meshki": "black",
    "white": "white", "سفید": "white", "sefid": "white",
    "cream": "cream", "کرم": "cream", "creme": "cream", "کِرم": "cream",
    "charcoal": "charcoal", "ذغالی": "charcoal", "زغالی": "charcoal", "دودی": "charcoal",
    "navy": "navy", "سرمه ای": "navy", "سرمه‌ای": "navy", "سورمه ای": "navy", "سرمه": "navy",
    "gray": "gray", "grey": "gray", "طوسی": "gray", "توسی": "gray", "خاکستری": "gray", "طوسى": "gray",
    "red": "red", "قرمز": "red", "ghermez": "red",
    "blue": "blue", "آبی": "blue", "ابی": "blue",
    "green": "green", "سبز": "green",
    "pink": "pink", "صورتی": "pink",
    "beige": "beige", "بژ": "beige",
    "brown": "brown", "قهوه ای": "brown", "قهوه‌ای": "brown",
}

STANDARD_ALPHA_SIZES = {"XS", "S", "M", "L", "XL", "XXL", "XXXL"}
FREE_SIZE_ALIASES = {"فری سایز", "تک سایز", "free size", "freesize", "one size", "onesize", "فری", "تک"}


@dataclass(frozen=True)
class NormalizedValue:
    raw: str | None
    normalized: str | None
    confidence: float
    reason: str | None = None


def normalize_color(raw: str | None) -> NormalizedValue:
    cleaned = _clean(raw)
    if not cleaned:
        return NormalizedValue(raw=raw, normalized=None, confidence=0.0, reason="missing_color")
    normalized = COLOR_ALIASES.get(cleaned)
    if normalized:
        return NormalizedValue(raw=raw, normalized=normalized, confidence=1.0)
    compact = cleaned.replace(" ", "")
    for alias, canonical in COLOR_ALIASES.items():
        if alias.replace(" ", "") == compact:
            return NormalizedValue(raw=raw, normalized=canonical, confidence=0.95)
    return NormalizedValue(raw=raw, normalized=cleaned, confidence=0.55, reason="unknown_color_alias")


def normalize_size(raw: str | int | None, *, category: str | None = None, size_chart: dict[str, Any] | None = None) -> NormalizedValue:
    if raw is None:
        return NormalizedValue(raw=None, normalized=None, confidence=0.0, reason="missing_size")
    cleaned = _clean(str(raw))
    if not cleaned:
        return NormalizedValue(raw=str(raw), normalized=None, confidence=0.0, reason="missing_size")
    if cleaned in FREE_SIZE_ALIASES:
        return NormalizedValue(raw=str(raw), normalized="FREE_SIZE", confidence=1.0)
    alpha = cleaned.upper().replace(" ", "")
    if alpha in STANDARD_ALPHA_SIZES:
        return NormalizedValue(raw=str(raw), normalized=alpha, confidence=1.0)
    numeric_match = re.fullmatch(r"(?:سایز\s*)?(\d{2,3})(?:\s*(?:shoe|کفش))?", cleaned)
    if numeric_match:
        size = numeric_match.group(1)
        conf = 1.0
        if category and any(token in category.lower() for token in ("shoe", "shoes", "کفش")):
            conf = 1.0 if 34 <= int(size) <= 48 else 0.65
        return NormalizedValue(raw=str(raw), normalized=size, confidence=conf)
    if size_chart:
        aliases = size_chart.get("aliases", {})
        normalized = aliases.get(cleaned) or aliases.get(alpha)
        if normalized:
            return NormalizedValue(raw=str(raw), normalized=str(normalized), confidence=0.98)
    return NormalizedValue(raw=str(raw), normalized=cleaned.upper(), confidence=0.55, reason="unknown_size_alias")

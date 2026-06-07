from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class NormalizedValueRead(BaseModel):
    raw: str | None = None
    normalized: str | None = None
    confidence: float
    reason: str | None = None


class VariantAlternative(BaseModel):
    variant_id: UUID
    sku: str
    color: str | None = None
    size: str | None = None
    normalized_color: str | None = None
    normalized_size: str | None = None
    available_stock: int
    reason: str


class VariantResolverRequest(BaseModel):
    product_id: UUID
    raw_color: str | None = None
    raw_size: str | None = None
    quantity: int = Field(default=1, ge=1)


class VariantResolverResult(BaseModel):
    variant_id: UUID | None = None
    sku: str | None = None
    normalized_color: str | None = None
    normalized_size: str | None = None
    color_confidence: float = 0.0
    size_confidence: float = 0.0
    confidence: float = 0.0
    mismatch_reasons: list[str] = Field(default_factory=list)
    available_alternatives: list[VariantAlternative] = Field(default_factory=list)
    available_stock: int | None = None


class NormalizeColorRequest(BaseModel):
    raw_color: str | None = None


class NormalizeSizeRequest(BaseModel):
    raw_size: str | None = None
    category: str | None = None
    size_chart: dict | None = None

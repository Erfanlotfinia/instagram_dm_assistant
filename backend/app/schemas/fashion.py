from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class NormalizedValueRead(BaseModel):
    raw: str | None = None
    normalized: str | None = None
    raw_value: str | None = None
    normalized_value: str | None = None
    matched: bool | None = None
    confidence: float
    source: str | None = None
    reason: str | None = None


class VariantAlternative(BaseModel):
    variant_id: UUID
    sku: str
    color: str | None = None
    size: str | None = None
    normalized_color: str | None = None
    normalized_size: str | None = None
    normalized_attributes: dict[str, str] = Field(default_factory=dict)
    available_stock: int
    reason: str


class VariantResolverRequest(BaseModel):
    product_id: UUID
    raw_color: str | None = None
    raw_size: str | None = None
    raw_requested_attributes: dict[str, str | None] = Field(default_factory=dict)
    quantity: int = Field(default=1, ge=1)


class VariantResolverResult(BaseModel):
    matched: bool = False
    variant_id: UUID | None = None
    sku: str | None = None
    normalized_color: str | None = None
    normalized_size: str | None = None
    normalized_attributes: dict[str, str] = Field(default_factory=dict)
    color_confidence: float = 0.0
    size_confidence: float = 0.0
    confidence: float = 0.0
    mismatch_reasons: list[str] = Field(default_factory=list)
    available_alternatives: list[VariantAlternative] = Field(default_factory=list)
    alternatives: list[VariantAlternative] = Field(default_factory=list)
    available_stock: int | None = None


class NormalizeColorRequest(BaseModel):
    raw_color: str | None = None


class NormalizeSizeRequest(BaseModel):
    raw_size: str | None = None
    category: str | None = None
    size_chart: dict | None = None

class ColorAliasCreate(BaseModel):
    raw_value: str
    normalized_value: str
    language: str = "und"


class ColorAliasRead(ColorAliasCreate):
    id: UUID
    shop_id: UUID | None = None
    is_active: bool
    model_config = {"from_attributes": True}


class SizeAliasCreate(BaseModel):
    raw_value: str
    normalized_value: str
    category: str | None = None


class SizeAliasRead(SizeAliasCreate):
    id: UUID
    shop_id: UUID | None = None
    is_active: bool
    model_config = {"from_attributes": True}


class AttributeAliasCreate(BaseModel):
    attribute_slug: str = Field(min_length=1, max_length=128)
    raw_value: str = Field(min_length=1, max_length=128)
    normalized_value: str = Field(min_length=1, max_length=128)
    language: str = "und"


class AttributeAliasRead(AttributeAliasCreate):
    id: UUID
    shop_id: UUID | None = None
    attribute_definition_id: UUID
    is_active: bool
    model_config = {"from_attributes": True}


class SizeChartCreate(BaseModel):
    product_id: UUID | None = None
    category: str
    chart_json: dict = Field(default_factory=dict)


class SizeChartRead(SizeChartCreate):
    id: UUID
    shop_id: UUID
    model_config = {"from_attributes": True}


class ColorAliasUpdate(BaseModel):
    raw_value: str | None = None
    normalized_value: str | None = None
    language: str | None = None
    is_active: bool | None = None


class SizeAliasUpdate(BaseModel):
    raw_value: str | None = None
    normalized_value: str | None = None
    category: str | None = None
    is_active: bool | None = None


class UnavailableDemandRead(BaseModel):
    id: UUID
    shop_id: UUID
    product_id: UUID | None = None
    requested_color_raw: str | None = None
    requested_color_normalized: str | None = None
    requested_size_raw: str | None = None
    requested_size_normalized: str | None = None
    requested_quantity: int
    reason: str
    conversation_id: UUID | None = None
    customer_id: UUID | None = None
    estimated_lost_revenue: float | None = None
    model_config = {"from_attributes": True}

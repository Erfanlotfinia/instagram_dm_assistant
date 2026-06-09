from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CatalogImportRow(BaseModel):
    title: str
    description: str | None = None
    brand: str | None = None
    color: str | None = None
    size: str | None = None
    material: str | None = None
    gender: str | None = None
    collection: str | None = None
    base_price: float | None = None
    currency: str | None = None
    category: str | None = None
    aliases: list[str] = Field(default_factory=list)
    variants: list[dict] = Field(default_factory=list)


class CatalogImportRequest(BaseModel):
    shop_id: UUID
    rows: list[CatalogImportRow] = Field(default_factory=list)
    source_format: str = "json"
    resume_job_id: UUID | None = None


class CatalogImportJobRead(BaseModel):
    id: UUID
    shop_id: UUID
    status: str
    source_format: str
    total_rows: int
    processed_rows: int
    failed_rows: int
    checkpoint: dict = Field(default_factory=dict)
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    model_config = {"from_attributes": True}


class CatalogReindexRequest(BaseModel):
    shop_id: UUID
    product_ids: list[UUID] | None = None
    resume_job_id: UUID | None = None
    batch_size: int | None = Field(default=None, ge=1, le=500)


class CatalogReindexJobRead(BaseModel):
    job_id: UUID
    shop_id: UUID
    status: str
    total_products: int
    indexed_products: int
    checkpoint: dict = Field(default_factory=dict)


class ProductAliasRead(BaseModel):
    id: UUID
    alias_text: str
    language: str
    source: str
    confidence: float
    is_active: bool
    model_config = {"from_attributes": True}

    @field_validator("source", mode="before")
    @classmethod
    def coerce_source(cls, value: object) -> str:
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)


class ProductNormalizedRead(BaseModel):
    id: UUID
    shop_id: UUID
    product_id: UUID
    normalized_title: str
    brand: str | None = None
    color: str | None = None
    size: str | None = None
    material: str | None = None
    gender: str | None = None
    collection: str | None = None
    synonym_candidates: list[str] = Field(default_factory=list)
    qdrant_point_id: str | None = None
    embedding_model: str | None = None
    last_normalized_at: datetime | None = None
    last_indexed_at: datetime | None = None
    aliases: list[ProductAliasRead] = Field(default_factory=list)
    model_config = {"from_attributes": True}


class CatalogProductListResponse(BaseModel):
    items: list[ProductNormalizedRead]
    total: int
    page: int
    page_size: int


class ProductAliasesPatchRequest(BaseModel):
    add: list[str] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)
    language: str = "und"


class ProductAliasesPatchResponse(BaseModel):
    product_id: UUID
    aliases: list[ProductAliasRead]

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ResolveMediaReference(BaseModel):
    media_id: str | None = None
    media_url: str | None = None


class ResolveConversationContext(BaseModel):
    conversation_id: UUID | None = None
    prior_product_id: UUID | None = None
    prior_messages: list[str] = Field(default_factory=list)
    extracted_slots: dict = Field(default_factory=dict)


class ResolveProductRequest(BaseModel):
    shop_id: UUID
    message_text: str
    media_references: list[ResolveMediaReference] = Field(default_factory=list)
    conversation_context: ResolveConversationContext | None = None
    limit: int = Field(default=5, ge=1, le=20)
    fusion_strategy: str | None = None


class ProductCandidate(BaseModel):
    product_id: UUID
    title: str
    score: float
    confidence_band: str
    rationale: str
    matched_aliases: list[str] = Field(default_factory=list)
    rules_fired: list[str] = Field(default_factory=list)


class ResolveProductResponse(BaseModel):
    trace_id: UUID
    query: str
    candidates: list[ProductCandidate]
    confidence_band: str
    confidence_score: float
    missing_slots: list[str] = Field(default_factory=list)
    rationale: str | None = None


class ResolveVariantRequest(BaseModel):
    shop_id: UUID
    message_text: str
    product_id: UUID | None = None
    candidate_product_ids: list[UUID] = Field(default_factory=list)
    media_references: list[ResolveMediaReference] = Field(default_factory=list)
    conversation_context: ResolveConversationContext | None = None
    raw_color: str | None = None
    raw_size: str | None = None
    quantity: int = Field(default=1, ge=1)
    limit: int = Field(default=5, ge=1, le=20)


class VariantCandidate(BaseModel):
    variant_id: UUID
    product_id: UUID
    sku: str
    color: str | None = None
    size: str | None = None
    normalized_color: str | None = None
    normalized_size: str | None = None
    available_stock: int
    score: float
    confidence_band: str
    rationale: str
    matched_aliases: list[str] = Field(default_factory=list)
    rules_fired: list[str] = Field(default_factory=list)


class ResolveVariantResponse(BaseModel):
    trace_id: UUID
    product_id: UUID | None = None
    candidates: list[VariantCandidate]
    confidence_band: str
    confidence_score: float
    missing_slots: list[str] = Field(default_factory=list)
    rationale: str | None = None


class ResolverTraceRead(BaseModel):
    id: UUID
    shop_id: UUID
    trace_type: str
    conversation_id: UUID | None = None
    input_payload: dict = Field(default_factory=dict)
    top_candidates: list[dict] = Field(default_factory=list)
    matched_aliases: list[dict] = Field(default_factory=list)
    rules_fired: list[str] = Field(default_factory=list)
    missing_slots: list[str] = Field(default_factory=list)
    confidence_band: str
    confidence_score: float
    rationale: str | None = None
    qdrant_query_metadata: dict = Field(default_factory=dict)
    created_at: datetime
    model_config = {"from_attributes": True}


class ResolverFeedbackRequest(BaseModel):
    shop_id: UUID
    action: str
    original_product_id: UUID | None = None
    corrected_product_id: UUID | None = None
    original_variant_id: UUID | None = None
    corrected_variant_id: UUID | None = None
    notes: str | None = None


class ResolverFeedbackRead(BaseModel):
    id: UUID
    shop_id: UUID
    trace_id: UUID
    action: str
    operator_id: UUID
    original_product_id: UUID | None = None
    corrected_product_id: UUID | None = None
    original_variant_id: UUID | None = None
    corrected_variant_id: UUID | None = None
    notes: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class ResolverConfidenceThresholds(BaseModel):
    high: float = 0.85
    medium: float = 0.55

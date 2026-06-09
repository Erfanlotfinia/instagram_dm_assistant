from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AgentIntent, AgentRunStatus, AgentWorkflowState


class StrictAgentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProductReference(StrictAgentModel):
    instagram_post_url: str | None = None
    instagram_media_id: str | None = None


class ExtractedSlots(StrictAgentModel):
    color: str | None = None
    size: str | None = None
    quantity: int | None = Field(default=None, ge=1, le=100)
    customer_name: str | None = None
    phone: str | None = None
    city: str | None = None
    address: str | None = None
    postal_code: str | None = None


class ExtractionConfidence(StrictAgentModel):
    intent: float = Field(default=0.0, ge=0.0, le=1.0)
    slots: float = Field(default=0.0, ge=0.0, le=1.0)
    product: float = Field(default=0.0, ge=0.0, le=1.0)
    variant: float = Field(default=0.0, ge=0.0, le=1.0)
    address: float = Field(default=1.0, ge=0.0, le=1.0)


class AgentExtractionResult(StrictAgentModel):
    intent: AgentIntent
    product_reference: ProductReference = Field(default_factory=ProductReference)
    slots: ExtractedSlots = Field(default_factory=ExtractedSlots)
    missing_fields: list[str] = Field(default_factory=list)
    confidence: ExtractionConfidence = Field(default_factory=ExtractionConfidence)
    needs_human: bool = False
    human_reason: str | None = None
    reply_style_hint: str | None = None


class AgentExtractionInput(BaseModel):
    message_text: str | None
    shared_post_url: str | None
    workflow_state: AgentWorkflowState
    known_slots: dict[str, Any]
    product_info: dict[str, Any] | None
    valid_colors: list[str]
    valid_sizes: list[str]


class ConversationSlotsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    product_id: UUID | None
    product_variant_id: UUID | None
    instagram_post_url: str | None
    color: str | None
    normalized_color: str | None = None
    size: str | None
    normalized_size: str | None = None
    variant_alternatives: list[dict[str, Any]] = Field(default_factory=list)
    quantity: int | None
    customer_name: str | None
    phone: str | None
    city: str | None
    address: str | None
    postal_code: str | None
    missing_fields: list[str]
    confidence: dict[str, Any]
    updated_at: datetime


class AgentActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    action_name: str
    input_json: dict[str, Any]
    output_json: dict[str, Any]
    confidence: float | None
    status: str
    error_message: str | None
    created_at: datetime


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    input_message_id: UUID
    model_name: str
    prompt_version: str
    input_json: dict[str, Any]
    output_json: dict[str, Any]
    status: AgentRunStatus
    error_message: str | None
    created_at: datetime


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)


class SemanticSearchHit(BaseModel):
    product_id: UUID
    title: str
    score: float
    description: str | None = None


class SemanticSearchResponse(BaseModel):
    query: str
    hits: list[SemanticSearchHit]

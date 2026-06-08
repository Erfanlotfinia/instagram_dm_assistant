from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import (
    AgentMode,
    AgentWorkflowState,
    ConversationEventType,
    ConversationPriorityLevel,
    ConversationState,
    MessageDirection,
    MessageType,
)
from app.schemas.agent import AgentActionRead, AgentRunRead, ConversationSlotsRead
from app.schemas.customer import CustomerProfileRead, CustomerUpdate
from app.schemas.suggested_reply import SuggestedReplyRead


class CustomerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    instagram_user_id: str
    full_name: str | None = None


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    instagram_user_id: str
    full_name: str | None = None
    phone: str | None = None
    city: str | None = None
    address: str | None = None
    postal_code: str | None = None
    notes: str | None = None


class ConversationListFilters(BaseModel):
    state: ConversationState | None = None
    handoff_required: bool | None = None
    assigned_operator_id: UUID | None = None
    unassigned: bool | None = None
    updated_from: datetime | None = None
    updated_to: datetime | None = None
    search: str | None = Field(default=None, max_length=255)
    priority_level: ConversationPriorityLevel | None = None
    priority_levels: list[ConversationPriorityLevel] | None = None
    needs_attention: bool | None = None
    waiting_for_payment: bool | None = None
    ready_to_order: bool | None = None
    low_confidence: bool | None = None
    is_simulation: bool | None = None


class LinkedProductSummary(BaseModel):
    id: UUID
    title: str


class LinkedOrderSummary(BaseModel):
    id: UUID
    status: str
    payment_status: str
    total_amount: str


class OperatorSummary(BaseModel):
    id: UUID
    full_name: str


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    instagram_account_id: UUID
    customer_id: UUID
    state: ConversationState
    last_intent: str | None
    assigned_operator_id: UUID | None
    handoff_required: bool
    handoff_reason: str | None
    workflow_state: AgentWorkflowState
    agent_paused: bool
    is_simulation: bool = False
    suggested_outbound: str | None = None
    preview_required: bool = False
    preview_reason: str | None = None
    priority_score: int = 0
    priority_level: ConversationPriorityLevel = ConversationPriorityLevel.LOW
    priority_reason: str | None = None
    needs_attention: bool = False
    last_operator_action_at: datetime | None = None
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime
    customer: CustomerSummary | None = None
    assigned_operator: OperatorSummary | None = None
    last_message_text: str | None = None
    last_message_direction: MessageDirection | None = None
    confidence_score: float | None = None
    agent_mode: AgentMode | None = None
    linked_product: LinkedProductSummary | None = None
    linked_order: LinkedOrderSummary | None = None

    @field_validator("customer", mode="before")
    @classmethod
    def _coerce_customer(cls, value: Any) -> Any:
        if value is None or isinstance(value, CustomerSummary):
            return value
        if hasattr(value, "id") and hasattr(value, "instagram_user_id"):
            return CustomerSummary(
                id=value.id,
                instagram_user_id=value.instagram_user_id,
                full_name=getattr(value, "full_name", None),
            )
        return value

    @field_validator("assigned_operator", mode="before")
    @classmethod
    def _coerce_assigned_operator(cls, value: Any) -> Any:
        if value is None or isinstance(value, OperatorSummary):
            return value
        if hasattr(value, "id") and hasattr(value, "full_name"):
            return OperatorSummary(id=value.id, full_name=value.full_name)
        return value


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    direction: MessageDirection
    message_type: MessageType
    text: str | None
    created_at: datetime
    raw_payload: dict[str, Any] | None = Field(default=None)


class MessageCreate(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class ConversationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    event_type: ConversationEventType
    title: str
    description: str | None = None
    metadata: dict[str, Any] | None = Field(
        default=None, validation_alias="event_metadata", serialization_alias="metadata"
    )
    created_by_user_id: UUID | None = None
    created_at: datetime


class InventoryStatusRead(BaseModel):
    variant_id: UUID | None = None
    in_stock: bool | None = None
    available_quantity: int | None = None


class ConversationDetailRead(ConversationRead):
    messages: list[MessageRead] = Field(default_factory=list)
    slots: ConversationSlotsRead | None = None
    agent_runs: list[AgentRunRead] = Field(default_factory=list)
    agent_actions: list[AgentActionRead] = Field(default_factory=list)
    customer: CustomerRead | None = None
    customer_profile: CustomerProfileRead | None = None
    linked_product: LinkedProductSummary | None = None
    linked_order: LinkedOrderSummary | None = None
    suggested_replies: list[SuggestedReplyRead] = Field(default_factory=list)
    events: list[ConversationEventRead] = Field(default_factory=list)
    inventory_status: InventoryStatusRead | None = None
    decision_trace_summary: str | None = None


class ConversationHandoffResponse(BaseModel):
    conversation_id: UUID
    workflow_state: AgentWorkflowState
    handoff_required: bool
    handoff_reason: str | None
    agent_paused: bool
    suggested_outbound: str | None = None
    preview_required: bool = False
    preview_reason: str | None = None
    assigned_operator_id: UUID | None
    priority_score: int = 0
    priority_level: ConversationPriorityLevel = ConversationPriorityLevel.LOW
    needs_attention: bool = False


class ConversationResolveResponse(BaseModel):
    conversation_id: UUID
    state: ConversationState


class ConversationAssignRequest(BaseModel):
    operator_id: UUID


class ConversationAssignResponse(BaseModel):
    conversation_id: UUID
    assigned_operator_id: UUID
    assigned_operator_name: str | None = None

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AgentWorkflowState, ConversationState, MessageDirection, MessageType
from app.schemas.agent import AgentActionRead, AgentRunRead, ConversationSlotsRead


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


class CustomerUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    city: str | None = Field(default=None, max_length=128)
    address: str | None = None
    postal_code: str | None = Field(default=None, max_length=32)
    notes: str | None = None


class ConversationListFilters(BaseModel):
    state: ConversationState | None = None
    handoff_required: bool | None = None
    assigned_operator_id: UUID | None = None
    updated_from: datetime | None = None
    updated_to: datetime | None = None
    search: str | None = Field(default=None, max_length=255)


class LinkedProductSummary(BaseModel):
    id: UUID
    title: str


class LinkedOrderSummary(BaseModel):
    id: UUID
    status: str
    payment_status: str
    total_amount: str


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
    last_message_at: datetime | None
    created_at: datetime
    updated_at: datetime
    customer: CustomerSummary | None = None
    last_message_text: str | None = None
    last_message_direction: MessageDirection | None = None
    confidence_score: float | None = None


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


class ConversationDetailRead(ConversationRead):
    messages: list[MessageRead] = Field(default_factory=list)
    slots: ConversationSlotsRead | None = None
    agent_runs: list[AgentRunRead] = Field(default_factory=list)
    agent_actions: list[AgentActionRead] = Field(default_factory=list)
    customer: CustomerRead | None = None
    linked_product: LinkedProductSummary | None = None
    linked_order: LinkedOrderSummary | None = None


class ConversationHandoffResponse(BaseModel):
    conversation_id: UUID
    workflow_state: AgentWorkflowState
    handoff_required: bool
    handoff_reason: str | None
    agent_paused: bool
    assigned_operator_id: UUID | None


class ConversationResolveResponse(BaseModel):
    conversation_id: UUID
    state: ConversationState

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    InventoryReservationStatus,
    OperatorReviewDecision,
    OrderCorrectnessAction,
    OrderStatus,
)


class OrderItemDraftCreate(BaseModel):
    product_id: UUID | None = None
    product_variant_id: UUID | None = None
    quantity: int = Field(default=1, ge=1)
    product_title_snapshot: str = ""
    variant_label_snapshot: str = ""
    unit_price: Decimal = Decimal("0")


class OrderDraftCreateRequest(BaseModel):
    shop_id: UUID
    customer_id: UUID
    conversation_id: UUID
    items: list[OrderItemDraftCreate] = Field(default_factory=list)
    customer_name: str = ""
    phone: str = ""
    city: str = ""
    address: str = ""
    postal_code: str = ""
    currency: str = "USD"
    confidence_score: Decimal | None = None
    idempotency_key: str | None = None
    is_simulation: bool = False


class OrderClarifyRequest(BaseModel):
    missing_fields: list[str] = Field(default_factory=list)
    notes: str | None = None


class OrderConfirmRequest(BaseModel):
    confirmation_source: str = "operator"
    operator_decision: OperatorReviewDecision | None = None
    reason: str | None = None
    notes: str | None = None


class OrderReserveRequest(BaseModel):
    ttl_seconds: int = Field(default=1800, ge=60)


class OrderCancelRequest(BaseModel):
    reason: str | None = None


class ReservationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_variant_id: UUID
    quantity: int
    status: InventoryReservationStatus
    expires_at: datetime
    confirmed_at: datetime | None = None
    released_at: datetime | None = None


class OrderItemDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID | None
    product_variant_id: UUID | None
    quantity: int
    product_title_snapshot: str
    variant_label_snapshot: str
    unit_price: Decimal


class PilotModeSnapshot(BaseModel):
    pilot_enabled: bool = False
    pilot_name: str = "Pilot"
    emergency_stop: bool = False
    require_operator_approval: bool = False


class OrderCorrectnessRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    customer_id: UUID
    conversation_id: UUID
    status: OrderStatus
    subtotal_amount: Decimal
    total_amount: Decimal
    currency: str
    payment_status: str
    shipping_status: str
    customer_name: str
    phone: str
    city: str
    address: str
    postal_code: str
    expires_at: datetime | None
    customer_confirmed_at: datetime | None
    customer_confirmation_source: str | None
    confidence_score: Decimal | None
    pilot_mode_snapshot: dict[str, Any] | None
    active_reservation_id: UUID | None
    draft_items: list[OrderItemDraftRead] = Field(default_factory=list)
    reservations: list[ReservationSummary] = Field(default_factory=list)
    is_simulation: bool


class TimelineEntry(BaseModel):
    entry_type: str
    occurred_at: datetime
    label: str
    status: str | None = None
    metadata: dict[str, Any] | None = None


class OrderTimelineResponse(BaseModel):
    order_id: UUID
    entries: list[TimelineEntry]


class ActionAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action: OrderCorrectnessAction
    allowed: bool
    denial_reasons: list[str] | None
    policy_snapshot: dict[str, Any] | None
    trace_id: str | None
    created_at: datetime

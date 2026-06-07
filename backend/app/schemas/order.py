from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    OrderPaymentStatus,
    OrderShippingStatus,
    OrderStatus,
    PaymentProvider,
    PaymentRecordStatus,
    ShipmentProvider,
    ShipmentStatus,
)


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID | None
    product_variant_id: UUID | None
    product_title_snapshot: str
    variant_color_snapshot: str | None
    variant_size_snapshot: str | None
    sku_snapshot: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: PaymentProvider
    status: PaymentRecordStatus
    payment_url: str | None
    provider_reference: str | None
    created_at: datetime
    updated_at: datetime


class ShipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: ShipmentProvider
    status: ShipmentStatus
    tracking_code: str | None
    tracking_url: str | None
    shipped_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OrderTimelineEvent(BaseModel):
    status: str
    label: str
    occurred_at: datetime
    source: str


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    customer_id: UUID
    conversation_id: UUID
    status: OrderStatus
    subtotal_amount: Decimal
    shipping_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    currency: str
    payment_status: OrderPaymentStatus
    shipping_status: OrderShippingStatus
    customer_name: str
    phone: str
    city: str
    address: str
    postal_code: str
    notes: str | None
    risk_flags: list[str] = Field(default_factory=list)
    approval_source: str | None = None
    payment_callback_status: str | None = None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead] = Field(default_factory=list)
    payments: list[PaymentRead] = Field(default_factory=list)
    shipments: list[ShipmentRead] = Field(default_factory=list)
    timeline: list[OrderTimelineEvent] = Field(default_factory=list)


class OrderListFilters(BaseModel):
    status: OrderStatus | None = None
    payment_status: OrderPaymentStatus | None = None
    shipping_status: OrderShippingStatus | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class OrderShipRequest(BaseModel):
    tracking_code: str = Field(min_length=1, max_length=128)
    tracking_url: str | None = Field(default=None, max_length=2048)
    provider: ShipmentProvider = ShipmentProvider.MANUAL


class OrderCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=512)

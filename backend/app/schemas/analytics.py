from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class FunnelAnalytics(BaseModel):
    inbound_messages: int = 0
    product_resolved_count: int = 0
    variant_resolved_count: int = 0
    draft_orders: int = 0
    confirmed_orders: int = 0
    waiting_for_payment: int = 0
    resolved_product_rate: float = 0.0
    variant_resolved_rate: float = 0.0
    draft_order_rate: float = 0.0
    payment_conversion_rate: float = 0.0
    paid_orders: int = 0
    revenue: Decimal = Decimal("0")
    abandoned_conversations: int = 0
    top_abandoned_reason: str | None = None
    operator_handoff_rate: float = 0.0
    average_time_to_first_response_seconds: float | None = None
    average_time_to_payment_seconds: float | None = None


class PostPerformanceRow(BaseModel):
    instagram_post_url: str
    product_id: UUID | None = None
    inbound_messages: int = 0
    draft_orders: int = 0
    paid_orders: int = 0
    revenue: Decimal = Decimal("0")
    conversion_rate: float = 0.0


class StockDemandRow(BaseModel):
    type: str
    value: str
    requests: int


class UnavailableDemandRow(BaseModel):
    requested_color: str | None = None
    requested_size: str | None = None
    product_id: UUID | None = None
    count: int = 0
    lost_revenue_estimate: Decimal = Decimal("0")


class HandoffAnalyticsRow(BaseModel):
    reason: str
    count: int
    rate: float


class AnalyticsDateRange(BaseModel):
    start: datetime | None = None
    end: datetime | None = None


class ResponseTimeAnalytics(BaseModel):
    average_first_response_time_seconds: float | None = None
    average_time_to_draft_order_seconds: float | None = None
    average_time_to_payment_seconds: float | None = None

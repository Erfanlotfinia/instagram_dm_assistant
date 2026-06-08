from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, computed_field


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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def product_resolved_rate(self) -> float:
        return self.resolved_product_rate


class PostPerformanceRow(BaseModel):
    instagram_post_url: str
    product_id: UUID | None = None
    inbound_messages: int = 0
    draft_orders: int = 0
    paid_orders: int = 0
    revenue: Decimal = Decimal("0")
    conversion_rate: float = 0.0


class PostRevenueRow(BaseModel):
    instagram_post_url: str
    product_id: UUID | None = None
    conversations: int = 0
    draft_orders: int = 0
    paid_orders: int = 0
    revenue: Decimal = Decimal("0")
    conversion_rate: float = 0.0
    abandoned_rate: float = 0.0


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


class LostDemandRow(BaseModel):
    requested_product: str | None = None
    requested_color: str | None = None
    requested_size: str | None = None
    product_id: UUID | None = None
    count: int = 0
    estimated_lost_revenue: Decimal = Decimal("0")
    reason: str | None = None


class LostDemandListResponse(BaseModel):
    items: list[LostDemandRow]
    total: int
    page: int
    page_size: int


class OperatorPerformanceRow(BaseModel):
    operator_id: UUID
    operator_name: str
    assigned_conversations: int = 0
    resolved_conversations: int = 0
    average_response_time_seconds: float | None = None
    manual_messages_sent: int = 0
    orders_closed: int = 0
    revenue_assisted: Decimal = Decimal("0")


class OperatorPerformanceListResponse(BaseModel):
    items: list[OperatorPerformanceRow]
    total: int
    page: int
    page_size: int


class AgentPerformanceMetrics(BaseModel):
    auto_sent_messages: int = 0
    preview_required_messages: int = 0
    handoff_rate: float = 0.0
    failed_agent_runs: int = 0
    invalid_llm_outputs: int = 0
    average_intent_confidence: float | None = None
    average_product_confidence: float | None = None
    average_variant_confidence: float | None = None

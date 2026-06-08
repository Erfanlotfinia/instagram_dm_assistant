from uuid import UUID

from pydantic import BaseModel, Field


class ConversionFunnelMetrics(BaseModel):
    inbound_messages: int = 0
    product_resolved: int = 0
    draft_orders: int = 0
    paid_orders: int = 0


class TopSellingPostSummary(BaseModel):
    instagram_post_url: str
    paid_orders: int = 0
    revenue: str = "0"


class LostDemandVariantSummary(BaseModel):
    requested_color: str | None = None
    requested_size: str | None = None
    product_id: UUID | None = None
    count: int = 0


class LowStockVariantSummary(BaseModel):
    variant_id: UUID
    product_id: UUID
    product_title: str
    sku: str
    color: str | None = None
    size: str | None = None
    available_stock: int


class DashboardMetrics(BaseModel):
    today_orders: int = 0
    paid_orders: int = 0
    waiting_for_payment: int = 0
    handoff_conversations: int = 0
    abandoned_orders: int = 0
    recovered_orders: int = 0
    recovered_revenue: str = "0"
    upsell_suggestions: int = 0
    upsell_accepted: int = 0
    top_selling_posts: list[TopSellingPostSummary] = Field(default_factory=list)
    top_lost_demand_variants: list[LostDemandVariantSummary] = Field(default_factory=list)
    low_stock_variants: list[LowStockVariantSummary] = Field(default_factory=list)
    conversion_funnel: ConversionFunnelMetrics = Field(default_factory=ConversionFunnelMetrics)

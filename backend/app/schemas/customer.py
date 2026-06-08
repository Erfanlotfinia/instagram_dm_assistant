from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CustomerUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    city: str | None = Field(default=None, max_length=128)
    address: str | None = None
    postal_code: str | None = Field(default=None, max_length=32)
    notes: str | None = None


class PreviousOrderSummary(BaseModel):
    id: UUID
    status: str
    payment_status: str
    total_amount: str
    created_at: datetime


class CustomerProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    instagram_user_id: str
    full_name: str | None = None
    phone: str | None = None
    city: str | None = None
    address: str | None = None
    postal_code: str | None = None
    notes: str | None = None
    previous_orders: list[PreviousOrderSummary] = Field(default_factory=list)
    preferred_size: str | None = None
    preferred_colors: list[str] = Field(default_factory=list)
    last_successful_size: str | None = None
    last_purchase_at: datetime | None = None
    total_paid_amount: str = "0"
    order_count: int = 0
    is_repeat_customer: bool = False

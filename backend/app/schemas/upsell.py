from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductUpsellCreate(BaseModel):
    source_product_id: UUID
    target_product_id: UUID
    message_template: str | None = None
    is_active: bool = True


class ProductUpsellUpdate(BaseModel):
    message_template: str | None = None
    is_active: bool | None = None


class ProductUpsellRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    source_product_id: UUID
    target_product_id: UUID
    message_template: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UpsellSuggestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    conversation_id: UUID
    order_id: UUID | None = None
    source_product_id: UUID
    target_product_id: UUID
    suggested_text: str
    status: str
    created_at: datetime
    updated_at: datetime

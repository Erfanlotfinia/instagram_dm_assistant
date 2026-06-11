from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VariantCreate(BaseModel):
    color: str | None = Field(default=None, max_length=64)
    normalized_color: str | None = Field(default=None, max_length=64)
    size: str | None = Field(default=None, max_length=64)
    normalized_size: str | None = Field(default=None, max_length=64)
    sku: str = Field(min_length=1, max_length=128)
    price: Decimal = Field(gt=Decimal("0"))
    stock_quantity: int = Field(default=0, ge=0)
    is_active: bool = True


class VariantUpdate(BaseModel):
    color: str | None = Field(default=None, max_length=64)
    normalized_color: str | None = Field(default=None, max_length=64)
    size: str | None = Field(default=None, max_length=64)
    normalized_size: str | None = Field(default=None, max_length=64)
    sku: str | None = Field(default=None, min_length=1, max_length=128)
    price: Decimal | None = Field(default=None, gt=Decimal("0"))
    stock_quantity: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class VariantArchiveRequest(BaseModel):
    force: bool = False
    reason: str | None = Field(default=None, max_length=512)


class VariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    color: str | None
    normalized_color: str | None
    size: str | None
    normalized_size: str | None
    sku: str
    price: Decimal
    stock_quantity: int
    reserved_quantity: int
    available_stock: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_variant(cls, variant) -> "VariantRead":
        data = VariantRead.model_validate(variant)
        return data.model_copy(update={"available_stock": variant.available_stock})

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import ProductStatus


class ProductCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: ProductStatus = ProductStatus.ACTIVE
    base_price: Decimal = Field(gt=Decimal("0"))
    currency: str = Field(default="USD", min_length=3, max_length=3)
    main_image_url: str | None = Field(default=None, max_length=2048)
    category: str | None = Field(default=None, max_length=128)
    size_chart: dict = Field(default_factory=dict)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str) -> str:
        return value.upper()


class ProductUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: ProductStatus | None = None
    base_price: Decimal | None = Field(default=None, gt=Decimal("0"))
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    main_image_url: str | None = Field(default=None, max_length=2048)
    category: str | None = Field(default=None, max_length=128)
    size_chart: dict = Field(default_factory=dict)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    title: str
    description: str | None
    status: ProductStatus
    base_price: Decimal
    currency: str
    main_image_url: str | None
    category: str | None
    size_chart: dict
    created_at: datetime
    updated_at: datetime

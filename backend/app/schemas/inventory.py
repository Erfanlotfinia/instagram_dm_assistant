from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import InventoryMovementType


class InventoryMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_variant_id: UUID
    movement_type: InventoryMovementType
    quantity: int
    reason: str
    reference_type: str | None
    reference_id: str | None
    created_at: datetime


class InventoryReserveRequest(BaseModel):
    quantity: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=512)
    reference_type: str | None = Field(default=None, max_length=64)
    reference_id: str | None = Field(default=None, max_length=128)


class InventoryReleaseRequest(BaseModel):
    quantity: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=512)
    reference_type: str | None = Field(default=None, max_length=64)
    reference_id: str | None = Field(default=None, max_length=128)

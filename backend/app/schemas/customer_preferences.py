from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CustomerPreferencesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    preferred_size: str | None = None
    preferred_colors: list[str] = Field(default_factory=list)
    preferred_categories: list[str] = Field(default_factory=list)
    last_successful_size: str | None = None
    last_successful_city: str | None = None
    last_successful_address_id: UUID | None = None
    updated_at: datetime

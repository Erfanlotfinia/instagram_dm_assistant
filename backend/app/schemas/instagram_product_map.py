from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import ConfidenceSource
from app.schemas.product import ProductRead


class InstagramProductMapCreate(BaseModel):
    instagram_account_id: UUID
    instagram_post_url: str = Field(min_length=1, max_length=2048)
    instagram_media_id: str | None = Field(default=None, max_length=128)
    product_id: UUID
    confidence_source: ConfidenceSource = ConfidenceSource.MANUAL
    is_active: bool = True


class InstagramProductMapUpdate(BaseModel):
    instagram_post_url: str | None = Field(default=None, min_length=1, max_length=2048)
    instagram_media_id: str | None = Field(default=None, max_length=128)
    product_id: UUID | None = None
    confidence_source: ConfidenceSource | None = None
    is_active: bool | None = None


class InstagramProductMapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    instagram_account_id: UUID
    instagram_media_id: str | None
    instagram_post_url: str
    product_id: UUID
    confidence_source: ConfidenceSource
    is_active: bool
    created_at: datetime
    updated_at: datetime


class InstagramProductMapDetailRead(InstagramProductMapRead):
    product: ProductRead


class ResolveInstagramProductRequest(BaseModel):
    instagram_post_url: str | None = Field(default=None, max_length=2048)
    instagram_media_id: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def require_url_or_media_id(self) -> "ResolveInstagramProductRequest":
        if not self.instagram_post_url and not self.instagram_media_id:
            raise ValueError("Either instagram_post_url or instagram_media_id is required")
        return self


class ResolveInstagramProductResponse(BaseModel):
    product: ProductRead | None = None
    map_id: UUID | None = None
    confidence_source: ConfidenceSource | None = None

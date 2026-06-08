from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import HandoffMode, ShopStatus, UserRole


class ShopCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255)
    default_currency: str = Field(default="USD", min_length=3, max_length=3)


class ShopUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)


class ShopAgentSettings(BaseModel):
    auto_reply_enabled: bool = True
    intent_confidence_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    slots_confidence_threshold: float = Field(default=0.60, ge=0.0, le=1.0)
    product_confidence_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    address_confidence_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    auto_send_confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    auto_send_enabled: bool = True
    preview_required_for_low_confidence: bool = True
    preview_required_for_first_24h: bool = True
    high_value_order_threshold: float = Field(default=500.0, ge=0.0)
    handoff_mode: HandoffMode = HandoffMode.AUTOMATIC
    default_language: str = Field(default="fa", min_length=2, max_length=8)
    low_stock_threshold: int = Field(default=5, ge=0)


class ShopRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    status: ShopStatus
    default_currency: str
    agent_settings: ShopAgentSettings = Field(default_factory=ShopAgentSettings)
    created_at: datetime
    updated_at: datetime
    onboarding_flags: dict = Field(default_factory=dict)


class ShopMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    user_id: UUID
    role: UserRole
    created_at: datetime
    full_name: str
    email: str


class InstagramAccountStatusSummary(BaseModel):
    id: UUID
    username: str
    status: str
    webhook_enabled: bool
    token_expires_at: datetime | None = None


class ShopSettingsRead(BaseModel):
    shop: ShopRead
    instagram_accounts: list[InstagramAccountStatusSummary] = Field(default_factory=list)
    webhook_active: bool = False


class OnboardingStepStatus(BaseModel):
    key: str
    label: str
    completed: bool
    href: str


class OnboardingStatusRead(BaseModel):
    shop_id: UUID
    completed_steps: list[str] = Field(default_factory=list)
    missing_steps: list[str] = Field(default_factory=list)
    progress_percent: int
    next_recommended_action: str
    steps: list[OnboardingStepStatus] = Field(default_factory=list)
    total_steps: int = 0

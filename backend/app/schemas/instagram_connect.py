from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.enums import ChannelConnectionSessionStatus


class InstagramConnectStartResponse(BaseModel):
    authorization_url: str
    session_id: UUID
    expires_at: datetime


class InstagramCandidateAccountRead(BaseModel):
    page_id: str
    page_name: str
    instagram_business_account_id: str
    instagram_username: str | None = None
    instagram_profile_picture_url: str | None = None


class InstagramConnectSessionRead(BaseModel):
    id: UUID
    shop_id: UUID
    status: ChannelConnectionSessionStatus
    expires_at: datetime
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
    candidate_accounts: list[InstagramCandidateAccountRead] = Field(default_factory=list)
    channel_account_id: UUID | None = None


class InstagramSelectAccountRequest(BaseModel):
    page_id: str
    instagram_business_account_id: str


class InstagramReadinessRead(BaseModel):
    meta_app_id_configured: bool
    meta_app_secret_configured: bool
    oauth_redirect_uri: str
    data_deletion_callback_configured: bool = False
    privacy_policy_url: str | None = None
    required_scopes: list[str]
    app_mode: str = "unknown"
    webhook_callback_reachable: bool
    webhook_callback_url: str
    app_review_status: str = "manual_check_required"

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import SuggestedReplyGeneratedBy, SuggestedReplyStatus


class SuggestedReplyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID
    conversation_id: UUID
    message_id: UUID | None = None
    suggested_text: str
    status: SuggestedReplyStatus
    generated_by: SuggestedReplyGeneratedBy
    approved_by_user_id: UUID | None = None
    edited_text: str | None = None
    reason: str | None = None
    created_at: datetime
    updated_at: datetime


class SuggestedReplyEditAndSend(BaseModel):
    edited_text: str = Field(min_length=1, max_length=4000)


class SuggestedReplyReject(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)

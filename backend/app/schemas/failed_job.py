from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import FailedJobStatus


class FailedJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID | None = None
    queue_name: str
    job_type: str
    payload: dict
    error_message: str | None = None
    traceback: str | None = None
    retry_count: int
    max_retries: int
    status: FailedJobStatus
    created_at: datetime
    updated_at: datetime


class FailedJobListResponse(BaseModel):
    items: list[FailedJobRead]
    total: int
    page: int
    page_size: int


class FailedJobActionResponse(BaseModel):
    id: UUID
    status: FailedJobStatus
    message: str = Field(default="ok")

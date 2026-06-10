from __future__ import annotations

from datetime import datetime
from uuid import UUID

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.core.log_masking import mask_value

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

    @field_serializer("payload")
    def serialize_payload(self, payload: dict) -> dict[str, Any]:
        return mask_value(None, payload)

    @field_serializer("traceback")
    def serialize_traceback(self, traceback: str | None) -> str | None:
        return mask_value("traceback", traceback) if traceback is not None else None
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

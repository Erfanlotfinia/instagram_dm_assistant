from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.log_masking import mask_value

from app.domain.enums import FailedJobStatus


class FailedJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shop_id: UUID | None = None
    queue_name: str
    job_type: str
    redacted_payload: dict[str, Any]
    error_message: str | None = None
    traceback: str | None = None
    retry_count: int
    max_retries: int
    status: FailedJobStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_job(cls, job: Any) -> FailedJobRead:
        return cls(
            id=job.id,
            shop_id=job.shop_id,
            queue_name=job.queue_name,
            job_type=job.job_type,
            redacted_payload=mask_value(None, job.payload or {}),
            error_message=job.error_message,
            traceback=mask_value("traceback", job.traceback) if job.traceback else None,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
            status=job.status,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )


class FailedJobListResponse(BaseModel):
    items: list[FailedJobRead]
    total: int
    page: int
    page_size: int


class FailedJobActionResponse(BaseModel):
    id: UUID
    status: FailedJobStatus
    message: str = Field(default="ok")

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.domain.enums import FailedJobStatus
from app.domain.models import User
from app.schemas.failed_job import FailedJobActionResponse, FailedJobListResponse
from app.services.failed_job_service import FailedJobService

router = APIRouter(prefix="/failed-jobs", tags=["failed-jobs"])


@router.get("", response_model=FailedJobListResponse)
def list_accessible_failed_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
    shop_id: UUID | None = None,
    unscoped_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status: FailedJobStatus | None = Query(default=FailedJobStatus.FAILED),
    queue_name: str | None = None,
    job_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> FailedJobListResponse:
    return FailedJobService(db).list_accessible_jobs(
        current_user,
        shop_id=shop_id,
        unscoped_only=unscoped_only,
        page=page,
        page_size=page_size,
        status_filter=status,
        queue_name=queue_name,
        job_type=job_type,
        date_from=date_from,
        date_to=date_to,
    )


@router.post("/{job_id}/retry", response_model=FailedJobActionResponse)
def retry_accessible_failed_job(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> FailedJobActionResponse:
    return FailedJobService(db).retry_accessible_job(job_id, current_user)


@router.post("/{job_id}/ignore", response_model=FailedJobActionResponse)
def ignore_accessible_failed_job(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db_session)],
) -> FailedJobActionResponse:
    return FailedJobService(db).ignore_accessible_job(job_id, current_user)

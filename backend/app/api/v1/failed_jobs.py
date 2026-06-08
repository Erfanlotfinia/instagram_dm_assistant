from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_shop_membership, require_shop_role
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import ShopMember, User
from app.schemas.failed_job import FailedJobActionResponse, FailedJobListResponse
from app.services.failed_job_service import FailedJobService

router = APIRouter(prefix="/shops/{shop_id}/failed-jobs", tags=["failed-jobs"])


@router.get("", response_model=FailedJobListResponse)
def list_failed_jobs(
    shop_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(get_shop_membership)],
    db: Annotated[Session, Depends(get_db_session)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> FailedJobListResponse:
    return FailedJobService(db).list_jobs(shop_id, current_user, page=page, page_size=page_size)


@router.post("/{job_id}/retry", response_model=FailedJobActionResponse)
def retry_failed_job(
    shop_id: UUID,
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> FailedJobActionResponse:
    return FailedJobService(db).retry_job(shop_id, job_id, current_user)


@router.post("/{job_id}/ignore", response_model=FailedJobActionResponse)
def ignore_failed_job(
    shop_id: UUID,
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    _membership: Annotated[ShopMember, Depends(require_shop_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> FailedJobActionResponse:
    return FailedJobService(db).ignore_job(shop_id, job_id, current_user)

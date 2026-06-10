from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_minimum_role
from app.core.log_masking import mask_value
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import User
from app.services.failed_job_service import FailedJobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _mask_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return mask_value(None, payload)


@router.get("/failed", deprecated=True)
def list_failed_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    _admin: Annotated[User, Depends(require_minimum_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> list[dict[str, Any]]:
    """Deprecated compatibility endpoint.

    Use /api/v1/failed-jobs instead. This endpoint is intentionally restricted
    to admins and only returns jobs scoped to shops the user can access.
    """
    response = FailedJobService(db).list_accessible_jobs(current_user, page=1, page_size=100)
    return [
        {
            "id": str(job.id),
            "shop_id": str(job.shop_id) if job.shop_id else None,
            "queue_name": job.queue_name,
            "job_type": job.job_type,
            "payload": _mask_payload(job.payload),
            "error_message": job.error_message,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
            "created_at": job.created_at,
            "status": job.status.value,
        }
        for job in response.items
    ]

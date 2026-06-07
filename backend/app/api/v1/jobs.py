from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.domain.models import FailedJob, User

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/failed")
def list_failed_jobs(_user: Annotated[User, Depends(get_current_user)], db: Annotated[Session, Depends(get_db_session)]) -> list[dict]:
    jobs = db.scalars(select(FailedJob).where(FailedJob.resolved.is_(False)).order_by(FailedJob.created_at.desc()).limit(100)).all()
    return [
        {
            "id": str(job.id),
            "queue_name": job.queue_name,
            "job_type": job.job_type,
            "payload": job.payload,
            "error_message": job.error_message,
            "retry_count": job.retry_count,
            "max_retries": job.max_retries,
            "created_at": job.created_at,
        }
        for job in jobs
    ]

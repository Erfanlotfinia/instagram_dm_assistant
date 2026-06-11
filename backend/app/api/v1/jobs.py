from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_minimum_role
from app.db.session import get_db_session
from app.domain.enums import UserRole
from app.domain.models import User

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/failed", deprecated=True)
def list_failed_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    _admin: Annotated[User, Depends(require_minimum_role(UserRole.ADMIN))],
    db: Annotated[Session, Depends(get_db_session)],
) -> None:
    """Deprecated. Use /api/v1/failed-jobs or /api/v1/shops/{shop_id}/failed-jobs."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="This endpoint is removed. Use /api/v1/failed-jobs instead.",
    )

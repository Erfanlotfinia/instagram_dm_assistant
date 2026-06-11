from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domain.enums import FailedJobStatus
from app.domain.models import FailedJob


def _apply_filters(
    stmt,
    *,
    status: FailedJobStatus | None,
    queue_name: str | None,
    job_type: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
):
    if status is not None:
        stmt = stmt.where(FailedJob.status == status)
    if queue_name:
        stmt = stmt.where(FailedJob.queue_name == queue_name)
    if job_type:
        stmt = stmt.where(FailedJob.job_type == job_type)
    if date_from is not None:
        stmt = stmt.where(FailedJob.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(FailedJob.created_at <= date_to)
    return stmt


class FailedJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, job: FailedJob) -> FailedJob:
        self.db.add(job)
        self.db.flush()
        return job

    def get_for_shop(self, shop_id: UUID, job_id: UUID) -> FailedJob | None:
        return self.db.scalar(
            select(FailedJob).where(
                FailedJob.id == job_id,
                or_(FailedJob.shop_id == shop_id, FailedJob.shop_id.is_(None)),
            )
        )

    def get_if_accessible(self, job_id: UUID, shop_ids: list[UUID]) -> FailedJob | None:
        if not shop_ids:
            return None
        return self.db.scalar(
            select(FailedJob).where(
                FailedJob.id == job_id,
                or_(FailedJob.shop_id.in_(shop_ids), FailedJob.shop_id.is_(None)),
            )
        )

    def list_for_shop(
        self,
        shop_id: UUID,
        *,
        status: FailedJobStatus | None = FailedJobStatus.FAILED,
        queue_name: str | None = None,
        job_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[FailedJob], int]:
        shop_scope = or_(FailedJob.shop_id == shop_id, FailedJob.shop_id.is_(None))
        stmt = _apply_filters(
            select(FailedJob).where(shop_scope),
            status=status,
            queue_name=queue_name,
            job_type=job_type,
            date_from=date_from,
            date_to=date_to,
        )
        count_stmt = _apply_filters(
            select(func.count(FailedJob.id)).where(shop_scope),
            status=status,
            queue_name=queue_name,
            job_type=job_type,
            date_from=date_from,
            date_to=date_to,
        )
        total = self.db.scalar(count_stmt) or 0
        items = list(
            self.db.scalars(
                stmt.order_by(FailedJob.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        return items, total

    def list_accessible(
        self,
        shop_ids: list[UUID],
        *,
        shop_filter: UUID | None = None,
        unscoped_only: bool = False,
        status: FailedJobStatus | None = FailedJobStatus.FAILED,
        queue_name: str | None = None,
        job_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[FailedJob], int]:
        if unscoped_only:
            scope = FailedJob.shop_id.is_(None)
        elif shop_filter is not None:
            scope = FailedJob.shop_id == shop_filter
        elif shop_ids:
            scope = or_(FailedJob.shop_id.in_(shop_ids), FailedJob.shop_id.is_(None))
        else:
            scope = FailedJob.shop_id.is_(None)

        stmt = _apply_filters(
            select(FailedJob).where(scope),
            status=status,
            queue_name=queue_name,
            job_type=job_type,
            date_from=date_from,
            date_to=date_to,
        )
        count_stmt = _apply_filters(
            select(func.count(FailedJob.id)).where(scope),
            status=status,
            queue_name=queue_name,
            job_type=job_type,
            date_from=date_from,
            date_to=date_to,
        )
        total = self.db.scalar(count_stmt) or 0
        items = list(
            self.db.scalars(
                stmt.order_by(FailedJob.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )
        return items, total

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, job: FailedJob) -> None:
        self.db.refresh(job)

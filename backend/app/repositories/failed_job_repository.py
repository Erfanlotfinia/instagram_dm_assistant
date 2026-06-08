from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.domain.enums import FailedJobStatus
from app.domain.models import FailedJob


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
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[FailedJob], int]:
        shop_scope = or_(FailedJob.shop_id == shop_id, FailedJob.shop_id.is_(None))
        stmt = select(FailedJob).where(shop_scope)
        if status is not None:
            stmt = stmt.where(FailedJob.status == status)
        count_stmt = select(func.count(FailedJob.id)).where(shop_scope)
        if status is not None:
            count_stmt = count_stmt.where(FailedJob.status == status)
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

        stmt = select(FailedJob).where(scope)
        count_stmt = select(func.count(FailedJob.id)).where(scope)
        if status is not None:
            stmt = stmt.where(FailedJob.status == status)
            count_stmt = count_stmt.where(FailedJob.status == status)
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

from __future__ import annotations

import traceback
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import FailedJobStatus, PilotEventSeverity, UserRole
from app.domain.models import FailedJob, ShopMember, User
from app.integrations.rabbitmq import RabbitMQPublisher
from app.repositories.failed_job_repository import FailedJobRepository
from app.schemas.failed_job import FailedJobActionResponse, FailedJobListResponse, FailedJobRead
from app.schemas.queue_events import MessageReceivedJob
from app.services.audit_service import AuditService
from app.services.shop_service import ShopService
from app.services.pilot_service import PilotService


class FailedJobService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.repo = FailedJobRepository(db)
        self.shop_service = ShopService(db)

    @staticmethod
    def record_failure(
        db: Session,
        *,
        queue_name: str,
        job_type: str,
        payload: dict[str, Any],
        error_message: str,
        retry_count: int = 0,
        tb: str | None = None,
        settings: Settings | None = None,
    ) -> FailedJob:
        settings = settings or get_settings()
        shop_id: UUID | None = None
        try:
            shop_id = MessageReceivedJob.model_validate(payload).shop_id
        except Exception:  # noqa: BLE001
            raw_shop = payload.get("shop_id")
            if raw_shop:
                shop_id = UUID(str(raw_shop))

        job = FailedJob(
            shop_id=shop_id,
            queue_name=queue_name,
            job_type=job_type,
            payload=payload,
            error_message=error_message,
            traceback=tb,
            retry_count=retry_count,
            max_retries=settings.rabbitmq_max_retries,
            status=FailedJobStatus.FAILED,
            resolved=False,
        )
        repo = FailedJobRepository(db)
        created = repo.create(job)
        if shop_id is not None:
            PilotService(db).log_event(
                shop_id,
                "failed_job",
                PilotEventSeverity.ERROR,
                "Worker job failed",
                description=error_message,
                metadata={"queue_name": queue_name, "job_type": job_type, "retry_count": retry_count},
            )
        repo.commit()
        return created

    def list_jobs(
        self,
        shop_id: UUID,
        user: User,
        *,
        page: int = 1,
        page_size: int = 25,
        status_filter: FailedJobStatus | None = FailedJobStatus.FAILED,
        queue_name: str | None = None,
        job_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> FailedJobListResponse:
        self._require_admin(shop_id, user)
        items, total = self.repo.list_for_shop(
            shop_id,
            page=page,
            page_size=page_size,
            status=status_filter,
            queue_name=queue_name,
            job_type=job_type,
            date_from=date_from,
            date_to=date_to,
        )
        self._audit_viewed(shop_id, user, total)
        return self._to_list_response(items, total, page, page_size)

    def list_accessible_jobs(
        self,
        user: User,
        *,
        shop_id: UUID | None = None,
        unscoped_only: bool = False,
        page: int = 1,
        page_size: int = 25,
        status_filter: FailedJobStatus | None = FailedJobStatus.FAILED,
        queue_name: str | None = None,
        job_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> FailedJobListResponse:
        admin_shop_ids = self._admin_shop_ids(user)
        if not admin_shop_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires admin role or higher")
        if shop_id is not None:
            if shop_id not in admin_shop_ids:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this shop")
        if unscoped_only and shop_id is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Use either shop_id or unscoped_only, not both",
            )
        items, total = self.repo.list_accessible(
            admin_shop_ids,
            shop_filter=shop_id,
            unscoped_only=unscoped_only,
            page=page,
            page_size=page_size,
            status=status_filter,
            queue_name=queue_name,
            job_type=job_type,
            date_from=date_from,
            date_to=date_to,
        )
        audit_shop_id = shop_id or admin_shop_ids[0]
        self._audit_viewed(audit_shop_id, user, total)
        return self._to_list_response(items, total, page, page_size)

    def retry_job(self, shop_id: UUID, job_id: UUID, user: User) -> FailedJobActionResponse:
        self._require_admin(shop_id, user)
        job = self._get_job_or_404(shop_id, job_id)
        return self._retry_job(job, audit_shop_id=job.shop_id or shop_id, user=user)

    def retry_accessible_job(self, job_id: UUID, user: User) -> FailedJobActionResponse:
        job = self._get_accessible_job_or_404(job_id, user)
        audit_shop_id = self._audit_shop_for_job(user, job)
        self._require_admin(audit_shop_id, user)
        return self._retry_job(job, audit_shop_id=audit_shop_id, user=user)

    def ignore_job(self, shop_id: UUID, job_id: UUID, user: User) -> FailedJobActionResponse:
        self._require_admin(shop_id, user)
        job = self._get_job_or_404(shop_id, job_id)
        return self._ignore_job(job, audit_shop_id=job.shop_id or shop_id, user=user)

    def ignore_accessible_job(self, job_id: UUID, user: User) -> FailedJobActionResponse:
        job = self._get_accessible_job_or_404(job_id, user)
        audit_shop_id = self._audit_shop_for_job(user, job)
        self._require_admin(audit_shop_id, user)
        return self._ignore_job(job, audit_shop_id=audit_shop_id, user=user)

    def _retry_job(self, job: FailedJob, *, audit_shop_id: UUID, user: User) -> FailedJobActionResponse:
        if job.status != FailedJobStatus.FAILED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only failed jobs can be retried")

        publisher = RabbitMQPublisher(self.settings)
        try:
            publisher.publish(self.settings.rabbitmq_queue_message_received, job.payload, retry_count=0)
        finally:
            publisher.close()

        job.status = FailedJobStatus.RETRIED
        job.resolved = True
        self.repo.commit()
        self.repo.refresh(job)
        AuditService(self.db).log(
            action="failed_job_retried",
            entity_type="failed_job",
            shop_id=audit_shop_id,
            actor_user_id=user.id,
            entity_id=str(job.id),
            metadata={"queue_name": job.queue_name, "job_type": job.job_type},
        )
        self.repo.commit()
        return FailedJobActionResponse(id=job.id, status=job.status, message="Job requeued")

    def _ignore_job(self, job: FailedJob, *, audit_shop_id: UUID, user: User) -> FailedJobActionResponse:
        if job.status != FailedJobStatus.FAILED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only failed jobs can be ignored")

        job.status = FailedJobStatus.IGNORED
        job.resolved = True
        self.repo.commit()
        self.repo.refresh(job)
        AuditService(self.db).log(
            action="failed_job_ignored",
            entity_type="failed_job",
            shop_id=audit_shop_id,
            actor_user_id=user.id,
            entity_id=str(job.id),
            metadata={"queue_name": job.queue_name, "job_type": job.job_type},
        )
        self.repo.commit()
        return FailedJobActionResponse(id=job.id, status=job.status, message="Job ignored")

    def _to_list_response(
        self,
        items: list[FailedJob],
        total: int,
        page: int,
        page_size: int,
    ) -> FailedJobListResponse:
        return FailedJobListResponse(
            items=[FailedJobRead.from_job(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    def _audit_viewed(self, shop_id: UUID, user: User, total: int) -> None:
        AuditService(self.db).log(
            action="failed_job_viewed",
            entity_type="failed_job",
            shop_id=shop_id,
            actor_user_id=user.id,
            metadata={"total": total},
        )
        self.repo.commit()

    def _accessible_shop_ids(self, user: User) -> list[UUID]:
        return list(
            self.db.scalars(select(ShopMember.shop_id).where(ShopMember.user_id == user.id)).all()
        )

    def _admin_shop_ids(self, user: User) -> list[UUID]:
        return list(
            self.db.scalars(
                select(ShopMember.shop_id).where(
                    ShopMember.user_id == user.id,
                    ShopMember.role.in_([UserRole.OWNER, UserRole.ADMIN]),
                )
            ).all()
        )

    def _get_accessible_job_or_404(self, job_id: UUID, user: User) -> FailedJob:
        job = self.repo.get_if_accessible(job_id, self._accessible_shop_ids(user))
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Failed job not found")
        return job

    def _audit_shop_for_job(self, user: User, job: FailedJob) -> UUID:
        if job.shop_id is not None:
            return job.shop_id
        memberships = self.db.scalars(select(ShopMember).where(ShopMember.user_id == user.id)).all()
        for membership in memberships:
            if membership.role in {UserRole.OWNER, UserRole.ADMIN}:
                return membership.shop_id
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires admin role or higher")

    def _get_job_or_404(self, shop_id: UUID, job_id: UUID) -> FailedJob:
        job = self.repo.get_for_shop(shop_id, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Failed job not found")
        return job

    def _require_admin(self, shop_id: UUID, user: User) -> None:
        membership = self.shop_service.get_membership(shop_id, user.id)
        if membership is None or membership.role not in {UserRole.OWNER, UserRole.ADMIN}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires admin role or higher")


def format_traceback(exc: BaseException) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))

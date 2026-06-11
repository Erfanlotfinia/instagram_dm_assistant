from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import OutboxEventStatus
from app.domain.models import OutboxEvent


class OutboxEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, event: OutboxEvent) -> OutboxEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def claim_pending(self, *, limit: int = 50) -> list[OutboxEvent]:
        now = datetime.now(UTC)
        stmt = (
            select(OutboxEvent)
            .where(
                OutboxEvent.status == OutboxEventStatus.PENDING,
                (OutboxEvent.next_attempt_at.is_(None)) | (OutboxEvent.next_attempt_at <= now),
            )
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(self.db.scalars(stmt).all())

    def mark_published(self, event: OutboxEvent) -> None:
        event.status = OutboxEventStatus.PUBLISHED
        event.published_at = datetime.now(UTC)
        event.last_error = None

    def mark_failed(self, event: OutboxEvent, error: str, *, retry_delay_seconds: int) -> None:
        event.retry_count += 1
        event.last_error = error[:2000]
        event.next_attempt_at = datetime.now(UTC) + timedelta(seconds=retry_delay_seconds)
        if event.retry_count >= 10:
            event.status = OutboxEventStatus.FAILED

    def get_by_id(self, event_id: UUID) -> OutboxEvent | None:
        return self.db.get(OutboxEvent, event_id)

    def commit(self) -> None:
        self.db.commit()

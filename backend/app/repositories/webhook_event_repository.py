from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import WebhookProcessingStatus, WebhookProvider
from app.domain.models import WebhookEvent


class WebhookEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, event: WebhookEvent) -> WebhookEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def get_by_id(self, event_id: UUID) -> WebhookEvent | None:
        return self.db.get(WebhookEvent, event_id)

    def get_by_idempotency_key(
        self, provider: WebhookProvider, idempotency_key: str
    ) -> WebhookEvent | None:
        stmt = select(WebhookEvent).where(
            WebhookEvent.provider == provider,
            WebhookEvent.idempotency_key == idempotency_key,
        )
        return self.db.scalar(stmt)

    def update_status(
        self,
        event: WebhookEvent,
        status: WebhookProcessingStatus,
        error_message: str | None = None,
    ) -> WebhookEvent:
        event.processing_status = status
        if error_message is not None:
            event.error_message = error_message
        self.db.flush()
        return event

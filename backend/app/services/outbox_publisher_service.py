from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import OutboxEventStatus
from app.integrations.rabbitmq import RabbitMQPublisher
from app.repositories.outbox_event_repository import OutboxEventRepository

logger = logging.getLogger(__name__)


class OutboxPublisherService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.repo = OutboxEventRepository(db)

    def publish_pending(self, *, batch_size: int = 50) -> int:
        events = self.repo.claim_pending(limit=batch_size)
        if not events:
            return 0

        publisher = RabbitMQPublisher(self.settings)
        published = 0
        try:
            for event in events:
                if event.status != OutboxEventStatus.PENDING:
                    continue
                try:
                    queue_name, payload = self._resolve_target(event.payload)
                    publisher.publish(queue_name, payload)
                    self.repo.mark_published(event)
                    published += 1
                except Exception as exc:  # noqa: BLE001
                    delay = min(300, 5 * (2 ** min(event.retry_count, 6)))
                    self.repo.mark_failed(event, str(exc), retry_delay_seconds=delay)
                    logger.warning(
                        "Outbox publish failed event_id=%s retry=%s error=%s",
                        event.id,
                        event.retry_count,
                        exc,
                    )
            self.repo.commit()
        finally:
            publisher.close()
        return published

    @staticmethod
    def _resolve_target(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        queue_name = payload.get("_queue_name")
        body = payload.get("_body")
        if not queue_name or not isinstance(body, dict):
            raise ValueError("Outbox payload must include _queue_name and _body")
        return str(queue_name), body

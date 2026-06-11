from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.domain.enums import WebhookProcessingStatus
from app.integrations.redis_lock import ConversationLockService
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.webhook_event_repository import WebhookEventRepository
from app.schemas.queue_events import InvalidJobPayloadError, MessageReceivedJob, validate_message_received_payload
from app.services.conversation_orchestrator import ConversationOrchestrator

logger = logging.getLogger(__name__)

__all__ = [
    "ConversationLockedError",
    "InvalidJobPayloadError",
    "MessageConsumer",
    "handle_delivery",
    "parse_delivery_body",
    "validate_message_received_payload",
]


class ConversationLockedError(Exception):
    """Raised when a conversation lock cannot be acquired."""


def parse_delivery_body(body: bytes) -> dict:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidJobPayloadError("Job body is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise InvalidJobPayloadError("Job body must be a JSON object")
    return payload


class MessageConsumer:
    def __init__(
        self,
        db: Session,
        lock_service: ConversationLockService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.lock_service = lock_service or ConversationLockService(self.settings)
        self.messages = MessageRepository(db)
        self.conversations = ConversationRepository(db)
        self.webhook_events = WebhookEventRepository(db)

    def process_job(self, payload: dict) -> bool:
        job = validate_message_received_payload(payload)
        lock_token = self.lock_service.acquire(str(job.conversation_id))
        if lock_token is None:
            logger.info("Conversation %s is locked; requeueing job", job.conversation_id)
            raise ConversationLockedError(f"Conversation {job.conversation_id} is locked")

        try:
            return self._handle_job(job)
        finally:
            self.lock_service.release(str(job.conversation_id), lock_token)

    def _handle_job(self, job: MessageReceivedJob) -> bool:
        message = self.messages.get_by_id(job.message_id)
        if message is None:
            logger.warning("Message %s not found for job", job.message_id)
            return False

        conversation = self.conversations.get_by_id(job.conversation_id)
        if conversation is None:
            logger.warning("Conversation %s not found for job", job.conversation_id)
            return False

        logger.info(
            "Message %s ready for agent processing (conversation=%s, shop=%s)",
            job.message_id,
            job.conversation_id,
            job.shop_id,
        )

        ConversationOrchestrator(self.db, settings=self.settings).process_inbound_message(
            job.conversation_id,
            job.message_id,
        )

        if job.webhook_event_id is not None:
            webhook_event = self.webhook_events.get_by_id(job.webhook_event_id)
            if webhook_event is not None:
                if webhook_event.processing_status == WebhookProcessingStatus.PROCESSED:
                    logger.info("Webhook event %s already processed", job.webhook_event_id)
                    return True
                self.webhook_events.update_status(webhook_event, WebhookProcessingStatus.PROCESSED)

        self.db.commit()
        return True


def handle_delivery(body: bytes) -> bool:
    payload = parse_delivery_body(body)
    db = SessionLocal()
    try:
        return MessageConsumer(db).process_job(payload)
    except ConversationLockedError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to process RabbitMQ job")
        raise
    finally:
        db.close()

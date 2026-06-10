from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.request_context import get_request_id
from app.domain.enums import (
    ConversationState,
    MessageChannel,
    MessageDirection,
    MessageType,
    WebhookDedupeOutcome,
    WebhookProcessingStatus,
    WebhookProvider,
)
from app.domain.models import Conversation, Customer, Message, WebhookEvent
from app.integrations.instagram_webhook import ParsedInstagramMessage, parse_instagram_webhook_payload
from app.integrations.rabbitmq import MessagePublisher, RabbitMQPublisher
from app.integrations.redis_cache import RedisCacheService
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.instagram_account_repository import InstagramAccountRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.webhook_event_repository import WebhookEventRepository
from app.schemas.queue_events import MessageReceivedJob
from app.schemas.webhook import WebhookAckResponse, WebhookIgnoredResponse

logger = logging.getLogger(__name__)

MESSAGE_TYPE_MAP = {
    "text": MessageType.TEXT,
    "shared_post": MessageType.SHARED_POST,
    "attachment": MessageType.ATTACHMENT,
}


def compute_webhook_idempotency_key(payload: dict[str, Any]) -> str:
    entry_ids: list[str] = []
    for entry in payload.get("entry", []):
        entry_id = entry.get("id")
        if entry_id:
            entry_ids.append(str(entry_id))
        for item in entry.get("messaging", []) + entry.get("changes", []):
            mid = item.get("message", {}).get("mid") or item.get("value", {}).get("message", {}).get("mid")
            if mid:
                entry_ids.append(str(mid))
    if entry_ids:
        return f"meta:{':'.join(entry_ids)}"
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(body.encode()).hexdigest()}"


class WebhookIngestionService:
    def __init__(
        self,
        db: Session,
        publisher: MessagePublisher | None = None,
        settings: Settings | None = None,
        cache: RedisCacheService | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.publisher = publisher or RabbitMQPublisher(self.settings)
        self.cache = cache or RedisCacheService(self.settings)
        self.webhook_events = WebhookEventRepository(db)
        self.accounts = InstagramAccountRepository(db)
        self.customers = CustomerRepository(db)
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)

    def handle_instagram_payload(
        self, payload: dict[str, Any], raw_body: bytes | None = None
    ) -> WebhookAckResponse | WebhookIgnoredResponse:
        parsed_messages = parse_instagram_webhook_payload(payload)
        if not parsed_messages:
            return WebhookIgnoredResponse(reason="no_messaging_events")

        idempotency_key = compute_webhook_idempotency_key(payload)
        trace_id = get_request_id()

        if not self.cache.try_acquire_idempotency(idempotency_key):
            logger.info("Duplicate webhook (redis) key=%s trace_id=%s", idempotency_key, trace_id)
            return WebhookAckResponse(dedupe_outcome=WebhookDedupeOutcome.DUPLICATE.value)

        existing_event = self.webhook_events.get_by_idempotency_key(
            WebhookProvider.INSTAGRAM, idempotency_key
        )
        if existing_event is not None:
            logger.info("Duplicate webhook (db) key=%s trace_id=%s", idempotency_key, trace_id)
            return WebhookAckResponse(dedupe_outcome=WebhookDedupeOutcome.DUPLICATE.value)

        webhook_event = WebhookEvent(
            provider=WebhookProvider.INSTAGRAM,
            event_type="instagram.messaging",
            raw_payload=payload,
            processing_status=WebhookProcessingStatus.RECEIVED,
            idempotency_key=idempotency_key,
            trace_id=trace_id,
            dedupe_outcome=WebhookDedupeOutcome.PROCESSED,
        )
        try:
            self.webhook_events.create(webhook_event)
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            logger.info("Duplicate webhook (integrity) key=%s", idempotency_key)
            return WebhookAckResponse(dedupe_outcome=WebhookDedupeOutcome.DUPLICATE.value)

        jobs: list[MessageReceivedJob] = []
        errors: list[str] = []

        for parsed in parsed_messages:
            try:
                job = self._process_message(webhook_event.id, parsed)
                if job is not None:
                    jobs.append(job)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to process Instagram message %s", parsed.message_id)
                errors.append(str(exc))

        queued_count = len(jobs)
        if queued_count > 0:
            self.webhook_events.update_status(webhook_event, WebhookProcessingStatus.QUEUED)
        elif errors:
            self.webhook_events.update_status(
                webhook_event,
                WebhookProcessingStatus.FAILED,
                error_message="; ".join(errors),
            )
            webhook_event.dedupe_outcome = WebhookDedupeOutcome.IGNORED

        self.db.commit()

        for job in jobs:
            self.publisher.publish(
                self.settings.rabbitmq_queue_message_received,
                job.model_dump(mode="json"),
            )
        return WebhookAckResponse(dedupe_outcome=webhook_event.dedupe_outcome.value)

    def _process_message(self, webhook_event_id: UUID, parsed: ParsedInstagramMessage) -> MessageReceivedJob | None:
        existing = self.messages.get_by_instagram_message_id(parsed.message_id)
        if existing is not None:
            logger.info("Duplicate Instagram message id %s ignored", parsed.message_id)
            return None

        account = self.accounts.get_by_ig_user_id(parsed.recipient_id)
        if account is None:
            logger.warning("No Instagram account for recipient %s", parsed.recipient_id)
            return None

        customer = self.customers.get_by_instagram_user_id(account.shop_id, parsed.sender_id)
        if customer is None:
            customer = self.customers.create(
                Customer(
                    shop_id=account.shop_id,
                    instagram_user_id=parsed.sender_id,
                )
            )

        conversation = self.conversations.get_open_for_participants(
            account.shop_id,
            account.id,
            customer.id,
        )
        if conversation is None:
            conversation = self.conversations.create(
                Conversation(
                    shop_id=account.shop_id,
                    instagram_account_id=account.id,
                    customer_id=customer.id,
                    state=ConversationState.OPEN,
                )
            )

        message_type = MESSAGE_TYPE_MAP.get(parsed.message_type, MessageType.TEXT)
        display_text = parsed.text
        if display_text is None and parsed.shared_post_url:
            display_text = parsed.shared_post_url
        elif display_text is None and parsed.attachment_url:
            display_text = parsed.attachment_url

        raw_payload = {
            **parsed.messaging_event,
            "_meta": {
                "webhook_event_id": str(webhook_event_id),
                "attachment_url": parsed.attachment_url,
                "shared_post_url": parsed.shared_post_url,
            },
        }

        message = Message(
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
            channel=MessageChannel.INSTAGRAM,
            instagram_message_id=parsed.message_id,
            message_type=message_type,
            text=display_text,
            raw_payload=raw_payload,
        )

        try:
            with self.db.begin_nested():
                self.messages.create(message)
        except IntegrityError:
            logger.info("Race duplicate for Instagram message id %s", parsed.message_id)
            return None

        message_time = parsed.timestamp or datetime.now(UTC)
        conversation.last_message_at = message_time
        if conversation.state == ConversationState.CLOSED:
            conversation.state = ConversationState.OPEN

        webhook_event = self.webhook_events.get_by_id(webhook_event_id)
        if webhook_event is not None:
            webhook_event.shop_id = account.shop_id
            webhook_event.instagram_account_id = account.id

        job = MessageReceivedJob(
            message_id=message.id,
            conversation_id=conversation.id,
            shop_id=account.shop_id,
            instagram_account_id=account.id,
            customer_id=customer.id,
            webhook_event_id=webhook_event_id,
        )
        return job

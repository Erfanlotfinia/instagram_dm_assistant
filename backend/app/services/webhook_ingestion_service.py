from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import (
    ConversationState,
    MessageChannel,
    MessageDirection,
    MessageType,
    WebhookProcessingStatus,
    WebhookProvider,
)
from app.domain.models import Conversation, Customer, Message, WebhookEvent
from app.integrations.instagram_webhook import ParsedInstagramMessage, parse_instagram_webhook_payload
from app.integrations.rabbitmq import MessagePublisher, RabbitMQPublisher
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


class WebhookIngestionService:
    def __init__(
        self,
        db: Session,
        publisher: MessagePublisher | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.publisher = publisher or RabbitMQPublisher(self.settings)
        self.webhook_events = WebhookEventRepository(db)
        self.accounts = InstagramAccountRepository(db)
        self.customers = CustomerRepository(db)
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)

    def handle_instagram_payload(self, payload: dict[str, Any]) -> WebhookAckResponse | WebhookIgnoredResponse:
        parsed_messages = parse_instagram_webhook_payload(payload)
        if not parsed_messages:
            return WebhookIgnoredResponse(reason="no_messaging_events")

        webhook_event = self.webhook_events.create(
            WebhookEvent(
                provider=WebhookProvider.INSTAGRAM,
                event_type="instagram.messaging",
                raw_payload=payload,
                processing_status=WebhookProcessingStatus.RECEIVED,
            )
        )

        queued_count = 0
        errors: list[str] = []

        for parsed in parsed_messages:
            try:
                queued = self._process_message(webhook_event.id, parsed)
                if queued:
                    queued_count += 1
            except Exception as exc:  # noqa: BLE001 - log and continue for remaining messages
                logger.exception("Failed to process Instagram message %s", parsed.message_id)
                errors.append(str(exc))

        if queued_count > 0:
            self.webhook_events.update_status(webhook_event, WebhookProcessingStatus.QUEUED)
        elif errors:
            self.webhook_events.update_status(
                webhook_event,
                WebhookProcessingStatus.FAILED,
                error_message="; ".join(errors),
            )

        self.db.commit()
        return WebhookAckResponse()

    def _process_message(self, webhook_event_id: UUID, parsed: ParsedInstagramMessage) -> bool:
        existing = self.messages.get_by_instagram_message_id(parsed.message_id)
        if existing is not None:
            logger.info("Duplicate Instagram message id %s ignored", parsed.message_id)
            return False

        account = self.accounts.get_by_ig_user_id(parsed.recipient_id)
        if account is None:
            logger.warning("No Instagram account for recipient %s", parsed.recipient_id)
            return False

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
            return False

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
        self.publisher.publish(
            self.settings.rabbitmq_queue_message_received,
            job.model_dump(mode="json"),
        )
        return True

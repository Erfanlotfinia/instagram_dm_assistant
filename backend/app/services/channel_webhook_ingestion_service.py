from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.channels.adapters import (
    BaleProviderAdapter,
    InstagramProviderAdapter,
    RubikaProviderAdapter,
    WhatsAppProviderAdapter,
)
from app.core.config import get_settings
from app.core.log_masking import redact_value
from app.core.request_context import get_request_id
from app.domain.enums import (
    ChannelConversationStatus,
    ChannelMessageType,
    ChannelProvider,
    MessageChannel,
    MessageDirection,
    MessageType,
    OutboxEventStatus,
    WebhookDedupeOutcome,
    WebhookProcessingStatus,
    WebhookProvider,
)
from app.domain.models import (
    ChannelAccount,
    ChannelConversation,
    ChannelDeliveryStatusEvent,
    ChannelMessage,
    Message,
    OutboxEvent,
    WebhookEvent,
)
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.channels import NormalizedInboundMessage
from app.schemas.queue_events import MessageReceivedJob
from app.schemas.webhook import WebhookAckResponse, WebhookIgnoredResponse
from app.services.channel_account_service import adapter_for_provider
from app.services.telegram_business_update_service import TelegramBusinessUpdateService

logger = logging.getLogger(__name__)


def channel_idempotency_key(message: NormalizedInboundMessage) -> str:
    identity = message.external_message_id or message.external_update_id
    if not identity:
        raw = json.dumps(message.raw_payload, sort_keys=True, default=str)
        identity = hashlib.sha256(raw.encode()).hexdigest()
    return f"{message.provider.value}:{message.channel_account_id}:{identity}"


def redacted_normalized_payload(message: NormalizedInboundMessage) -> dict[str, Any]:
    payload = message.model_dump(mode="json")
    payload["raw_payload"] = redact_value(message.raw_payload)
    return payload


class ChannelWebhookIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def adapter_for_provider(
        self, provider: ChannelProvider, account: ChannelAccount | None = None
    ):
        if account is not None:
            return adapter_for_provider(provider, account)
        return {
            ChannelProvider.INSTAGRAM: InstagramProviderAdapter(),
            ChannelProvider.WHATSAPP: WhatsAppProviderAdapter(),
            ChannelProvider.TELEGRAM: adapter_for_provider(ChannelProvider.TELEGRAM),
            ChannelProvider.BALE: BaleProviderAdapter(),
            ChannelProvider.RUBIKA: RubikaProviderAdapter(),
        }[provider]

    def handle_payload(
        self,
        provider: ChannelProvider,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
        shop_id: Any | None = None,
        channel_account_id: Any | None = None,
    ) -> WebhookAckResponse | WebhookIgnoredResponse:
        account = self._account_by_id(provider, channel_account_id)
        if account is None:
            return WebhookIgnoredResponse(reason="channel_account_not_found")

        webhook_key = self._webhook_idempotency_key(provider, account, payload)
        existing_event = self.db.scalar(
            select(WebhookEvent).where(
                WebhookEvent.provider == WebhookProvider(provider.value),
                WebhookEvent.idempotency_key == webhook_key,
            )
        )
        if existing_event is not None:
            return WebhookAckResponse(dedupe_outcome=WebhookDedupeOutcome.DUPLICATE.value)

        webhook_event = WebhookEvent(
            provider=WebhookProvider(provider.value),
            shop_id=account.shop_id,
            event_type="channel.webhook.received",
            raw_payload=redact_value(payload),
            processing_status=WebhookProcessingStatus.RECEIVED,
            idempotency_key=webhook_key,
            trace_id=get_request_id(),
            dedupe_outcome=WebhookDedupeOutcome.PROCESSED,
        )
        self.db.add(webhook_event)
        try:
            # The lookup above is only a fast path; the database unique index is the
            # final concurrency guard when duplicate deliveries race this insert.
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            return WebhookAckResponse(dedupe_outcome=WebhookDedupeOutcome.DUPLICATE.value)

        if provider == ChannelProvider.TELEGRAM:
            TelegramBusinessUpdateService(self.db).handle_update(account, payload)

        messages = self.adapter_for_provider(provider, account).parse_inbound_update(
            payload, headers
        )
        if not messages:
            webhook_event.processing_status = WebhookProcessingStatus.PROCESSED
            webhook_event.dedupe_outcome = WebhookDedupeOutcome.IGNORED
            self.db.commit()
            return WebhookIgnoredResponse(reason="no_channel_messages")
        jobs = []
        for normalized in messages:
            normalized.shop_id = account.shop_id
            normalized.channel_account_id = account.id
            job = self._process_message(account, normalized, webhook_event.id)
            if job:
                jobs.append(job)
        webhook_event.processing_status = (
            WebhookProcessingStatus.QUEUED if jobs else WebhookProcessingStatus.PROCESSED
        )
        webhook_event.dedupe_outcome = (
            WebhookDedupeOutcome.PROCESSED if jobs else WebhookDedupeOutcome.IGNORED
        )
        self.db.commit()
        return WebhookAckResponse(dedupe_outcome="processed" if jobs else "ignored")

    def _account_by_id(
        self, provider: ChannelProvider, channel_account_id: Any | None
    ) -> ChannelAccount | None:
        if channel_account_id is None:
            return None
        return self.db.scalar(
            select(ChannelAccount).where(
                ChannelAccount.provider == provider,
                ChannelAccount.id == channel_account_id,
            )
        )

    @staticmethod
    def _webhook_idempotency_key(
        provider: ChannelProvider,
        account: ChannelAccount,
        payload: dict[str, Any],
    ) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return (
            f"channel-webhook:{provider.value}:{account.id}:"
            f"{hashlib.sha256(raw.encode()).hexdigest()}"
        )

    def _process_message(
        self,
        account: ChannelAccount,
        normalized: NormalizedInboundMessage,
        webhook_event_id: Any,
    ) -> MessageReceivedJob | None:
        idempotency_key = channel_idempotency_key(normalized)
        if normalized.raw_payload.get("event_type") == "delivery_status":
            status_payload = normalized.raw_payload.get("status", {})
            external_message_id = str(
                status_payload.get("id") or normalized.external_message_id or ""
            )
            if not external_message_id:
                return None
            if self.db.scalar(
                select(ChannelDeliveryStatusEvent).where(
                    ChannelDeliveryStatusEvent.provider == account.provider,
                    ChannelDeliveryStatusEvent.channel_account_id == account.id,
                    ChannelDeliveryStatusEvent.external_message_id == external_message_id,
                    ChannelDeliveryStatusEvent.status
                    == str(status_payload.get("status", "unknown")),
                )
            ):
                return None
            self.db.add(
                ChannelDeliveryStatusEvent(
                    shop_id=account.shop_id,
                    provider=account.provider,
                    channel_account_id=account.id,
                    external_message_id=external_message_id,
                    external_chat_id=normalized.external_chat_id,
                    status=str(status_payload.get("status", "unknown")),
                    raw_payload_json=redact_value(normalized.raw_payload),
                    occurred_at=normalized.received_at,
                )
            )
            return None
        if self.db.scalar(
            select(ChannelMessage).where(
                ChannelMessage.provider == account.provider,
                ChannelMessage.channel_account_id == account.id,
                ChannelMessage.idempotency_key == idempotency_key,
            )
        ):
            return None
        customer = CustomerRepository(self.db).create_customer_from_channel_identity(
            shop_id=account.shop_id,
            provider=account.provider,
            channel_account_id=account.id,
            external_user_id=normalized.external_user_id,
            external_chat_id=normalized.external_chat_id,
            username=normalized.username,
            display_name=normalized.display_name,
            phone=normalized.phone,
            raw_profile_json=redact_value(normalized.raw_payload),
        )
        conversation = ConversationRepository(self.db).get_or_create_conversation_by_channel(
            shop_id=account.shop_id,
            customer_id=customer.id,
            provider=account.provider,
            channel_account_id=account.id,
            external_conversation_id=normalized.external_chat_id,
        )
        conversation.channel_customer_id = normalized.external_user_id
        channel_conversation = self.db.scalar(
            select(ChannelConversation).where(
                ChannelConversation.provider == account.provider,
                ChannelConversation.channel_account_id == account.id,
                ChannelConversation.external_chat_id == normalized.external_chat_id,
            )
        )
        if channel_conversation is None:
            expires = (
                normalized.received_at + timedelta(hours=24)
                if account.provider == ChannelProvider.WHATSAPP
                else None
            )
            channel_conversation = ChannelConversation(
                shop_id=account.shop_id,
                provider=account.provider,
                channel_account_id=account.id,
                external_chat_id=normalized.external_chat_id,
                conversation_id=conversation.id,
                messaging_window_expires_at=expires,
                last_inbound_at=normalized.received_at,
                status=ChannelConversationStatus.OPEN,
            )
            self.db.add(channel_conversation)
        else:
            channel_conversation.last_inbound_at = normalized.received_at
            if account.provider == ChannelProvider.WHATSAPP:
                channel_conversation.messaging_window_expires_at = (
                    normalized.received_at + timedelta(hours=24)
                )
        internal_type = (
            MessageType.TEXT
            if normalized.message_type == ChannelMessageType.TEXT
            else MessageType.ATTACHMENT
        )
        text = (
            normalized.text
            or normalized.caption
            or normalized.shared_post_url
            or normalized.button_text
        )
        internal_message = Message(
            shop_id=account.shop_id,
            conversation_id=conversation.id,
            customer_id=customer.id,
            direction=MessageDirection.INBOUND,
            channel_provider=account.provider,
            channel_account_id=account.id,
            external_message_id=normalized.external_message_id,
            external_update_id=normalized.external_update_id,
            channel=MessageChannel(account.provider.value),
            instagram_message_id=(
                normalized.external_message_id
                if account.provider == ChannelProvider.INSTAGRAM
                else None
            ),
            channel_message_id=normalized.external_message_id,
            message_type=internal_type,
            text=text,
            content=text,
            raw_payload=redact_value(normalized.raw_payload),
            raw_payload_json=redact_value(normalized.raw_payload),
            normalized_payload_json=redacted_normalized_payload(normalized),
        )
        self.db.add(internal_message)
        self.db.flush()
        channel_message = ChannelMessage(
            shop_id=account.shop_id,
            provider=account.provider,
            channel_account_id=account.id,
            conversation_id=conversation.id,
            internal_message_id=internal_message.id,
            external_message_id=normalized.external_message_id,
            external_update_id=normalized.external_update_id,
            direction=MessageDirection.INBOUND,
            message_type=normalized.message_type,
            text=normalized.text,
            caption=normalized.caption,
            media_json={"items": [m.model_dump(mode="json") for m in normalized.media_items]},
            interactive_json={
                "button_id": normalized.button_id,
                "button_text": normalized.button_text,
            },
            raw_payload_json=redact_value(normalized.raw_payload),
            normalized_payload_json=redacted_normalized_payload(normalized),
            idempotency_key=idempotency_key,
        )
        try:
            self.db.add(channel_message)
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            return None
        conversation.last_message_at = normalized.received_at or datetime.now(UTC)
        job = MessageReceivedJob(
            message_id=internal_message.id,
            conversation_id=conversation.id,
            shop_id=account.shop_id,
            instagram_account_id=conversation.instagram_account_id,
            channel_provider=account.provider,
            channel_account_id=account.id,
            customer_id=customer.id,
            webhook_event_id=webhook_event_id,
        )
        self.db.add(
            OutboxEvent(
                event_type="channel.message.received",
                aggregate_type="message",
                aggregate_id=str(internal_message.id),
                shop_id=account.shop_id,
                payload={
                    "_queue_name": get_settings().rabbitmq_queue_message_received,
                    "_body": job.model_dump(mode="json"),
                    "idempotency_key": f"message-received:{internal_message.id}",
                },
                status=OutboxEventStatus.PENDING,
            )
        )
        return job

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
    TelegramProviderAdapter,
    WhatsAppProviderAdapter,
)
from app.domain.enums import (
    ChannelConversationStatus,
    ChannelMessageType,
    ChannelProvider,
    ConversationState,
    MessageChannel,
    MessageDirection,
    MessageType,
    OutboxEventStatus,
)
from app.domain.models import (
    ChannelAccount,
    ChannelContactIdentity,
    ChannelConversation,
    ChannelMessage,
    ChannelDeliveryStatusEvent,
    Conversation,
    Customer,
    Message,
    OutboxEvent,
)
from app.schemas.channels import NormalizedInboundMessage
from app.schemas.queue_events import MessageReceivedJob
from app.schemas.webhook import WebhookAckResponse, WebhookIgnoredResponse
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.customer_repository import CustomerRepository

logger = logging.getLogger(__name__)


def mask_pii(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: (
                "***"
                if k.lower() in {"phone", "wa_id", "from", "access_token", "token"}
                else mask_pii(v)
            )
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [mask_pii(v) for v in value]
    return value


def channel_idempotency_key(message: NormalizedInboundMessage) -> str:
    identity = message.external_message_id or message.external_update_id
    if not identity:
        raw = json.dumps(message.raw_payload, sort_keys=True, default=str)
        identity = hashlib.sha256(raw.encode()).hexdigest()
    return f"{message.provider.value}:{message.channel_account_id}:{identity}"


class ChannelWebhookIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def adapter_for_provider(self, provider: ChannelProvider):
        return {
            ChannelProvider.INSTAGRAM: InstagramProviderAdapter(),
            ChannelProvider.WHATSAPP: WhatsAppProviderAdapter(),
            ChannelProvider.TELEGRAM: TelegramProviderAdapter(),
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
        messages = self.adapter_for_provider(provider).parse_inbound_update(
            payload, headers
        )
        if not messages:
            return WebhookIgnoredResponse(reason="no_channel_messages")
        jobs = []
        for normalized in messages:
            account = self._resolve_account(
                provider, normalized, shop_id, channel_account_id
            )
            if not account:
                logger.warning(
                    "No channel account found for provider=%s payload=%s",
                    provider.value,
                    mask_pii(normalized.raw_payload),
                )
                continue
            normalized.shop_id = account.shop_id
            normalized.channel_account_id = account.id
            job = self._process_message(account, normalized)
            if job:
                jobs.append(job)
        self.db.commit()
        return WebhookAckResponse(dedupe_outcome="processed" if jobs else "ignored")

    def _resolve_account(
        self,
        provider: ChannelProvider,
        message: NormalizedInboundMessage,
        shop_id: Any | None,
        channel_account_id: Any | None,
    ) -> ChannelAccount | None:
        stmt = select(ChannelAccount).where(ChannelAccount.provider == provider)
        if channel_account_id:
            stmt = stmt.where(ChannelAccount.id == channel_account_id)
        elif shop_id:
            stmt = stmt.where(ChannelAccount.shop_id == shop_id)
        elif provider == ChannelProvider.WHATSAPP:
            phone_number_id = message.raw_payload.get("phone_number_id")
            if not phone_number_id:
                return None
            stmt = stmt.where(ChannelAccount.phone_number_id == phone_number_id)
        elif provider == ChannelProvider.INSTAGRAM:
            recipient = message.raw_payload.get("recipient") or {}
            recipient_id = recipient.get("id") if isinstance(recipient, dict) else None
            if not recipient_id:
                return None
            stmt = stmt.where(ChannelAccount.external_account_id == str(recipient_id))
        else:
            return None
        return self.db.scalar(stmt)

    def _process_message(
        self, account: ChannelAccount, normalized: NormalizedInboundMessage
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
                    ChannelDeliveryStatusEvent.external_message_id
                    == external_message_id,
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
                    raw_payload_json=mask_pii(normalized.raw_payload),
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
            raw_profile_json=mask_pii(normalized.raw_payload),
        )
        conversation = ConversationRepository(
            self.db
        ).get_or_create_conversation_by_channel(
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
            raw_payload=mask_pii(normalized.raw_payload),
            raw_payload_json=mask_pii(normalized.raw_payload),
            normalized_payload_json=normalized.model_dump(mode="json"),
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
            media_json={
                "items": [m.model_dump(mode="json") for m in normalized.media_items]
            },
            interactive_json={
                "button_id": normalized.button_id,
                "button_text": normalized.button_text,
            },
            raw_payload_json=mask_pii(normalized.raw_payload),
            normalized_payload_json=normalized.model_dump(mode="json"),
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
            webhook_event_id=None,
        )
        self.db.add(
            OutboxEvent(
                event_type="message.received",
                aggregate_type="message",
                aggregate_id=str(internal_message.id),
                shop_id=account.shop_id,
                payload={
                    "_body": job.model_dump(mode="json"),
                    "idempotency_key": f"message-received:{internal_message.id}",
                },
                status=OutboxEventStatus.PENDING,
            )
        )
        return job

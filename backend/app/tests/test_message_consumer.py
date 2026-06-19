import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from app.core.security import encrypt_secret
from app.domain.enums import MessageChannel, MessageDirection, MessageType, WebhookProvider
from app.domain.enums import ChannelProvider, InstagramAccountStatus, WebhookProcessingStatus
from app.domain.models import (
    Conversation,
    Customer,
    InstagramAccount,
    Message,
    WebhookEvent,
)
from app.integrations.redis_lock import ConversationLockService
from app.schemas.queue_events import InvalidJobPayloadError, MessageReceivedJob, validate_message_received_payload
from app.services.webhook_ingestion_service import WebhookIngestionService
from app.tests.fixtures.instagram import build_instagram_conversation, seed_instagram_channel_account
from app.tests.fixtures.instagram_webhook import SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD
from app.workers.message_consumer import MessageConsumer, handle_delivery


def test_message_consumer_marks_webhook_processed(db_session, demo_shop) -> None:
    account = InstagramAccount(
        shop_id=demo_shop.id,
        ig_user_id="17841400000000001",
        username="demo_shop",
        access_token_encrypted=encrypt_secret("token"),
        status=InstagramAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.commit()

    publisher = MagicMock()
    WebhookIngestionService(db_session, publisher=publisher).handle_instagram_payload(
        SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD
    )

    message = db_session.query(Message).one()
    conversation = db_session.query(Conversation).one()
    customer = db_session.query(Customer).one()
    webhook_event = db_session.query(WebhookEvent).one()

    lock_service = MagicMock(spec=ConversationLockService)
    lock_service.acquire.return_value = "lock-token"
    lock_service.release.return_value = True

    job = MessageReceivedJob(
        message_id=message.id,
        conversation_id=conversation.id,
        shop_id=demo_shop.id,
        instagram_account_id=account.id,
        customer_id=customer.id,
        webhook_event_id=webhook_event.id,
    )

    consumer = MessageConsumer(db_session, lock_service=lock_service)
    assert consumer.process_job(job.model_dump(mode="json")) is True
    assert webhook_event.processing_status == WebhookProcessingStatus.PROCESSED


def test_message_consumer_is_idempotent_for_processed_event(db_session, demo_shop) -> None:
    account, channel_account = seed_instagram_channel_account(db_session, demo_shop)

    customer = Customer(shop_id=demo_shop.id, instagram_user_id="cust")
    db_session.add(customer)
    db_session.flush()
    conversation = build_instagram_conversation(
        db_session,
        demo_shop,
        account,
        channel_account,
        customer,
        external_id="cust",
    )
    message = Message(
        shop_id=demo_shop.id,
        conversation_id=conversation.id,
        customer_id=customer.id,
        channel_provider=ChannelProvider.INSTAGRAM,
        channel_account_id=channel_account.id,
        direction=MessageDirection.INBOUND,
        channel=MessageChannel.INSTAGRAM,
        message_type=MessageType.TEXT,
        text="hi",
        raw_payload={},
    )
    db_session.add(message)
    webhook_event = WebhookEvent(
        provider=WebhookProvider.INSTAGRAM,
        event_type="instagram.messaging",
        raw_payload={},
        processing_status=WebhookProcessingStatus.PROCESSED,
    )
    db_session.add(webhook_event)
    db_session.commit()

    lock_service = MagicMock(spec=ConversationLockService)
    lock_service.acquire.return_value = "lock-token"

    job = MessageReceivedJob(
        message_id=message.id,
        conversation_id=conversation.id,
        shop_id=demo_shop.id,
        instagram_account_id=account.id,
        customer_id=customer.id,
        webhook_event_id=webhook_event.id,
    )

    consumer = MessageConsumer(db_session, lock_service=lock_service)
    assert consumer.process_job(job.model_dump(mode="json")) is True


def test_validate_message_received_payload_reports_missing_fields() -> None:
    with pytest.raises(InvalidJobPayloadError, match="missing required fields"):
        validate_message_received_payload({"raw": "malformed-worker-payload", "retry_count": 3})


def test_handle_delivery_rejects_malformed_payload() -> None:
    body = b'{"raw": "malformed-worker-payload", "retry_count": 3}'

    with pytest.raises(InvalidJobPayloadError, match="missing required fields"):
        handle_delivery(body)

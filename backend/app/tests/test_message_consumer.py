from unittest.mock import MagicMock, call

import pytest

from app.core.security import encrypt_secret
from app.domain.enums import (
    ChannelProvider,
    InstagramAccountStatus,
    MessageChannel,
    MessageDirection,
    MessageType,
    WebhookProcessingStatus,
    WebhookProvider,
)
from app.domain.models import (
    Conversation,
    Customer,
    InstagramAccount,
    Message,
    WebhookEvent,
)
from app.integrations.redis_lock import ConversationLockService
from app.schemas.queue_events import (
    InvalidJobPayloadError,
    MessageReceivedJob,
    validate_message_received_payload,
)
from app.services.webhook_ingestion_service import WebhookIngestionService
from app.tests.fixtures.instagram import (
    build_instagram_conversation,
    seed_instagram_channel_account,
)
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

class _DummySettings:
    rabbitmq_queue_message_received = "channel.message.received"
    rabbitmq_queue_retry = "channel.message.received.retry"
    rabbitmq_queue_dlq = "channel.message.received.dlq"
    rabbitmq_max_retries = 2


class _Method:
    delivery_tag = 123


def _worker(monkeypatch, publisher=None):
    from app.workers.main import WorkerApp

    worker = WorkerApp.__new__(WorkerApp)
    worker.settings = _DummySettings()
    worker._publisher = publisher or MagicMock()
    worker._update_queue_lag = MagicMock()
    worker._persist_failed_job = MagicMock()
    return worker


def _properties(retry_count=0):
    from pika import BasicProperties

    return BasicProperties(
        headers={"x-retry-count": retry_count},
        correlation_id="corr-1",
        message_id="msg-1",
    )


def test_conversation_lock_sends_to_retry_queue_not_immediate_requeue(monkeypatch) -> None:
    from app.workers import main as worker_main
    from app.workers.message_consumer import ConversationLockedError

    publisher = MagicMock()
    worker = _worker(monkeypatch, publisher)
    channel = MagicMock()
    monkeypatch.setattr(
        worker_main,
        "handle_delivery",
        MagicMock(side_effect=ConversationLockedError("locked")),
    )

    worker._on_message(channel, _Method(), _properties(), b'{"message_id": "m"}')

    publisher.publish_to_retry.assert_called_once()
    channel.basic_ack.assert_called_once_with(delivery_tag=123)
    channel.basic_nack.assert_not_called()


def test_generic_retryable_error_goes_to_retry_until_max_retries(monkeypatch) -> None:
    from app.workers import main as worker_main

    publisher = MagicMock()
    worker = _worker(monkeypatch, publisher)
    channel = MagicMock()
    monkeypatch.setattr(worker_main, "handle_delivery", MagicMock(side_effect=RuntimeError("boom")))

    worker._on_message(channel, _Method(), _properties(retry_count=1), b'{"message_id": "m"}')

    publisher.publish_to_retry.assert_called_once()
    assert publisher.publish_to_retry.call_args.kwargs["retry_count"] == 2
    publisher.publish_to_dlq.assert_not_called()
    channel.basic_ack.assert_called_once_with(delivery_tag=123)


def test_after_max_retries_message_goes_to_dlq(monkeypatch) -> None:
    from app.workers import main as worker_main

    publisher = MagicMock()
    worker = _worker(monkeypatch, publisher)
    channel = MagicMock()
    monkeypatch.setattr(worker_main, "handle_delivery", MagicMock(side_effect=RuntimeError("boom")))

    worker._on_message(channel, _Method(), _properties(retry_count=2), b'{"message_id": "m"}')

    publisher.publish_to_dlq.assert_called_once()
    assert publisher.publish_to_dlq.call_args.kwargs["retry_count"] == 3
    publisher.publish_to_retry.assert_not_called()
    channel.basic_ack.assert_called_once_with(delivery_tag=123)
    worker._persist_failed_job.assert_called_once()


def test_invalid_payload_goes_to_dlq_and_failed_jobs(monkeypatch) -> None:
    from app.schemas.queue_events import InvalidJobPayloadError
    from app.workers import main as worker_main

    publisher = MagicMock()
    worker = _worker(monkeypatch, publisher)
    channel = MagicMock()
    monkeypatch.setattr(
        worker_main,
        "handle_delivery",
        MagicMock(side_effect=InvalidJobPayloadError("bad")),
    )

    worker._on_message(channel, _Method(), _properties(), b'{"raw": "bad"}')

    publisher.publish_to_dlq.assert_called_once()
    channel.basic_ack.assert_called_once_with(delivery_tag=123)
    worker._persist_failed_job.assert_called_once()


def test_original_message_acked_only_after_retry_publish_succeeds(monkeypatch) -> None:
    from app.workers import main as worker_main

    publisher = MagicMock()
    worker = _worker(monkeypatch, publisher)
    channel = MagicMock()
    monkeypatch.setattr(worker_main, "handle_delivery", MagicMock(side_effect=RuntimeError("boom")))

    worker._on_message(channel, _Method(), _properties(), b'{"message_id": "m"}')

    assert publisher.publish_to_retry.call_count == 1
    assert channel.method_calls[-1] == call.basic_ack(delivery_tag=123)


def test_publisher_confirm_failure_does_not_ack_original_message(monkeypatch) -> None:
    from app.workers import main as worker_main

    publisher = MagicMock()
    publisher.publish_to_retry.side_effect = RuntimeError("nack")
    worker = _worker(monkeypatch, publisher)
    channel = MagicMock()
    monkeypatch.setattr(worker_main, "handle_delivery", MagicMock(side_effect=RuntimeError("boom")))

    with pytest.raises(RuntimeError, match="nack"):
        worker._on_message(channel, _Method(), _properties(), b'{"message_id": "m"}')

    channel.basic_ack.assert_not_called()

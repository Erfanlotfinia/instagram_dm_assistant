from unittest.mock import MagicMock

from sqlalchemy import select

from app.domain.models import OutboxEvent
from app.services.outbox_publisher_service import OutboxPublisherService
from app.services.webhook_ingestion_service import WebhookIngestionService
from app.tests.fixtures.instagram_webhook import SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD
from app.tests.test_webhook_ingestion import _create_account


def test_webhook_creates_outbox_event(db_session, demo_shop) -> None:
    _create_account(db_session, demo_shop)
    publisher = MagicMock()
    service = WebhookIngestionService(db_session, publisher=publisher)

    service.handle_instagram_payload(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)

    publisher.publish.assert_not_called()
    events = db_session.scalars(select(OutboxEvent)).all()
    assert len(events) == 1
    assert events[0].status.value == "pending"
    assert events[0].payload["_queue_name"] == "channel.message.received"


def test_outbox_publisher_publishes_after_commit(db_session, demo_shop) -> None:
    _create_account(db_session, demo_shop)
    service = WebhookIngestionService(db_session, publisher=MagicMock())
    service.handle_instagram_payload(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)

    publisher = MagicMock()
    from app.integrations.rabbitmq import RabbitMQPublisher

    original = RabbitMQPublisher

    class FakePublisher:
        def __init__(self, settings):
            self.settings = settings

        def publish(self, queue_name, payload, retry_count=0):
            publisher.publish(queue_name, payload, retry_count=retry_count)

        def close(self):
            return None

    import app.services.outbox_publisher_service as outbox_module

    outbox_module.RabbitMQPublisher = FakePublisher
    try:
        count = OutboxPublisherService(db_session).publish_pending()
    finally:
        outbox_module.RabbitMQPublisher = original

    assert count == 1
    publisher.publish.assert_called_once()
    published = db_session.scalar(select(OutboxEvent))
    assert published is not None
    assert published.status.value == "published"

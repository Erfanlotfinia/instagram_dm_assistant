from unittest.mock import MagicMock

from sqlalchemy import func, select

from app.core.security import encrypt_secret
from app.domain.enums import InstagramAccountStatus, WebhookProcessingStatus
from app.domain.models import Conversation, Customer, InstagramAccount, Message, WebhookEvent
from app.services.webhook_ingestion_service import WebhookIngestionService
from app.tests.fixtures.instagram_webhook import (
    SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD,
    SAMPLE_SHARED_POST_PAYLOAD,
)


def _create_account(db_session, demo_shop, ig_user_id: str = "17841400000000001") -> InstagramAccount:
    account = InstagramAccount(
        shop_id=demo_shop.id,
        ig_user_id=ig_user_id,
        username="demo_shop",
        access_token_encrypted=encrypt_secret("token"),
        webhook_enabled=True,
        status=InstagramAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


def test_webhook_creates_customer_and_conversation(db_session, demo_shop) -> None:
    _create_account(db_session, demo_shop)
    publisher = MagicMock()
    service = WebhookIngestionService(db_session, publisher=publisher)

    service.handle_instagram_payload(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)

    customers = db_session.scalars(select(Customer)).all()
    conversations = db_session.scalars(select(Conversation)).all()
    messages = db_session.scalars(select(Message)).all()

    assert len(customers) == 1
    assert customers[0].instagram_user_id == "customer-ig-999"
    assert len(conversations) == 1
    assert conversations[0].customer_id == customers[0].id
    assert len(messages) == 1
    assert messages[0].instagram_message_id == "m_test_message_001"
    assert messages[0].text == "Hello, I want to order"


def test_webhook_stores_raw_payload_and_event(db_session, demo_shop) -> None:
    _create_account(db_session, demo_shop)
    publisher = MagicMock()
    service = WebhookIngestionService(db_session, publisher=publisher)

    service.handle_instagram_payload(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)

    events = db_session.scalars(select(WebhookEvent)).all()
    assert len(events) == 1
    assert events[0].raw_payload == SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD
    assert events[0].processing_status == WebhookProcessingStatus.QUEUED


def test_webhook_parses_shared_post(db_session, demo_shop) -> None:
    _create_account(db_session, demo_shop)
    publisher = MagicMock()
    service = WebhookIngestionService(db_session, publisher=publisher)

    service.handle_instagram_payload(SAMPLE_SHARED_POST_PAYLOAD)

    message = db_session.scalar(select(Message).where(Message.instagram_message_id == "m_test_message_002"))
    assert message is not None
    assert message.text == "https://www.instagram.com/p/ABC123/"


def test_rabbitmq_publish_payload(db_session, demo_shop) -> None:
    from app.domain.models import OutboxEvent

    _create_account(db_session, demo_shop)
    publisher = MagicMock()
    service = WebhookIngestionService(db_session, publisher=publisher)

    service.handle_instagram_payload(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)

    publisher.publish.assert_not_called()
    outbox_events = db_session.scalars(select(OutboxEvent)).all()
    assert len(outbox_events) == 1
    body = outbox_events[0].payload["_body"]
    assert "message_id" in body
    assert "conversation_id" in body
    assert "shop_id" in body


def test_unknown_recipient_still_stores_event(db_session, demo_shop) -> None:
    publisher = MagicMock()
    service = WebhookIngestionService(db_session, publisher=publisher)

    result = service.handle_instagram_payload(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)

    assert result.status == "ok"
    count = db_session.scalar(select(func.count()).select_from(WebhookEvent))
    assert count == 1
    publisher.publish.assert_not_called()

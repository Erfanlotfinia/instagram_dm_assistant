from unittest.mock import MagicMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import encrypt_secret
from app.domain.enums import InstagramAccountStatus
from app.domain.models import InstagramAccount, OutboxEvent
from app.services.webhook_ingestion_service import WebhookIngestionService
from app.tests.fixtures.instagram_webhook import SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD


@pytest.fixture()
def instagram_account(db_session: Session, demo_shop):
    account = InstagramAccount(
        shop_id=demo_shop.id,
        ig_user_id="17841400000000001",
        username="demo_shop",
        access_token_encrypted=encrypt_secret("token"),
        webhook_enabled=True,
        status=InstagramAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture()
def mock_publisher():
    publisher = MagicMock()
    publisher.publish = MagicMock()
    return publisher


def test_instagram_webhook_verification_success(client) -> None:
    settings = get_settings()
    response = client.get(
        "/api/v1/webhooks/instagram",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": settings.instagram_webhook_verify_token,
            "hub.challenge": "challenge-token-123",
        },
    )
    assert response.status_code == 200
    assert response.text == "challenge-token-123"


def test_instagram_webhook_verification_failure(client) -> None:
    response = client.get(
        "/api/v1/webhooks/instagram",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "challenge-token-123",
        },
    )
    assert response.status_code == 403


def test_instagram_webhook_receiver_via_service(
    db_session: Session,
    instagram_account,
    mock_publisher,
) -> None:
    service = WebhookIngestionService(db_session, publisher=mock_publisher)
    result = service.handle_instagram_payload(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)
    assert result.status == "ok"
    mock_publisher.publish.assert_not_called()
    outbox_count = db_session.scalar(select(func.count()).select_from(OutboxEvent))
    assert outbox_count == 1


def test_instagram_webhook_receiver_via_api(client, instagram_account, db_session) -> None:
    response = client.post("/api/v1/webhooks/instagram", json=SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    outbox_count = db_session.scalar(select(func.count()).select_from(OutboxEvent))
    assert outbox_count == 1


def test_instagram_webhook_duplicate_message_is_idempotent(
    db_session: Session,
    instagram_account,
    mock_publisher,
) -> None:
    service = WebhookIngestionService(db_session, publisher=mock_publisher)
    first = service.handle_instagram_payload(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)
    second = service.handle_instagram_payload(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)

    assert first.status == "ok"
    assert second.status == "ok"
    assert second.dedupe_outcome == "duplicate"
    mock_publisher.publish.assert_not_called()
    outbox_count = db_session.scalar(select(func.count()).select_from(OutboxEvent))
    assert outbox_count == 1

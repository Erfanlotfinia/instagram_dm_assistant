"""Duplicate webhook delivery tests."""

from app.integrations.rabbitmq import NoOpPublisher
from app.services.webhook_ingestion_service import WebhookIngestionService, compute_webhook_idempotency_key
from app.tests.fixtures.instagram_webhook import SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD


def test_compute_idempotency_key_stable() -> None:
    key1 = compute_webhook_idempotency_key(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)
    key2 = compute_webhook_idempotency_key(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)
    assert key1 == key2
    assert key1.startswith("meta:") or key1.startswith("sha256:")


def test_duplicate_webhook_returns_duplicate_outcome(db_session, demo_shop) -> None:
    from app.tests.fixtures.orders import seed_order_flow_data

    seed_order_flow_data(db_session, demo_shop)
    service = WebhookIngestionService(db_session, publisher=NoOpPublisher())
    first = service.handle_instagram_payload(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)
    second = service.handle_instagram_payload(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)
    assert first.status == "ok"
    assert second.dedupe_outcome == "duplicate"

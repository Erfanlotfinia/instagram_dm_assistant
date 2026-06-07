from unittest.mock import MagicMock

from app.core.security import encrypt_secret
from app.domain.enums import InstagramAccountStatus
from app.domain.models import InstagramAccount
from app.services.webhook_ingestion_service import WebhookIngestionService
from app.tests.fixtures.instagram_webhook import SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD


def test_get_dashboard_metrics(client, auth_headers, db_session, demo_shop) -> None:
    response = client.get(
        f"/api/v1/shops/{demo_shop.id}/dashboard/metrics",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "today_orders" in data
    assert "paid_orders" in data
    assert "waiting_for_payment" in data
    assert "handoff_conversations" in data
    assert "low_stock_variants" in data
    assert "conversion_funnel" in data
    assert data["conversion_funnel"]["inbound_messages"] >= 0


def test_send_manual_message_requires_takeover(client, auth_headers, db_session, demo_shop) -> None:
    account = InstagramAccount(
        shop_id=demo_shop.id,
        ig_user_id="17841400000000001",
        username="demo_shop",
        access_token_encrypted=encrypt_secret("token"),
        status=InstagramAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.commit()

    WebhookIngestionService(db_session, publisher=MagicMock()).handle_instagram_payload(
        SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD
    )
    conversation_id = client.get(
        f"/api/v1/shops/{demo_shop.id}/conversations",
        headers=auth_headers,
    ).json()[0]["id"]

    blocked = client.post(
        f"/api/v1/shops/{demo_shop.id}/conversations/{conversation_id}/messages",
        headers=auth_headers,
        json={"text": "Hello from operator"},
    )
    assert blocked.status_code == 400

    client.post(
        f"/api/v1/shops/{demo_shop.id}/conversations/{conversation_id}/take-over",
        headers=auth_headers,
    )
    sent = client.post(
        f"/api/v1/shops/{demo_shop.id}/conversations/{conversation_id}/messages",
        headers=auth_headers,
        json={"text": "Hello from operator"},
    )
    assert sent.status_code == 201
    assert sent.json()["text"] == "Hello from operator"
    assert sent.json()["direction"] == "outbound"


def test_mark_conversation_resolved(client, auth_headers, db_session, demo_shop) -> None:
    account = InstagramAccount(
        shop_id=demo_shop.id,
        ig_user_id="17841400000000001",
        username="demo_shop",
        access_token_encrypted=encrypt_secret("token"),
        status=InstagramAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.commit()

    WebhookIngestionService(db_session, publisher=MagicMock()).handle_instagram_payload(
        SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD
    )
    conversation_id = client.get(
        f"/api/v1/shops/{demo_shop.id}/conversations",
        headers=auth_headers,
    ).json()[0]["id"]

    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/conversations/{conversation_id}/mark-resolved",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["state"] == "closed"

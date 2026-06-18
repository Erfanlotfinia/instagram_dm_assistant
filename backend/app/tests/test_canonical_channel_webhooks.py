import hashlib
import hmac
import json
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.security import encrypt_secret
from app.domain.enums import ChannelProvider
from app.domain.models import (
    ChannelAccount,
    ChannelMessage,
    InstagramAccount,
    OutboxEvent,
    WebhookEvent,
)
from app.tests.fixtures.instagram_webhook import SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD

FIXTURES = Path(__file__).parent / "fixtures" / "channels"


def _account(db_session, demo_shop, provider, *, secret="webhook-secret", **values):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=provider,
        display_name=f"{provider.value} test",
        webhook_secret_encrypted=encrypt_secret(secret),
        webhook_verify_token="verify-token",
        **values,
    )
    db_session.add(account)
    db_session.commit()
    return account


def _signed_post(client, provider, payload, secret="webhook-secret", header=None):
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {"content-type": "application/json"}
    if provider in {ChannelProvider.INSTAGRAM, ChannelProvider.WHATSAPP}:
        headers["X-Hub-Signature-256"] = (
            "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        )
    else:
        headers[header or "X-Webhook-Secret"] = secret
    return client.post(f"/api/v1/channels/{provider.value}/webhook", content=body, headers=headers)


@pytest.mark.parametrize("provider", [ChannelProvider.INSTAGRAM, ChannelProvider.WHATSAPP])
def test_meta_webhook_verification_success(client, db_session, demo_shop, provider):
    _account(db_session, demo_shop, provider)
    response = client.get(
        f"/api/v1/channels/{provider.value}/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "verify-token",
            "hub.challenge": "challenge-123",
        },
    )
    assert response.status_code == 200
    assert response.text == "challenge-123"


def test_instagram_webhook_verification_failure(client, db_session, demo_shop):
    _account(db_session, demo_shop, ChannelProvider.INSTAGRAM)
    response = client.get(
        "/api/v1/channels/instagram/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "challenge-123",
        },
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("provider", "fixture", "account_values"),
    [
        (ChannelProvider.TELEGRAM, "telegram_text.json", {}),
        (ChannelProvider.BALE, "bale_text.json", {}),
        (ChannelProvider.RUBIKA, "rubika_receive_update_text.json", {}),
    ],
)
def test_bot_webhook_creates_normalized_message(
    client, db_session, demo_shop, provider, fixture, account_values
):
    account = _account(db_session, demo_shop, provider, **account_values)
    payload = json.loads((FIXTURES / fixture).read_text())
    response = _signed_post(client, provider, payload)
    assert response.status_code == 200, response.text

    message = db_session.scalar(
        select(ChannelMessage).where(ChannelMessage.channel_account_id == account.id)
    )
    assert message is not None
    assert message.provider == provider
    assert message.normalized_payload_json["provider"] == provider.value
    event = db_session.scalar(
        select(OutboxEvent).where(OutboxEvent.aggregate_id == str(message.internal_message_id))
    )
    assert event.event_type == "channel.message.received"
    assert event.payload["_queue_name"] == "channel.message.received"


def test_invalid_provider_returns_not_found(client):
    response = client.post("/api/v1/channels/not-a-provider/webhook", json={})
    assert response.status_code == 404


def test_invalid_signature_is_rejected(client, db_session, demo_shop):
    _account(
        db_session,
        demo_shop,
        ChannelProvider.WHATSAPP,
        phone_number_id="phone-1",
    )
    payload = json.loads((FIXTURES / "whatsapp_text.json").read_text())
    response = _signed_post(client, ChannelProvider.WHATSAPP, payload, secret="wrong")
    assert response.status_code == 403


def test_duplicate_webhook_is_idempotent(client, db_session, demo_shop):
    _account(db_session, demo_shop, ChannelProvider.TELEGRAM)
    payload = json.loads((FIXTURES / "telegram_text.json").read_text())
    first = _signed_post(client, ChannelProvider.TELEGRAM, payload)
    second = _signed_post(client, ChannelProvider.TELEGRAM, payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["dedupe_outcome"] == "duplicate"
    assert db_session.scalar(select(func.count()).select_from(ChannelMessage)) == 1
    assert db_session.scalar(select(func.count()).select_from(WebhookEvent)) == 1
    assert db_session.scalar(select(func.count()).select_from(OutboxEvent)) == 1


def test_instagram_uses_channel_account_without_instagram_account(client, db_session, demo_shop):
    _account(
        db_session,
        demo_shop,
        ChannelProvider.INSTAGRAM,
        external_account_id="17841400000000001",
    )
    response = _signed_post(client, ChannelProvider.INSTAGRAM, SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)
    assert response.status_code == 200, response.text
    assert db_session.scalar(select(func.count()).select_from(InstagramAccount)) == 0
    assert db_session.scalar(select(func.count()).select_from(ChannelMessage)) == 1

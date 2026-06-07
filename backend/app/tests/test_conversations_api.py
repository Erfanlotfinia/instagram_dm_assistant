from unittest.mock import MagicMock

from app.core.security import encrypt_secret
from app.domain.enums import InstagramAccountStatus
from app.domain.models import InstagramAccount
from app.services.webhook_ingestion_service import WebhookIngestionService
from app.tests.fixtures.instagram_webhook import SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD


def test_list_conversations(client, auth_headers, db_session, demo_shop) -> None:
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

    response = client.get(f"/api/v1/shops/{demo_shop.id}/conversations", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["handoff_required"] is False
    assert data[0]["last_message_text"] == "Hello, I want to order"


def test_get_conversation_detail_includes_messages(client, auth_headers, db_session, demo_shop) -> None:
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

    list_response = client.get(f"/api/v1/shops/{demo_shop.id}/conversations", headers=auth_headers)
    conversation_id = list_response.json()[0]["id"]

    detail_response = client.get(
        f"/api/v1/shops/{demo_shop.id}/conversations/{conversation_id}",
        headers=auth_headers,
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert len(detail["messages"]) == 1
    assert detail["messages"][0]["direction"] == "inbound"
    assert detail["messages"][0]["raw_payload"] is not None
    assert detail["workflow_state"] == "idle"
    assert detail["agent_actions"] == []


def test_take_over_and_release_conversation(client, auth_headers, db_session, demo_shop) -> None:
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

    take_over = client.post(
        f"/api/v1/shops/{demo_shop.id}/conversations/{conversation_id}/take-over",
        headers=auth_headers,
    )
    assert take_over.status_code == 200
    assert take_over.json()["agent_paused"] is True
    assert take_over.json()["workflow_state"] == "human_handoff"

    release = client.post(
        f"/api/v1/shops/{demo_shop.id}/conversations/{conversation_id}/release-to-agent",
        headers=auth_headers,
    )
    assert release.status_code == 200
    assert release.json()["agent_paused"] is False
    assert release.json()["workflow_state"] == "idle"

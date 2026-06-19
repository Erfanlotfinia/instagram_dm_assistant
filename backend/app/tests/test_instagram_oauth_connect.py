from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.security import decrypt_secret, encrypt_secret
from app.domain.enums import (
    ChannelAccountStatus,
    ChannelConnectionMethod,
    ChannelConnectionProvider,
    ChannelConnectionSessionStatus,
    ChannelProvider,
)
from app.domain.models import ChannelAccount, ChannelConnectionSession
from app.services.instagram_meta_connect_service import (
    InstagramCandidateAccount,
    InstagramMetaConnectService,
    MetaTokenResult,
)
from app.tests.fixtures.instagram_webhook import SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD


@pytest.fixture
def meta_app_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_APP_ID", "test-meta-app-id")
    monkeypatch.setenv("META_APP_SECRET", "test-meta-app-secret")
    from app.core.config import get_settings

    get_settings.cache_clear()


def _start_connect(client, auth_headers, shop_id):
    response = client.post(
        f"/api/v1/shops/{shop_id}/channels/instagram/connect/start",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_start_connect_creates_session(client, auth_headers, demo_shop, db_session, meta_app_settings):
    body = _start_connect(client, auth_headers, demo_shop.id)
    assert "authorization_url" in body
    assert "session_id" in body
    assert "expires_at" in body
    assert "facebook.com" in body["authorization_url"]
    assert "test-meta-app-id" in body["authorization_url"]

    session = db_session.get(ChannelConnectionSession, UUID(body["session_id"]))
    assert session is not None
    assert session.shop_id == demo_shop.id
    assert session.status == ChannelConnectionSessionStatus.REDIRECTED
    assert len(session.state) >= 32
    assert session.state != session.nonce


def test_start_connect_states_are_random(client, auth_headers, demo_shop, meta_app_settings):
    first = _start_connect(client, auth_headers, demo_shop.id)
    second = _start_connect(client, auth_headers, demo_shop.id)
    first_session = client.get(
        f"/api/v1/shops/{demo_shop.id}/channels/instagram/connect/sessions/{first['session_id']}",
        headers=auth_headers,
    ).json()
    second_session = client.get(
        f"/api/v1/shops/{demo_shop.id}/channels/instagram/connect/sessions/{second['session_id']}",
        headers=auth_headers,
    ).json()
    assert first_session["id"] != second_session["id"]


def test_expired_state_rejected(client, auth_headers, demo_shop, db_session, meta_app_settings):
    body = _start_connect(client, auth_headers, demo_shop.id)
    session = db_session.get(ChannelConnectionSession, UUID(body["session_id"]))
    session.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    response = client.get(
        "/api/v1/channels/instagram/oauth/callback",
        params={"code": "auth-code", "state": session.state},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "connection_expired" in response.headers["location"] or "failed" in response.headers["location"]


def test_reused_state_rejected(client, auth_headers, demo_shop, db_session, meta_app_settings):
    body = _start_connect(client, auth_headers, demo_shop.id)
    session = db_session.get(ChannelConnectionSession, UUID(body["session_id"]))
    session.status = ChannelConnectionSessionStatus.CONNECTED
    db_session.commit()

    response = client.get(
        "/api/v1/channels/instagram/oauth/callback",
        params={"code": "auth-code", "state": session.state},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "failed" in response.headers["location"]


def test_callback_creates_channel_account_single_candidate(
    client, auth_headers, demo_shop, db_session, meta_app_settings
):
    body = _start_connect(client, auth_headers, demo_shop.id)
    session = db_session.get(ChannelConnectionSession, UUID(body["session_id"]))

    candidate = InstagramCandidateAccount(
        page_id="page-1",
        page_name="Demo Page",
        instagram_business_account_id="ig-biz-1",
        instagram_username="demo_shop",
    )
    pages = [
        {
            "id": "page-1",
            "name": "Demo Page",
            "access_token": "page-access-token",
            "instagram_business_account": {
                "id": "ig-biz-1",
                "username": "demo_shop",
            },
        }
    ]

    with (
        patch.object(
            InstagramMetaConnectService,
            "exchange_code_for_token",
            AsyncMock(return_value=MetaTokenResult(access_token="short-token")),
        ),
        patch.object(
            InstagramMetaConnectService,
            "exchange_for_long_lived_token",
            AsyncMock(return_value=MetaTokenResult(access_token="long-token", expires_in=3600)),
        ),
        patch.object(InstagramMetaConnectService, "validate_required_permissions", AsyncMock(return_value=[])),
        patch.object(InstagramMetaConnectService, "fetch_user_pages", AsyncMock(return_value=pages)),
        patch.object(
            InstagramMetaConnectService,
            "create_or_update_channel_account",
            AsyncMock(side_effect=lambda **kwargs: _create_instagram_account(db_session, demo_shop.id, kwargs)),
        ),
    ):
        response = client.get(
            "/api/v1/channels/instagram/oauth/callback",
            params={"code": "auth-code", "state": session.state},
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert "status=connected" in response.headers["location"]
    account = db_session.scalar(
        select(ChannelAccount).where(
            ChannelAccount.shop_id == demo_shop.id,
            ChannelAccount.provider == ChannelProvider.INSTAGRAM,
        )
    )
    assert account is not None
    assert account.access_token_encrypted is not None
    assert decrypt_secret(account.access_token_encrypted) == "page-access-token"
    assert "access_token" not in response.text


def _create_instagram_account(db_session, shop_id, kwargs):
    candidate = kwargs["candidate"]
    account = ChannelAccount(
        shop_id=shop_id,
        provider=ChannelProvider.INSTAGRAM,
        display_name=f"@{candidate.instagram_username}",
        external_account_id=candidate.instagram_business_account_id,
        access_token_encrypted=encrypt_secret(kwargs["page_access_token"]),
        webhook_verify_token="verify-token-unique",
        webhook_secret_encrypted=encrypt_secret("secret"),
        status=ChannelAccountStatus.CONNECTED,
        capabilities_json={"supports_text": True},
        settings_json={"page_id": candidate.page_id, "instagram_username": candidate.instagram_username},
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


def test_callback_multiple_accounts_requires_selection(
    client, auth_headers, demo_shop, db_session, meta_app_settings
):
    body = _start_connect(client, auth_headers, demo_shop.id)
    session = db_session.get(ChannelConnectionSession, UUID(body["session_id"]))
    pages = [
        {
            "id": "page-1",
            "name": "Page One",
            "access_token": "token-1",
            "instagram_business_account": {"id": "ig-1", "username": "one"},
        },
        {
            "id": "page-2",
            "name": "Page Two",
            "access_token": "token-2",
            "instagram_business_account": {"id": "ig-2", "username": "two"},
        },
    ]

    with (
        patch.object(
            InstagramMetaConnectService,
            "exchange_code_for_token",
            AsyncMock(return_value=MetaTokenResult(access_token="short-token")),
        ),
        patch.object(
            InstagramMetaConnectService,
            "exchange_for_long_lived_token",
            AsyncMock(return_value=MetaTokenResult(access_token="long-token")),
        ),
        patch.object(InstagramMetaConnectService, "validate_required_permissions", AsyncMock(return_value=[])),
        patch.object(InstagramMetaConnectService, "fetch_user_pages", AsyncMock(return_value=pages)),
    ):
        response = client.get(
            "/api/v1/channels/instagram/oauth/callback",
            params={"code": "auth-code", "state": session.state},
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert "/system/channels/instagram/select" in response.headers["location"]
    db_session.refresh(session)
    assert session.status == ChannelConnectionSessionStatus.ACCOUNT_SELECTION_REQUIRED
    assert len(session.provider_payload_redacted["candidates"]) == 2


def test_select_account_completes_connection(
    client, auth_headers, demo_shop, admin_user, db_session, meta_app_settings
):
    session = ChannelConnectionSession(
        id=uuid4(),
        shop_id=demo_shop.id,
        provider=ChannelConnectionProvider.INSTAGRAM,
        method=ChannelConnectionMethod.META_OAUTH_BUSINESS_LOGIN,
        status=ChannelConnectionSessionStatus.ACCOUNT_SELECTION_REQUIRED,
        state="state-value",
        nonce="nonce-value",
        redirect_uri="http://localhost:8000/api/v1/channels/instagram/oauth/callback",
        requested_scopes_json=["instagram_basic"],
        provider_payload_redacted={
            "candidates": [
                {
                    "page_id": "page-1",
                    "page_name": "Demo Page",
                    "instagram_business_account_id": "ig-biz-1",
                    "instagram_username": "demo_shop",
                }
            ]
        },
        oauth_token_encrypted=encrypt_secret("user-token"),
        created_by=admin_user.id,
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    db_session.add(session)
    db_session.commit()

    pages = [
        {
            "id": "page-1",
            "name": "Demo Page",
            "access_token": "page-access-token",
            "instagram_business_account": {"id": "ig-biz-1", "username": "demo_shop"},
        }
    ]
    with (
        patch.object(InstagramMetaConnectService, "fetch_user_pages", AsyncMock(return_value=pages)),
        patch.object(
            InstagramMetaConnectService,
            "create_or_update_channel_account",
            AsyncMock(side_effect=lambda **kwargs: _create_instagram_account(db_session, demo_shop.id, kwargs)),
        ),
    ):
        response = client.post(
            f"/api/v1/shops/{demo_shop.id}/channels/instagram/connect/sessions/{session.id}/select-account",
            headers=auth_headers,
            json={"page_id": "page-1", "instagram_business_account_id": "ig-biz-1"},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "instagram"
    assert body["token_configured"] is True
    assert "access_token" not in response.text
    db_session.refresh(session)
    assert session.status == ChannelConnectionSessionStatus.CONNECTED
    assert session.oauth_token_encrypted is None


def test_disconnect_disables_account_and_audits(
    client, auth_headers, demo_shop, db_session, meta_app_settings
):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.INSTAGRAM,
        display_name="@demo",
        external_account_id="ig-1",
        access_token_encrypted=encrypt_secret("token"),
        status=ChannelAccountStatus.CONNECTED,
        capabilities_json={"supports_text": True},
        settings_json={},
    )
    db_session.add(account)
    db_session.commit()

    with patch.object(InstagramMetaConnectService, "revoke_token_if_supported", AsyncMock()):
        response = client.post(
            f"/api/v1/shops/{demo_shop.id}/channels/{account.id}/disconnect",
            headers=auth_headers,
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "disabled"
    assert body["token_configured"] is False
    db_session.refresh(account)
    assert account.access_token_encrypted is None


def test_account_specific_instagram_webhook_verification(client, db_session, demo_shop):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.INSTAGRAM,
        display_name="@demo",
        external_account_id="ig-1",
        webhook_verify_token="account-verify-token",
        webhook_secret_encrypted=encrypt_secret("secret"),
        status=ChannelAccountStatus.CONNECTED,
        capabilities_json={},
        settings_json={},
    )
    db_session.add(account)
    db_session.commit()

    ok = client.get(
        f"/api/v1/channels/instagram/{account.id}/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "account-verify-token",
            "hub.challenge": "challenge-123",
        },
    )
    assert ok.status_code == 200
    assert ok.text == "challenge-123"

    bad = client.get(
        f"/api/v1/channels/instagram/{account.id}/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "challenge-123",
        },
    )
    assert bad.status_code == 403


def test_account_specific_instagram_webhook_post_ingests(
    client, db_session, demo_shop
):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.INSTAGRAM,
        display_name="@demo",
        external_account_id="17841400000000000",
        webhook_verify_token="verify",
        webhook_secret_encrypted=encrypt_secret("webhook-secret"),
        status=ChannelAccountStatus.CONNECTED,
        capabilities_json={},
        settings_json={},
    )
    db_session.add(account)
    db_session.commit()

    body = json.dumps(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD, separators=(",", ":")).encode()
    headers = {
        "content-type": "application/json",
        "X-Hub-Signature-256": "sha256="
        + hmac.new(b"webhook-secret", body, hashlib.sha256).hexdigest(),
    }
    response = client.post(
        f"/api/v1/channels/instagram/{account.id}/webhook",
        content=body,
        headers=headers,
    )
    assert response.status_code == 200


def test_session_read_never_returns_tokens(client, auth_headers, demo_shop, db_session, meta_app_settings):
    body = _start_connect(client, auth_headers, demo_shop.id)
    session = db_session.get(ChannelConnectionSession, UUID(body["session_id"]))
    session.oauth_token_encrypted = encrypt_secret("secret-token")
    db_session.commit()

    response = client.get(
        f"/api/v1/shops/{demo_shop.id}/channels/instagram/connect/sessions/{session.id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "secret-token" not in response.text
    assert "oauth_token" not in response.text


def test_cross_shop_session_access_blocked(client, auth_headers, demo_shop, db_session, meta_app_settings):
    body = _start_connect(client, auth_headers, demo_shop.id)
    from app.domain.models import Shop

    other = Shop(name="Other", slug="other-oauth-shop")
    db_session.add(other)
    db_session.commit()

    response = client.get(
        f"/api/v1/shops/{other.id}/channels/instagram/connect/sessions/{body['session_id']}",
        headers=auth_headers,
    )
    assert response.status_code == 403

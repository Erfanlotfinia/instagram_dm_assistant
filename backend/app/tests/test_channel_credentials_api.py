from uuid import UUID

from app.core.log_masking import mask_dict, mask_string
from app.core.security import decrypt_secret
from app.domain.enums import UserRole
from app.domain.models import ShopMember
from app.services.auth_service import AuthService


def _create_channel(client, auth_headers, shop_id):
    response = client.post(
        f"/api/v1/shops/{shop_id}/channels",
        headers=auth_headers,
        json={"provider": "telegram", "display_name": "Shop bot", "bot_username": "shop_bot"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_channel_create_and_credentials_are_write_only(client, auth_headers, demo_shop, db_session):
    channel = _create_channel(client, auth_headers, demo_shop.id)
    assert "capabilities_json" in channel
    assert "settings_json" in channel
    assert "capabilities" not in channel
    assert "settings" not in channel
    assert channel["token_configured"] is False
    assert channel["bot_token_configured"] is False

    raw_token = "123456789:super-secret-bot-token"
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/{channel['id']}/credentials",
        headers=auth_headers,
        json={"bot_token": raw_token, "webhook_secret": "webhook-secret-value"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["bot_token_configured"] is True
    assert body["webhook_secret_configured"] is True
    assert raw_token not in response.text
    assert not any("encrypted" in key for key in body)

    from app.domain.models import ChannelAccount

    account = db_session.get(ChannelAccount, UUID(channel["id"]))
    assert account.bot_token_encrypted != raw_token
    assert decrypt_secret(account.bot_token_encrypted) == raw_token


def test_validation_rejects_missing_provider_credentials(client, auth_headers, demo_shop):
    channel = _create_channel(client, auth_headers, demo_shop.id)
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/{channel['id']}/validate",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "error"
    assert body["last_error"] == "Missing required channel configuration: bot_token"


def test_cross_shop_channel_access_is_blocked(client, auth_headers, demo_shop, db_session):
    channel = _create_channel(client, auth_headers, demo_shop.id)
    from app.domain.models import Shop

    other = Shop(name="Other", slug="other-channel-shop")
    db_session.add(other)
    db_session.commit()

    response = client.get(
        f"/api/v1/shops/{other.id}/channels/{channel['id']}", headers=auth_headers
    )
    assert response.status_code == 403


def test_operator_cannot_update_credentials(client, admin_user, demo_shop, db_session):
    operator = AuthService.create_user(db_session, email="operator-channel@test.com", password="password123", full_name="Operator", role=UserRole.OPERATOR)
    db_session.add(ShopMember(shop_id=demo_shop.id, user_id=operator.id, role=UserRole.OPERATOR))
    db_session.commit()
    login = client.post("/api/v1/auth/login", json={"email": operator.email, "password": "password123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Create as owner, then attempt the secret write as operator.
    owner_login = client.post("/api/v1/auth/login", json={"email": admin_user.email, "password": "password123"})
    owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}
    channel = _create_channel(client, owner_headers, demo_shop.id)
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/{channel['id']}/credentials",
        headers=headers,
        json={"bot_token": "must-not-save"},
    )
    assert response.status_code == 403


def test_log_masking_redacts_channel_credentials():
    secret = "123456789:telegram-looking-secret-token"
    masked = mask_dict({"bot_token": secret, "webhook_secret_encrypted": secret})
    assert secret not in str(masked)
    assert mask_string(f"Authorization: Bearer {secret}") == "Authorization: Bearer [REDACTED]"

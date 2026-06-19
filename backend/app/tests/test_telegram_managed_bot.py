"""Telegram managed bot provisioning tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID

import pytest

from app.core.config import get_settings
from app.core.security import decrypt_secret, encrypt_secret
from app.domain.enums import (
    ChannelAccountStatus,
    ChannelProvider,
    TelegramConnectionMode,
    TelegramConnectionSessionStatus,
)
from app.domain.models import ChannelAccount, TelegramConnectionSession
from app.services.channel_account_service import ChannelAccountService
from app.services.telegram_managed_bot_service import (
    build_newbot_deep_link,
    suggest_bot_username,
)

FIXTURES = Path(__file__).parent / "fixtures" / "channels"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture()
def manager_bot_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_MANAGER_BOT_TOKEN", "999:MANAGER")
    monkeypatch.setenv("TELEGRAM_MANAGER_BOT_USERNAME", "modira_manager_bot")
    monkeypatch.setenv("TELEGRAM_MANAGER_BOT_ID", "999")
    monkeypatch.setenv("TELEGRAM_MANAGER_WEBHOOK_SECRET", "mgr-wh-sec")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_suggest_bot_username_format(demo_shop):
    username = suggest_bot_username(demo_shop.id, "My Shop Bot!")
    assert username.endswith("_bot")
    assert len(username) <= 32
    assert username == username.lower()
    assert all(ch.isalnum() or ch == "_" for ch in username)


def test_build_newbot_deep_link(manager_bot_env, demo_shop):
    username = suggest_bot_username(demo_shop.id, "Telegram")
    link = build_newbot_deep_link(username, "Telegram")
    assert link.startswith("https://t.me/newbot/modira_manager_bot/")
    assert username in link
    assert "name=Telegram" in link


def test_start_managed_session(client, auth_headers, db_session, demo_shop, manager_bot_env):
    start = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/telegram/connect/start",
        json={"mode": "bot", "display_name": "Telegram", "managed_bot": True},
        headers=auth_headers,
    )
    assert start.status_code == 200
    body = start.json()
    assert body["status"] == "waiting_managed_bot_approval"
    assert body["managed_bot"] is True
    assert body["deep_link"].startswith("https://t.me/newbot/modira_manager_bot/")
    assert body["suggested_bot_username"]

    session = db_session.get(TelegramConnectionSession, UUID(body["session_id"]))
    assert session is not None
    assert session.status == TelegramConnectionSessionStatus.WAITING_MANAGED_BOT_APPROVAL
    assert session.metadata_json.get("managed_bot") is True


def test_start_managed_session_requires_config(client, auth_headers, demo_shop, monkeypatch):
    monkeypatch.delenv("TELEGRAM_MANAGER_BOT_TOKEN", raising=False)
    get_settings.cache_clear()
    start = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/telegram/connect/start",
        json={"mode": "bot", "managed_bot": True},
        headers=auth_headers,
    )
    assert start.status_code == 503
    get_settings.cache_clear()


def test_manager_webhook_completes_session(
    client, auth_headers, db_session, demo_shop, manager_bot_env, monkeypatch
):
    start = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/telegram/connect/start",
        json={"mode": "bot", "display_name": "Telegram", "managed_bot": True},
        headers=auth_headers,
    )
    session_id = start.json()["session_id"]
    suggested_username = start.json()["suggested_bot_username"]

    payload = _load("telegram_managed_bot_updated.json")
    payload["managed_bot"]["bot"]["username"] = suggested_username

    async def fake_get_token(self, user_id: int) -> str:
        assert user_id == payload["managed_bot"]["bot"]["id"]
        return "888001:MANAGED_TOKEN"

    async def fake_validate(self, account=None):
        return True

    async def fake_sync(self, account):
        account.bot_username = suggested_username
        account.bot_id = str(payload["managed_bot"]["bot"]["id"])
        return {}

    async def fake_register(self, account):
        account.webhook_url = "https://example.com/webhook"
        account.status = ChannelAccountStatus.WEBHOOK_CONFIGURED

    from app.channels.telegram.bot import TelegramBotAdapter
    from app.channels.telegram.manager import TelegramManagerBotClient
    from app.services.telegram_connect_service import TelegramConnectService

    monkeypatch.setattr(TelegramManagerBotClient, "get_managed_bot_token", fake_get_token)
    monkeypatch.setattr(TelegramBotAdapter, "validate_connection", fake_validate)
    monkeypatch.setattr(TelegramBotAdapter, "sync_metadata", fake_sync)
    monkeypatch.setattr(TelegramConnectService, "_register_webhook", fake_register)

    response = client.post(
        "/api/v1/channels/telegram/manager/webhook",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": "mgr-wh-sec"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    session = db_session.get(TelegramConnectionSession, UUID(session_id))
    assert session.status == TelegramConnectionSessionStatus.CONNECTED
    account = db_session.get(ChannelAccount, session.channel_account_id)
    assert account is not None
    assert account.managed_bot is True
    assert account.manager_bot_id == "999"
    assert account.managed_bot_id == "888001"
    assert decrypt_secret(account.bot_token_encrypted) == "888001:MANAGED_TOKEN"
    assert account.bot_username == suggested_username


def test_token_not_exposed_in_api_response(
    client, auth_headers, db_session, demo_shop, manager_bot_env, monkeypatch
):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="Managed TG",
        connection_mode=TelegramConnectionMode.BOT,
        managed_bot=True,
        manager_bot_id="999",
        managed_bot_id="888001",
        bot_token_encrypted=encrypt_secret("secret-token"),
        bot_username="modira_demo_bot",
        status=ChannelAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.commit()

    listed = client.get(
        f"/api/v1/shops/{demo_shop.id}/channels",
        headers=auth_headers,
    )
    assert listed.status_code == 200
    body = listed.json()
    telegram = next(item for item in body if item["provider"] == "telegram")
    assert telegram["bot_token_configured"] is True
    assert "bot_token" not in telegram
    assert "bot_token_encrypted" not in telegram
    assert telegram["managed_bot"] is True


def test_rotate_managed_bot_token(
    client, auth_headers, db_session, demo_shop, manager_bot_env, monkeypatch
):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="Managed TG",
        connection_mode=TelegramConnectionMode.BOT,
        managed_bot=True,
        manager_bot_id="999",
        managed_bot_id="888001",
        bot_token_encrypted=encrypt_secret("old-token"),
        webhook_secret_encrypted=encrypt_secret("wh-sec"),
        status=ChannelAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.commit()

    async def fake_replace(self, user_id: int) -> str:
        assert user_id == 888001
        return "888001:NEW_TOKEN"

    async def fake_validate(self, account=None):
        return True

    async def fake_sync(self, account):
        return {}

    register_called: list[str] = []

    async def fake_register(self, account):
        register_called.append("called")
        account.webhook_url = "https://example.com/webhook"
        account.status = ChannelAccountStatus.WEBHOOK_CONFIGURED

    from app.channels.telegram.bot import TelegramBotAdapter
    from app.channels.telegram.manager import TelegramManagerBotClient
    from app.services.telegram_connect_service import TelegramConnectService

    monkeypatch.setattr(TelegramManagerBotClient, "replace_managed_bot_token", fake_replace)
    monkeypatch.setattr(TelegramBotAdapter, "validate_connection", fake_validate)
    monkeypatch.setattr(TelegramBotAdapter, "sync_metadata", fake_sync)
    monkeypatch.setattr(TelegramConnectService, "_register_webhook", fake_register)

    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/{account.id}/telegram/managed-bot/rotate-token",
        headers=auth_headers,
    )
    assert response.status_code == 200
    db_session.refresh(account)
    assert decrypt_secret(account.bot_token_encrypted) == "888001:NEW_TOKEN"
    assert register_called == ["called"]


def test_reconnect_managed_bot(
    client, auth_headers, db_session, demo_shop, manager_bot_env, monkeypatch
):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="Managed TG",
        connection_mode=TelegramConnectionMode.BOT,
        managed_bot=True,
        manager_bot_id="999",
        managed_bot_id="888001",
        bot_token_encrypted=encrypt_secret("stale-token"),
        webhook_secret_encrypted=encrypt_secret("wh-sec"),
        status=ChannelAccountStatus.ERROR,
        last_error="validation failed",
    )
    db_session.add(account)
    db_session.commit()

    async def fake_get_token(self, user_id: int) -> str:
        return "888001:REFRESHED_TOKEN"

    async def fake_validate(self, account=None):
        return True

    async def fake_sync(self, account):
        return {}

    async def fake_register(self, account):
        account.webhook_url = "https://example.com/webhook"
        account.status = ChannelAccountStatus.WEBHOOK_CONFIGURED

    from app.channels.telegram.bot import TelegramBotAdapter
    from app.channels.telegram.manager import TelegramManagerBotClient
    from app.services.telegram_connect_service import TelegramConnectService

    monkeypatch.setattr(TelegramManagerBotClient, "get_managed_bot_token", fake_get_token)
    monkeypatch.setattr(TelegramBotAdapter, "validate_connection", fake_validate)
    monkeypatch.setattr(TelegramBotAdapter, "sync_metadata", fake_sync)
    monkeypatch.setattr(TelegramConnectService, "_register_webhook", fake_register)

    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/{account.id}/telegram/managed-bot/reconnect",
        headers=auth_headers,
    )
    assert response.status_code == 200
    db_session.refresh(account)
    assert decrypt_secret(account.bot_token_encrypted) == "888001:REFRESHED_TOKEN"
    assert account.last_error is None


def test_rotate_rejected_for_non_managed(client, auth_headers, db_session, demo_shop, manager_bot_env):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="Manual TG",
        connection_mode=TelegramConnectionMode.BOT,
        managed_bot=False,
        bot_token_encrypted=encrypt_secret("manual"),
        status=ChannelAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.commit()

    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/{account.id}/telegram/managed-bot/rotate-token",
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_disconnect_clears_managed_fields(db_session, demo_shop, admin_user):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="Managed TG",
        connection_mode=TelegramConnectionMode.BOT,
        managed_bot=True,
        manager_bot_id="999",
        managed_bot_id="888001",
        bot_token_encrypted=encrypt_secret("token"),
        status=ChannelAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.commit()

    await ChannelAccountService(db_session).disconnect(account, admin_user.id)
    db_session.refresh(account)
    assert account.managed_bot is False
    assert account.manager_bot_id is None
    assert account.managed_bot_id is None
    assert account.bot_token_encrypted is None

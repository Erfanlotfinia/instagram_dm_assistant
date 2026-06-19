"""Telegram multi-mode connection tests."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select

from app.core.security import decrypt_secret, encrypt_secret
from app.domain.enums import (
    ChannelAccountStatus,
    ChannelMessageType,
    ChannelProvider,
    MessageDirection,
    MessageType,
    TelegramConnectionMode,
    TelegramConnectionSessionStatus,
)
from app.domain.models import (
    AdminAuditLog,
    ChannelAccount,
    ChannelMessage,
    Conversation,
    Message,
    TelegramConnectionSession,
)
from app.services.channel_account_service import adapter_for_provider
from app.services.channel_webhook_ingestion_service import ChannelWebhookIngestionService
from app.services.telegram_business_connection_service import TelegramBusinessConnectionService
from app.schemas.channels import NormalizedOutboundMessage

FIXTURES = Path(__file__).parent / "fixtures" / "channels"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_telegram_bot_adapter_parse_text():
    adapter = adapter_for_provider(
        ChannelProvider.TELEGRAM,
        ChannelAccount(
            provider=ChannelProvider.TELEGRAM,
            connection_mode=TelegramConnectionMode.BOT,
        ),
    )
    payload = _load("telegram_text.json")
    messages = adapter.parse_inbound_update(payload)
    assert len(messages) == 1
    assert messages[0].text == payload["message"]["text"]


@pytest.mark.asyncio
async def test_telegram_business_adapter_outbound_includes_connection_id(db_session, demo_shop):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="TG Business",
        connection_mode=TelegramConnectionMode.BUSINESS,
        bot_token_encrypted=encrypt_secret("test-token"),
        telegram_business_connection_id="biz-conn-1",
        telegram_business_enabled=True,
        status=ChannelAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.commit()

    adapter = adapter_for_provider(ChannelProvider.TELEGRAM, account)
    called: list[dict] = []

    async def fake_post(method: str, payload: dict):
        called.append({"method": method, "payload": payload})
        from app.schemas.channels import ProviderSendResult

        return ProviderSendResult(provider=ChannelProvider.TELEGRAM, success=True, raw_response={"ok": True})

    adapter._post_method = fake_post  # type: ignore[method-assign]
    message = NormalizedOutboundMessage(
        provider=ChannelProvider.TELEGRAM,
        channel_account_id=account.id,
        external_chat_id="123",
        text="hi",
    )
    result = await adapter.send_message(message, account)
    assert result.success
    assert called[0]["method"] == "sendMessage"
    assert called[0]["payload"]["business_connection_id"] == "biz-conn-1"


@pytest.mark.asyncio
async def test_telegram_hybrid_outbound_fallback(db_session, demo_shop):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="TG Hybrid",
        connection_mode=TelegramConnectionMode.HYBRID,
        bot_token_encrypted=encrypt_secret("test-token"),
        telegram_business_connection_id="biz-conn-1",
        telegram_business_enabled=True,
        status=ChannelAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.commit()

    adapter = adapter_for_provider(ChannelProvider.TELEGRAM, account)
    calls: list[str] = []

    async def business_fail(message, account=None):
        from app.schemas.channels import ProviderSendResult

        calls.append("business")
        return ProviderSendResult(
            provider=ChannelProvider.TELEGRAM,
            success=False,
            error_code="500",
            retryable=True,
        )

    async def bot_ok(message, account=None):
        from app.schemas.channels import ProviderSendResult

        calls.append("bot")
        return ProviderSendResult(provider=ChannelProvider.TELEGRAM, success=True)

    adapter._business.send_message = business_fail  # type: ignore[method-assign]
    adapter._bot.send_message = bot_ok  # type: ignore[method-assign]

    message = NormalizedOutboundMessage(
        provider=ChannelProvider.TELEGRAM,
        channel_account_id=account.id,
        external_chat_id="123",
        text="hi",
    )
    result = await adapter.send_message(message, account)
    assert result.success
    assert calls == ["business", "bot"]


def test_business_connection_webhook_updates_account(db_session, demo_shop, client):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="TG",
        connection_mode=TelegramConnectionMode.BUSINESS,
        bot_token_encrypted=encrypt_secret("token"),
        webhook_secret_encrypted=encrypt_secret("secret"),
        status=ChannelAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.commit()

    payload = _load("telegram_business_connection.json")
    response = client.post(
        f"/api/v1/channels/telegram/{account.id}/webhook",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
    )
    assert response.status_code == 200
    db_session.refresh(account)
    assert account.telegram_business_connection_id == "biz-conn-1"
    assert account.telegram_business_enabled is True
    assert account.telegram_rights_json.get("can_reply") is True
    assert account.telegram_chat_id == "123456789"
    assert account.telegram_username == "shop_owner"


def test_business_connection_disabled_disables_account(db_session, demo_shop, client):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="TG",
        connection_mode=TelegramConnectionMode.BUSINESS,
        bot_token_encrypted=encrypt_secret("token"),
        webhook_secret_encrypted=encrypt_secret("secret"),
        telegram_business_connection_id="biz-conn-1",
        telegram_business_enabled=True,
        status=ChannelAccountStatus.WEBHOOK_CONFIGURED,
    )
    db_session.add(account)
    db_session.commit()

    payload = _load("telegram_business_connection.json")
    payload["business_connection"]["is_enabled"] = False
    response = client.post(
        f"/api/v1/channels/telegram/{account.id}/webhook",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
    )
    assert response.status_code == 200
    db_session.refresh(account)
    assert account.telegram_business_enabled is False
    assert account.status == ChannelAccountStatus.DISABLED
    assert account.telegram_business_connection_id == "biz-conn-1"
    audit = db_session.query(AdminAuditLog).filter_by(action="telegram_business_disabled").one()
    assert audit.entity_id == str(account.id)


def test_business_connection_reenabled_restores_account(db_session, demo_shop):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="TG",
        connection_mode=TelegramConnectionMode.BUSINESS,
        bot_token_encrypted=encrypt_secret("token"),
        telegram_business_connection_id="biz-conn-1",
        telegram_business_enabled=False,
        status=ChannelAccountStatus.DISABLED,
        last_error="Telegram Business connection disabled",
    )
    db_session.add(account)
    db_session.commit()

    payload = _load("telegram_business_connection.json")
    TelegramBusinessConnectionService(db_session).connect(account, payload["business_connection"])
    db_session.refresh(account)
    assert account.telegram_business_enabled is True
    assert account.status == ChannelAccountStatus.WEBHOOK_CONFIGURED
    assert account.last_error is None


def test_business_message_ingestion_e2e(db_session, demo_shop):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="TG Business",
        connection_mode=TelegramConnectionMode.BUSINESS,
        bot_token_encrypted=encrypt_secret("token"),
        telegram_business_connection_id="biz-conn-1",
        telegram_business_enabled=True,
        status=ChannelAccountStatus.WEBHOOK_CONFIGURED,
    )
    db_session.add(account)
    db_session.commit()

    payload = _load("telegram_business_message.json")
    result = ChannelWebhookIngestionService(db_session).handle_payload(
        ChannelProvider.TELEGRAM,
        payload,
        {},
        shop_id=account.shop_id,
        channel_account_id=account.id,
    )
    assert result.dedupe_outcome == "processed"
    channel_message = db_session.scalar(
        select(ChannelMessage).where(ChannelMessage.channel_account_id == account.id)
    )
    assert channel_message is not None
    assert channel_message.text == "Hello from business chat"


def test_edited_business_message_updates_text(db_session, demo_shop):
    from app.domain.models import ChannelConversation

    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="TG",
        connection_mode=TelegramConnectionMode.BUSINESS,
        bot_token_encrypted=encrypt_secret("token"),
        status=ChannelAccountStatus.WEBHOOK_CONFIGURED,
    )
    db_session.add(account)
    db_session.flush()

    from app.domain.models import Customer

    customer = Customer(shop_id=demo_shop.id, full_name="Customer")
    db_session.add(customer)
    db_session.flush()

    conversation = Conversation(
        shop_id=demo_shop.id,
        channel_account_id=account.id,
        channel_provider=ChannelProvider.TELEGRAM.value,
        external_conversation_id="987654321",
        customer_id=customer.id,
    )
    db_session.add(conversation)
    db_session.flush()

    internal = Message(
        shop_id=demo_shop.id,
        conversation_id=conversation.id,
        channel_account_id=account.id,
        channel_provider=ChannelProvider.TELEGRAM,
        direction=MessageDirection.INBOUND,
        message_type=MessageType.TEXT,
        text="Hello from business chat",
        content="Hello from business chat",
        external_message_id="42",
    )
    db_session.add(internal)
    db_session.flush()

    channel_message = ChannelMessage(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        channel_account_id=account.id,
        conversation_id=conversation.id,
        external_message_id="42",
        direction=MessageDirection.INBOUND,
        message_type=ChannelMessageType.TEXT,
        text="Hello from business chat",
        internal_message_id=internal.id,
        idempotency_key="tg:42",
    )
    db_session.add(channel_message)
    db_session.commit()

    payload = {
        "update_id": 900003,
        "edited_business_message": {
            "business_connection_id": "biz-conn-1",
            "message_id": 42,
            "chat": {"id": 987654321, "type": "private"},
            "text": "Edited hello",
        },
    }
    ChannelWebhookIngestionService(db_session).handle_payload(
        ChannelProvider.TELEGRAM,
        payload,
        {},
        shop_id=account.shop_id,
        channel_account_id=account.id,
    )
    db_session.refresh(internal)
    db_session.refresh(channel_message)
    assert internal.text == "Edited hello"
    assert channel_message.text == "Edited hello"


def test_deleted_business_messages_soft_delete(db_session, demo_shop):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="TG",
        connection_mode=TelegramConnectionMode.BUSINESS,
        bot_token_encrypted=encrypt_secret("token"),
        status=ChannelAccountStatus.WEBHOOK_CONFIGURED,
    )
    db_session.add(account)
    db_session.flush()

    from app.domain.models import Customer

    customer = Customer(shop_id=demo_shop.id, full_name="Customer")
    db_session.add(customer)
    db_session.flush()

    conversation = Conversation(
        shop_id=demo_shop.id,
        channel_account_id=account.id,
        channel_provider=ChannelProvider.TELEGRAM.value,
        external_conversation_id="987654321",
        customer_id=customer.id,
    )
    db_session.add(conversation)
    db_session.flush()

    internal = Message(
        shop_id=demo_shop.id,
        conversation_id=conversation.id,
        channel_account_id=account.id,
        channel_provider=ChannelProvider.TELEGRAM,
        direction=MessageDirection.INBOUND,
        message_type=MessageType.TEXT,
        text="To delete",
        content="To delete",
        external_message_id="99",
    )
    db_session.add(internal)
    db_session.flush()

    channel_message = ChannelMessage(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        channel_account_id=account.id,
        conversation_id=conversation.id,
        external_message_id="99",
        direction=MessageDirection.INBOUND,
        message_type=ChannelMessageType.TEXT,
        text="To delete",
        internal_message_id=internal.id,
        idempotency_key="tg:99",
        raw_payload_json={},
    )
    db_session.add(channel_message)
    db_session.commit()

    payload = {
        "update_id": 900004,
        "deleted_business_messages": {
            "business_connection_id": "biz-conn-1",
            "chat": {"id": 987654321},
            "message_ids": [99],
        },
    }
    ChannelWebhookIngestionService(db_session).handle_payload(
        ChannelProvider.TELEGRAM,
        payload,
        {},
        shop_id=account.shop_id,
        channel_account_id=account.id,
    )
    db_session.refresh(channel_message)
    assert channel_message.raw_payload_json.get("deleted") is True


def test_telegram_connect_start_and_bot_token(client, auth_headers, db_session, demo_shop, monkeypatch):
    start = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/telegram/connect/start",
        json={"mode": "bot", "display_name": "Test Bot"},
        headers=auth_headers,
    )
    assert start.status_code == 200
    session_id = start.json()["session_id"]

    session = db_session.get(TelegramConnectionSession, UUID(session_id))
    assert session is not None
    assert session.status == TelegramConnectionSessionStatus.WAITING_BOT_TOKEN

    async def fake_validate(self, account=None):
        return True

    async def fake_sync(self, account):
        account.bot_username = "testbot"
        account.bot_id = "999"
        return {}

    from app.channels.telegram.bot import TelegramBotAdapter

    monkeypatch.setattr(TelegramBotAdapter, "validate_connection", fake_validate)
    monkeypatch.setattr(TelegramBotAdapter, "sync_metadata", fake_sync)

    submit = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/telegram/connect/{session_id}/bot-token",
        json={"bot_token": "123:ABC", "webhook_secret": "wh-sec"},
        headers=auth_headers,
    )
    assert submit.status_code == 200
    body = submit.json()
    assert body["status"] == "connected"
    account = db_session.get(ChannelAccount, UUID(body["channel_account_id"]))
    assert account is not None
    assert decrypt_secret(account.bot_token_encrypted) == "123:ABC"


def test_business_mode_bot_token_submit_without_connection(
    client, auth_headers, db_session, demo_shop, monkeypatch
):
    start = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/telegram/connect/start",
        json={"mode": "business", "display_name": "Business TG"},
        headers=auth_headers,
    )
    assert start.status_code == 200
    session_id = start.json()["session_id"]

    async def fake_validate(self, account=None):
        return True

    async def fake_sync(self, account):
        account.bot_username = "bizbot"
        account.bot_id = "888"
        return {}

    async def fake_register(self, account):
        account.webhook_url = "https://example.com/webhook"
        account.status = ChannelAccountStatus.WEBHOOK_CONFIGURED

    from app.channels.telegram.bot import TelegramBotAdapter
    from app.services.telegram_connect_service import TelegramConnectService

    monkeypatch.setattr(TelegramBotAdapter, "validate_connection", fake_validate)
    monkeypatch.setattr(TelegramBotAdapter, "sync_metadata", fake_sync)
    monkeypatch.setattr(TelegramConnectService, "_register_webhook", fake_register)

    submit = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/telegram/connect/{session_id}/bot-token",
        json={"bot_token": "123:ABC", "webhook_secret": "wh-sec"},
        headers=auth_headers,
    )
    assert submit.status_code == 200
    body = submit.json()
    assert body["status"] == "waiting_business_connection"


def test_business_connect_e2e(client, auth_headers, db_session, demo_shop, monkeypatch):
    start = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/telegram/connect/start",
        json={"mode": "business", "display_name": "Biz"},
        headers=auth_headers,
    )
    session_id = start.json()["session_id"]

    async def fake_validate(self, account=None):
        return True

    async def fake_sync(self, account):
        account.bot_username = "bizbot"
        return {}

    async def fake_register(self, account):
        account.webhook_url = "https://example.com/webhook"
        account.status = ChannelAccountStatus.WEBHOOK_CONFIGURED

    from app.channels.telegram.bot import TelegramBotAdapter
    from app.services.telegram_connect_service import TelegramConnectService

    monkeypatch.setattr(TelegramBotAdapter, "validate_connection", fake_validate)
    monkeypatch.setattr(TelegramBotAdapter, "sync_metadata", fake_sync)
    monkeypatch.setattr(TelegramConnectService, "_register_webhook", fake_register)

    submit = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/telegram/connect/{session_id}/bot-token",
        json={"bot_token": "123:ABC", "webhook_secret": "wh-sec"},
        headers=auth_headers,
    )
    account_id = submit.json()["channel_account_id"]
    account = db_session.get(ChannelAccount, UUID(account_id))
    assert account is not None

    payload = _load("telegram_business_connection.json")
    client.post(
        f"/api/v1/channels/telegram/{account.id}/webhook",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": "wh-sec"},
    )
    db_session.refresh(account)
    session = db_session.get(TelegramConnectionSession, UUID(session_id))
    assert session.status == TelegramConnectionSessionStatus.CONNECTED
    assert account.telegram_business_enabled is True

    complete = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/telegram/connect/{session_id}/complete",
        headers=auth_headers,
    )
    assert complete.status_code == 200


def test_auto_complete_session_idempotent(client, auth_headers, db_session, demo_shop, monkeypatch):
    start = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/telegram/connect/start",
        json={"mode": "business", "display_name": "Biz"},
        headers=auth_headers,
    )
    session_id = start.json()["session_id"]

    async def fake_validate(self, account=None):
        return True

    async def fake_sync(self, account):
        return {}

    async def fake_register(self, account):
        account.webhook_url = "https://example.com/webhook"
        account.status = ChannelAccountStatus.WEBHOOK_CONFIGURED

    from app.channels.telegram.bot import TelegramBotAdapter
    from app.services.telegram_connect_service import TelegramConnectService

    monkeypatch.setattr(TelegramBotAdapter, "validate_connection", fake_validate)
    monkeypatch.setattr(TelegramBotAdapter, "sync_metadata", fake_sync)
    monkeypatch.setattr(TelegramConnectService, "_register_webhook", fake_register)

    submit = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/telegram/connect/{session_id}/bot-token",
        json={"bot_token": "123:ABC", "webhook_secret": "wh-sec"},
        headers=auth_headers,
    )
    account_id = submit.json()["channel_account_id"]
    payload = _load("telegram_business_connection.json")
    client.post(
        f"/api/v1/channels/telegram/{account_id}/webhook",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": "wh-sec"},
    )

    complete = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/telegram/connect/{session_id}/complete",
        headers=auth_headers,
    )
    assert complete.status_code == 200


@pytest.mark.asyncio
async def test_business_mark_read(db_session, demo_shop, monkeypatch):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="TG",
        connection_mode=TelegramConnectionMode.BUSINESS,
        bot_token_encrypted=encrypt_secret("test-token"),
        telegram_business_connection_id="biz-conn-1",
        telegram_business_enabled=True,
        telegram_rights_json={"can_read_messages": True},
        status=ChannelAccountStatus.WEBHOOK_CONFIGURED,
    )
    db_session.add(account)
    db_session.commit()

    called: list[dict] = []

    async def fake_mark_read(
        self,
        external_chat_id: str,
        external_message_id: str,
        business_connection_id: str | None = None,
    ):
        from app.schemas.channels import ProviderSendResult

        called.append(
            {
                "chat_id": external_chat_id,
                "message_id": external_message_id,
                "business_connection_id": business_connection_id,
            }
        )
        return ProviderSendResult(provider=ChannelProvider.TELEGRAM, success=True)

    from app.channels.telegram.business import TelegramBusinessAdapter

    monkeypatch.setattr(TelegramBusinessAdapter, "mark_read", fake_mark_read)

    result = await TelegramBusinessConnectionService(db_session).mark_read(
        account, "123", "42", connection_id="biz-conn-1"
    )
    assert result.success
    assert called[0]["business_connection_id"] == "biz-conn-1"


def test_business_sync_and_validate_api(client, auth_headers, db_session, demo_shop, monkeypatch):
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="TG",
        connection_mode=TelegramConnectionMode.BUSINESS,
        bot_token_encrypted=encrypt_secret("token"),
        telegram_business_connection_id="biz-conn-1",
        telegram_business_enabled=True,
        status=ChannelAccountStatus.WEBHOOK_CONFIGURED,
    )
    db_session.add(account)
    db_session.commit()

    async def fake_sync(self, account):
        account.telegram_last_sync_at = account.telegram_last_sync_at
        return {}

    async def fake_validate(self, account):
        return True

    monkeypatch.setattr(TelegramBusinessConnectionService, "sync", fake_sync)
    monkeypatch.setattr(TelegramBusinessConnectionService, "validate", fake_validate)

    sync = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/{account.id}/telegram/business/sync",
        headers=auth_headers,
    )
    assert sync.status_code == 200

    validate = client.post(
        f"/api/v1/shops/{demo_shop.id}/channels/{account.id}/telegram/business/validate",
        headers=auth_headers,
    )
    assert validate.status_code == 200


def test_outbound_redacts_bot_token_in_errors(db_session, demo_shop):
    from app.services.channel_outbound_service import ChannelOutboundService

    token = "123:SECRETTOKEN"
    account = ChannelAccount(
        shop_id=demo_shop.id,
        provider=ChannelProvider.TELEGRAM,
        display_name="TG",
        connection_mode=TelegramConnectionMode.BOT,
        bot_token_encrypted=encrypt_secret(token),
        status=ChannelAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.commit()

    safe = ChannelOutboundService._safe_error(f"Bad token {token}", [token])
    assert "SECRETTOKEN" not in safe
    assert "[REDACTED]" in safe

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from app.channels.adapters import TelegramProviderAdapter, WhatsAppProviderAdapter
from app.domain.enums import ChannelMessageType, ChannelProvider
from app.schemas.channels import MediaItem, NormalizedOutboundMessage
from app.services.channel_policy_service import ChannelPolicyService
from app.services.channel_webhook_ingestion_service import mask_pii

FIXTURES = Path(__file__).parent / "fixtures" / "channels"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_whatsapp_text_payload_normalization() -> None:
    message = WhatsAppProviderAdapter().parse_inbound_update(
        load_fixture("whatsapp_text.json")
    )[0]
    assert message.provider == ChannelProvider.WHATSAPP
    assert message.external_message_id == "wamid.text.1"
    assert message.external_chat_id == "15551234567"
    assert message.display_name == "Ava"
    assert message.text == "Do you have size M?"
    assert message.raw_payload["phone_number_id"] == "phone-1"


def test_whatsapp_image_payload_normalization() -> None:
    payload = load_fixture("whatsapp_text.json")
    msg = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    msg.update(
        {
            "type": "image",
            "text": None,
            "image": {
                "id": "media-1",
                "mime_type": "image/jpeg",
                "caption": "Blue dress",
            },
        }
    )
    message = WhatsAppProviderAdapter().parse_inbound_update(payload)[0]
    assert message.message_type == ChannelMessageType.IMAGE
    assert message.caption == "Blue dress"
    assert message.media_items[0].id == "media-1"
    assert message.media_items[0].mime_type == "image/jpeg"


def test_whatsapp_interactive_reply_normalization() -> None:
    message = WhatsAppProviderAdapter().parse_inbound_update(
        load_fixture("whatsapp_interactive_button.json")
    )[0]
    assert message.message_type == ChannelMessageType.INTERACTIVE
    assert message.button_id == "buy_sku_1"
    assert message.button_text == "Buy now"


def test_whatsapp_status_payload_is_delivery_event_not_llm_message() -> None:
    message = WhatsAppProviderAdapter().parse_inbound_update(
        load_fixture("whatsapp_status.json")
    )[0]
    assert message.raw_payload["event_type"] == "delivery_status"
    assert message.raw_payload["status"]["status"] == "delivered"
    assert message.message_type == ChannelMessageType.UNKNOWN


def test_whatsapp_signature_valid_invalid_and_missing() -> None:
    body = json.dumps(load_fixture("whatsapp_text.json")).encode()
    secret = "app-secret"
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(signature, expected)
    assert not hmac.compare_digest("sha256=bad", expected)
    assert not hmac.compare_digest("", expected)


def test_whatsapp_policy_blocks_free_form_outside_window_and_allows_template() -> None:
    account_id = "00000000-0000-0000-0000-000000000000"
    free_form = NormalizedOutboundMessage(
        provider=ChannelProvider.WHATSAPP,
        channel_account_id=account_id,
        external_chat_id="15551234567",
        text="Hello",
    )
    template = free_form.model_copy(update={"template_name": "order_update"})
    expired = datetime.now(UTC) - timedelta(minutes=1)
    assert not ChannelPolicyService().evaluate_outbound(free_form, expired).allowed
    assert ChannelPolicyService().evaluate_outbound(template, expired).allowed


@pytest.mark.anyio
async def test_whatsapp_retry_classification(monkeypatch: pytest.MonkeyPatch) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"code": 4, "message": "rate limit"}})

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, **kwargs):
            return await handler(httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    result = await WhatsAppProviderAdapter("token", "phone-1").send_message(
        NormalizedOutboundMessage(
            provider=ChannelProvider.WHATSAPP,
            channel_account_id="00000000-0000-0000-0000-000000000000",
            external_chat_id="1555",
            text="Hi",
        )
    )
    assert result.retryable is True
    assert result.error_code == "4"


def test_telegram_text_and_photo_caption_normalization() -> None:
    text = TelegramProviderAdapter().parse_inbound_update(
        load_fixture("telegram_text.json")
    )[0]
    photo = TelegramProviderAdapter().parse_inbound_update(
        load_fixture("telegram_photo_caption.json")
    )[0]
    assert text.external_update_id == "1001"
    assert text.text == "Hi"
    assert photo.message_type == ChannelMessageType.IMAGE
    assert photo.caption == "Is this available?"
    assert photo.media_items[0].id == "large"
    assert photo.raw_payload["chat_type"] == "private"


def test_telegram_callback_query_normalization() -> None:
    message = TelegramProviderAdapter().parse_inbound_update(
        load_fixture("telegram_callback_query.json")
    )[0]
    assert message.message_type == ChannelMessageType.BUTTON_CALLBACK
    assert message.external_message_id == "cb-1"
    assert message.button_id == "buy:sku-1"


@pytest.mark.anyio
async def test_telegram_send_message_success_and_callback_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 101}})

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, **kwargs):
            return await handler(httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    adapter = TelegramProviderAdapter("bot-token")
    result = await adapter.send_message(
        NormalizedOutboundMessage(
            provider=ChannelProvider.TELEGRAM,
            channel_account_id="00000000-0000-0000-0000-000000000000",
            external_chat_id="777",
            text="Hi",
        )
    )
    callback = await adapter.send_message(
        NormalizedOutboundMessage(
            provider=ChannelProvider.TELEGRAM,
            channel_account_id="00000000-0000-0000-0000-000000000000",
            external_chat_id="777",
            message_type=ChannelMessageType.BUTTON_CALLBACK,
            text="OK",
            metadata={"callback_query_id": "cb-1"},
        )
    )
    assert result.success is True
    assert callback.success is True
    assert any("sendMessage" in call for call in calls)
    assert any("answerCallbackQuery" in call for call in calls)


def test_token_masking() -> None:
    assert mask_pii({"token": "secret", "access_token": "secret", "from": "1555"}) == {
        "token": "***",
        "access_token": "***",
        "from": "***",
    }


def test_telegram_default_webhook_url_includes_channel_account_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api.v1.channels import _default_telegram_webhook_url
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "api_public_base_url", "https://example.test")

    account_id = UUID("11111111-1111-1111-1111-111111111111")

    assert _default_telegram_webhook_url(account_id) == (
        "https://example.test/api/v1/channels/telegram/"
        "11111111-1111-1111-1111-111111111111/webhook"
    )


def test_telegram_webhook_account_resolution_uses_secret_header() -> None:
    from app.api.v1.channels import _resolve_telegram_webhook_account
    from starlette.requests import Request

    class FakeDb:
        def __init__(self) -> None:
            self.statement = None

        def scalar(self, statement):
            self.statement = statement
            return None

    db = FakeDb()
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/channels/telegram/webhook",
            "headers": [(b"x-telegram-bot-api-secret-token", b"secret-for-account-2")],
        }
    )

    assert _resolve_telegram_webhook_account(db, request) is None
    compiled = str(db.statement.compile(compile_kwargs={"literal_binds": True}))

    assert "channel_accounts.webhook_secret = 'secret-for-account-2'" in compiled
    assert "LIMIT" not in compiled.upper()


def test_telegram_webhook_account_resolution_without_secret_skips_lookup() -> None:
    from app.api.v1.channels import _resolve_telegram_webhook_account
    from starlette.requests import Request

    class FakeDb:
        def scalar(self, statement):
            raise AssertionError(
                "Telegram account lookup should not run without a secret"
            )

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/channels/telegram/webhook",
            "headers": [],
        }
    )

    assert _resolve_telegram_webhook_account(FakeDb(), request) is None

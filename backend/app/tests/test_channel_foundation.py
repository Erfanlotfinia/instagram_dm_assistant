import asyncio
from datetime import UTC, datetime, timedelta

from starlette.requests import Request

from app.channels.adapters import TelegramProviderAdapter, WhatsAppProviderAdapter
from app.core.log_masking import redact_value
from app.domain.enums import ChannelMessageType, ChannelProvider, WebhookSecurityType
from app.schemas.channels import NormalizedOutboundMessage
from app.services.channel_policy_service import ChannelPolicyService


def test_provider_capabilities_cover_whatsapp_and_telegram() -> None:
    whatsapp = WhatsAppProviderAdapter().get_capabilities()
    telegram = TelegramProviderAdapter().get_capabilities()

    assert whatsapp.supports_templates is True
    assert whatsapp.supports_customer_service_window is True
    assert whatsapp.default_customer_service_window_hours == 24
    assert whatsapp.webhook_security_type == WebhookSecurityType.SIGNATURE
    assert telegram.supports_inline_keyboard is True
    assert telegram.webhook_security_type == WebhookSecurityType.SECRET_TOKEN_HEADER


def test_whatsapp_normalization_text_payload() -> None:
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "phone-1"},
                            "contacts": [
                                {"wa_id": "15551234567", "profile": {"name": "Ava"}}
                            ],
                            "messages": [
                                {
                                    "from": "15551234567",
                                    "id": "wamid.1",
                                    "timestamp": "1710000000",
                                    "type": "text",
                                    "text": {"body": "Do you have size M?"},
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }

    messages = WhatsAppProviderAdapter().parse_inbound_update(payload)

    assert len(messages) == 1
    assert messages[0].provider == ChannelProvider.WHATSAPP
    assert messages[0].external_message_id == "wamid.1"
    assert messages[0].external_chat_id == "15551234567"
    assert messages[0].display_name == "Ava"
    assert messages[0].message_type == ChannelMessageType.TEXT
    assert messages[0].text == "Do you have size M?"


def test_telegram_normalization_callback_payload() -> None:
    payload = {
        "update_id": 42,
        "callback_query": {
            "id": "cb-1",
            "from": {"id": 7, "username": "customer", "first_name": "Customer"},
            "data": "buy:sku-1",
            "message": {"message_id": 99, "date": 1710000000, "chat": {"id": 7}},
        },
    }

    message = TelegramProviderAdapter().parse_inbound_update(payload)[0]

    assert message.provider == ChannelProvider.TELEGRAM
    assert message.message_type == ChannelMessageType.BUTTON_CALLBACK
    assert message.button_id == "buy:sku-1"
    assert message.external_chat_id == "7"


def test_channel_policy_blocks_whatsapp_without_template_after_window() -> None:
    msg = NormalizedOutboundMessage(
        provider=ChannelProvider.WHATSAPP,
        channel_account_id="00000000-0000-0000-0000-000000000000",
        external_chat_id="15551234567",
        text="Hello",
    )

    decision = ChannelPolicyService().evaluate_outbound(
        msg, datetime.now(UTC) - timedelta(minutes=1)
    )

    assert decision.allowed is False
    assert decision.requires_template is True


def test_mask_pii_redacts_phone_like_fields() -> None:
    assert redact_value(
        {"from": "15551234567", "nested": {"access_token": "secret", "safe": "ok"}}
    ) == {"from": "[REDACTED]", "nested": {"access_token": "[REDACTED]", "safe": "ok"}}


def _request_with_headers(headers: dict[str, str], body: bytes = b"{}") -> Request:
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/webhook",
            "headers": [
                (key.lower().encode(), value.encode()) for key, value in headers.items()
            ],
        },
        receive,
    )


def test_static_token_adapter_rejects_missing_webhook_secret() -> None:
    request = _request_with_headers({"X-Telegram-Bot-Api-Secret-Token": "secret"})

    assert asyncio.run(TelegramProviderAdapter().verify_webhook(request)) is False


def test_static_token_adapter_accepts_matching_webhook_secret() -> None:
    request = _request_with_headers({"X-Telegram-Bot-Api-Secret-Token": "secret"})

    assert (
        asyncio.run(
            TelegramProviderAdapter(webhook_secret="secret").verify_webhook(request)
        )
        is True
    )

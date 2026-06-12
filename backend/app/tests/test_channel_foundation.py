from datetime import UTC, datetime, timedelta

from app.channels.adapters import TelegramProviderAdapter, WhatsAppProviderAdapter
from app.domain.enums import ChannelMessageType, ChannelProvider, WebhookSecurityType
from app.schemas.channels import NormalizedOutboundMessage
from app.services.channel_policy_service import ChannelPolicyService
from app.services.channel_webhook_ingestion_service import mask_pii


def test_provider_capabilities_cover_whatsapp_and_telegram() -> None:
    whatsapp = WhatsAppProviderAdapter().get_capabilities()
    telegram = TelegramProviderAdapter().get_capabilities()

    assert whatsapp.supports_templates is True
    assert whatsapp.supports_customer_service_window is True
    assert whatsapp.default_customer_service_window_hours == 24
    assert whatsapp.webhook_security_type == WebhookSecurityType.VERIFY_TOKEN
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
                            "contacts": [{"wa_id": "15551234567", "profile": {"name": "Ava"}}],
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
    assert mask_pii(
        {"from": "15551234567", "nested": {"access_token": "secret", "safe": "ok"}}
    ) == {"from": "***", "nested": {"access_token": "***", "safe": "ok"}}

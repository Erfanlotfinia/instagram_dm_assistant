from uuid import uuid4

import pytest

from app.domain.enums import ChannelMessageType, ChannelProvider, MessageDirection
from app.domain.models import ChannelMessage
from app.schemas.channels import NormalizedOutboundMessage, ProviderSendResult
from app.services import channel_outbound_service
from app.services.channel_outbound_service import ChannelOutboundService


class FakeSession:
    def __init__(self, existing: ChannelMessage):
        self.existing = existing
        self.commits = 0

    def scalar(self, statement):
        return self.existing

    def get(self, model, key):
        raise AssertionError("account lookup should be skipped for in-flight duplicate")

    def add(self, instance):
        raise AssertionError("no rows should be added for in-flight duplicate")

    def commit(self):
        self.commits += 1


@pytest.mark.anyio
async def test_outbound_idempotency_returns_in_flight_duplicate_without_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_adapter_for_provider(*args, **kwargs):
        raise AssertionError("provider should not be called for an in-flight duplicate")

    monkeypatch.setattr(channel_outbound_service, "adapter_for_provider", fail_adapter_for_provider)
    account_id = uuid4()
    existing = ChannelMessage(
        shop_id=uuid4(),
        provider=ChannelProvider.TELEGRAM,
        channel_account_id=account_id,
        conversation_id=uuid4(),
        direction=MessageDirection.OUTBOUND,
        message_type=ChannelMessageType.TEXT,
        text="Hello",
        media_json={"items": []},
        interactive_json={"buttons": []},
        raw_payload_json={},
        normalized_payload_json={},
        idempotency_key="idem-1",
    )
    service = ChannelOutboundService(FakeSession(existing))

    result = await service.send(
        NormalizedOutboundMessage(
            provider=ChannelProvider.TELEGRAM,
            channel_account_id=str(account_id),
            external_chat_id="chat-1",
            text="Hello",
            metadata={"idempotency_key": "idem-1", "conversation_id": str(uuid4())},
        )
    )

    assert result == ProviderSendResult(
        provider=ChannelProvider.TELEGRAM,
        success=False,
        raw_response={},
        error_code="outbound_send_in_flight",
        error_message="An outbound message with this idempotency key is already pending",
        retryable=True,
    )
    assert service.db.commits == 0


class _InstagramFakeClient:
    response = None
    request = None

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, **kwargs):
        import httpx

        type(self).request = httpx.Request(
            "POST", url, headers=kwargs.get("headers"), json=kwargs.get("json")
        )
        return type(self).response


@pytest.mark.anyio
@pytest.mark.parametrize("status_code,retryable", [(400, False), (429, True), (500, True)])
async def test_instagram_send_error_retryability(status_code, retryable, monkeypatch):
    import httpx

    from app.channels.adapters import InstagramProviderAdapter

    monkeypatch.setattr(httpx, "AsyncClient", _InstagramFakeClient)
    _InstagramFakeClient.response = httpx.Response(
        status_code, json={"error": {"code": status_code, "message": "send failed"}}
    )
    message = NormalizedOutboundMessage(
        provider=ChannelProvider.INSTAGRAM,
        channel_account_id=uuid4(),
        external_chat_id="customer-1",
        text="Hello",
    )
    result = await InstagramProviderAdapter(
        access_token="account-token", api_version="v99.0", api_base_url="https://graph.example"
    ).send_message(message, object())
    assert result.success is False
    assert result.retryable is retryable


@pytest.mark.anyio
async def test_instagram_text_send_success_uses_account_token(monkeypatch):
    import httpx

    from app.channels.adapters import InstagramProviderAdapter

    monkeypatch.setattr(httpx, "AsyncClient", _InstagramFakeClient)
    _InstagramFakeClient.response = httpx.Response(
        200, json={"recipient_id": "customer-1", "message_id": "mid.123"}
    )
    message = NormalizedOutboundMessage(
        provider=ChannelProvider.INSTAGRAM,
        channel_account_id=uuid4(),
        external_chat_id="customer-1",
        text="Hello",
    )
    result = await InstagramProviderAdapter(
        access_token="account-token", api_version="v99.0", api_base_url="https://graph.example"
    ).send_message(message, object())
    assert result.success is True
    assert result.external_message_id == "mid.123"
    assert _InstagramFakeClient.request.headers["authorization"] == "Bearer account-token"

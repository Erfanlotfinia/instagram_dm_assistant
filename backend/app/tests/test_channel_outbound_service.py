from uuid import uuid4

import pytest

from app.core.config import Settings
from app.domain.enums import ChannelMessageType, ChannelProvider, MessageDirection
from app.domain.models import ChannelMessage, Conversation, Message
from app.schemas.channels import NormalizedOutboundMessage, ProviderSendResult
from app.services import channel_outbound_service
from app.services.channel_outbound_service import (
    ChannelOutboundError,
    ChannelOutboundService,
    OutboundSyncContextError,
    agent_run_outbound_key,
)


def _production_settings(**overrides: object) -> Settings:
    base = {
        "app_env": "production",
        "enable_real_provider_send": True,
        "webhook_signature_bypass": False,
        "jwt_secret_key": "production-test-jwt-secret-key-32",
        "token_encryption_key": "production-test-token-encryption-key!",
        "cors_origins": ["https://admin.example.com"],
        "meta_app_secret": "meta-secret-value",
        "meta_app_id": "123456",
        "enabled_channel_providers": "instagram",
        "database_url": "postgresql+psycopg://postgres:postgres@localhost:5432/modira",
    }
    base.update(overrides)
    return Settings(**base)


def _conversation() -> Conversation:
    return Conversation(
        id=uuid4(),
        shop_id=uuid4(),
        customer_id=uuid4(),
        channel_account_id=uuid4(),
        channel_provider=ChannelProvider.TELEGRAM.value,
        external_conversation_id="chat-1",
    )


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


class WrapperSession:
    def __init__(self, conversation: Conversation):
        self.conversation = conversation
        self.added = []
        self.commits = 0
        self.flushes = 0

    def get(self, model, key):
        assert model is Conversation
        return self.conversation

    def add(self, instance):
        self.added.append(instance)

    def commit(self):
        self.commits += 1

    def flush(self):
        self.flushes += 1

    def refresh(self, instance):
        return instance


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


def test_send_text_message_commit_false_preserves_caller_transaction(monkeypatch) -> None:
    conversation = _conversation()
    session = WrapperSession(conversation)
    service = ChannelOutboundService(session)
    observed_commit = None

    async def successful_send(message, *, commit=True):
        nonlocal observed_commit
        observed_commit = commit
        return ProviderSendResult(provider=message.provider, success=True)

    monkeypatch.setattr(service, "send", successful_send)
    result = service.send_text_message(
        conversation.id,
        "Hello",
        commit=False,
        idempotency_key=agent_run_outbound_key(uuid4()),
    )

    assert isinstance(result, Message)
    assert observed_commit is False
    assert session.commits == 0
    assert session.flushes == 1


def test_send_text_message_does_not_record_failed_send(monkeypatch) -> None:
    conversation = _conversation()
    conversation.channel_provider = ChannelProvider.TELEGRAM
    session = WrapperSession(conversation)
    service = ChannelOutboundService(session)

    async def failed_send(message, *, commit=True):
        return ProviderSendResult(
            provider=message.provider,
            success=False,
            error_code="provider_error",
            error_message="Provider rejected the message",
        )

    monkeypatch.setattr(service, "send", failed_send)

    with pytest.raises(ChannelOutboundError, match="Provider rejected the message"):
        service.send_text_message(
            conversation.id,
            "Hello",
            idempotency_key=agent_run_outbound_key(uuid4()),
        )

    assert session.added == []
    assert session.commits == 0
    assert session.flushes == 0


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


@pytest.mark.anyio
async def test_same_text_different_business_keys_send_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    conversation = _conversation()
    session = WrapperSession(conversation)
    service = ChannelOutboundService(session)
    observed_keys: list[str | None] = []

    async def successful_send(message, *, commit=True):
        observed_keys.append(message.metadata.get("idempotency_key"))
        return ProviderSendResult(provider=message.provider, success=True)

    monkeypatch.setattr(service, "send", successful_send)

    run_a = uuid4()
    run_b = uuid4()
    await service.send_text_message_async(
        conversation.id,
        "Same reply text",
        commit=False,
        idempotency_key=agent_run_outbound_key(run_a),
    )
    await service.send_text_message_async(
        conversation.id,
        "Same reply text",
        commit=False,
        idempotency_key=agent_run_outbound_key(run_b),
    )

    assert observed_keys == [
        agent_run_outbound_key(run_a),
        agent_run_outbound_key(run_b),
    ]


@pytest.mark.anyio
async def test_same_business_idempotency_key_dedupes_without_second_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    business_key = agent_run_outbound_key(uuid4())

    async def fail_adapter_for_provider(*args, **kwargs):
        raise AssertionError("provider should not be called for duplicate business key")

    monkeypatch.setattr(channel_outbound_service, "adapter_for_provider", fail_adapter_for_provider)
    account_id = uuid4()
    existing = ChannelMessage(
        shop_id=uuid4(),
        provider=ChannelProvider.TELEGRAM,
        channel_account_id=account_id,
        conversation_id=uuid4(),
        direction=MessageDirection.OUTBOUND,
        message_type=ChannelMessageType.TEXT,
        text="Different text is fine",
        media_json={"items": []},
        interactive_json={"buttons": []},
        raw_payload_json={},
        normalized_payload_json={},
        idempotency_key=business_key,
    )
    service = ChannelOutboundService(FakeSession(existing))

    result = await service.send(
        NormalizedOutboundMessage(
            provider=ChannelProvider.TELEGRAM,
            channel_account_id=str(account_id),
            external_chat_id="chat-1",
            text="Totally different text",
            metadata={"idempotency_key": business_key, "conversation_id": str(uuid4())},
        )
    )

    assert result.error_code == "outbound_send_in_flight"


@pytest.mark.anyio
async def test_send_text_message_inside_event_loop_raises() -> None:
    conversation = _conversation()
    service = ChannelOutboundService(WrapperSession(conversation))

    with pytest.raises(OutboundSyncContextError, match="send_text_message_async"):
        service.send_text_message(
            conversation.id,
            "Hello",
            idempotency_key=agent_run_outbound_key(uuid4()),
        )


@pytest.mark.anyio
async def test_send_text_message_async_works(monkeypatch: pytest.MonkeyPatch) -> None:
    conversation = _conversation()
    session = WrapperSession(conversation)
    service = ChannelOutboundService(session)

    async def successful_send(message, *, commit=True):
        return ProviderSendResult(provider=message.provider, success=True)

    monkeypatch.setattr(service, "send", successful_send)

    result = await service.send_text_message_async(
        conversation.id,
        "Hello",
        commit=False,
        idempotency_key=agent_run_outbound_key(uuid4()),
    )

    assert isinstance(result, Message)
    assert result.text == "Hello"
    assert session.flushes == 1


def test_simulation_fallback_resolves_text_hash_without_explicit_key() -> None:
    settings = Settings(app_env="development", enable_real_provider_send=False)
    service = ChannelOutboundService(WrapperSession(_conversation()), settings=settings)
    message = NormalizedOutboundMessage(
        provider=ChannelProvider.TELEGRAM,
        channel_account_id=uuid4(),
        external_chat_id="chat-1",
        text="Hello",
        metadata={"is_simulation": True, "conversation_id": str(uuid4())},
    )

    key, error = service._resolve_idempotency_key(message)

    assert error is None
    assert key == service._text_hash_idempotency_key(message)


@pytest.mark.anyio
async def test_production_real_send_rejects_missing_idempotency_key() -> None:
    service = ChannelOutboundService(
        WrapperSession(_conversation()),
        settings=_production_settings(),
    )

    result = await service.send(
        NormalizedOutboundMessage(
            provider=ChannelProvider.TELEGRAM,
            channel_account_id=uuid4(),
            external_chat_id="chat-1",
            text="Hello",
            metadata={"conversation_id": str(uuid4()), "is_simulation": False},
        )
    )

    assert result.success is False
    assert result.error_code == "outbound_idempotency_key_required"

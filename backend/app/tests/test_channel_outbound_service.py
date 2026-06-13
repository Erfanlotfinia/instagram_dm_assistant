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

    monkeypatch.setattr(
        channel_outbound_service, "adapter_for_provider", fail_adapter_for_provider
    )
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
    )
    assert service.db.commits == 0

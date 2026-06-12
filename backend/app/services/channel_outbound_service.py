from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.enums import MessageDirection
from app.domain.models import ChannelAccount, ChannelMessage
from app.schemas.channels import NormalizedOutboundMessage, ProviderSendResult
from app.services.channel_account_service import adapter_for_provider
from app.services.channel_policy_service import ChannelPolicyService


class ChannelOutboundService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.policy = ChannelPolicyService()

    async def send(self, message: NormalizedOutboundMessage) -> ProviderSendResult:
        decision = self.policy.evaluate_outbound(message)
        if not decision.allowed:
            return ProviderSendResult(
                provider=message.provider,
                success=False,
                error_code=decision.reason,
                error_message=decision.reason,
            )
        account = self.db.get(ChannelAccount, message.channel_account_id)
        if account is None:
            return ProviderSendResult(
                provider=message.provider,
                success=False,
                error_code="channel_account_not_found",
                error_message="Channel account not found",
            )
        channel_message = ChannelMessage(
            shop_id=account.shop_id,
            provider=message.provider,
            channel_account_id=account.id,
            conversation_id=message.metadata.get("conversation_id"),
            direction=MessageDirection.OUTBOUND,
            message_type=message.message_type,
            text=message.text,
            media_json={"items": [m.model_dump(mode="json") for m in message.media_items]},
            interactive_json={"buttons": [b.model_dump() for b in message.buttons]},
            raw_payload_json={},
            normalized_payload_json=message.model_dump(mode="json"),
            idempotency_key=message.metadata.get(
                "idempotency_key",
                f"outbound:{message.channel_account_id}:{message.external_chat_id}:{message.text}",
            ),
            is_simulation=bool(message.metadata.get("is_simulation", False)),
        )
        if not channel_message.conversation_id:
            return ProviderSendResult(
                provider=message.provider,
                success=False,
                error_code="conversation_required",
                error_message="conversation_id metadata is required",
            )
        self.db.add(channel_message)
        self.db.commit()
        if channel_message.is_simulation:
            return ProviderSendResult(
                provider=message.provider, success=True, raw_response={"simulation": True}
            )
        result = await adapter_for_provider(message.provider).send_message(message)
        channel_message.external_message_id = result.external_message_id
        channel_message.raw_payload_json = result.raw_response or {}
        self.db.commit()
        return result

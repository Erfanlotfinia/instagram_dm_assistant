from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.enums import FailedJobStatus, MessageDirection
from app.domain.models import ChannelAccount, ChannelConversation, ChannelMessage, FailedJob
from app.schemas.channels import NormalizedOutboundMessage, ProviderSendResult
from app.services.channel_account_service import adapter_for_provider
from app.services.channel_policy_service import ChannelPolicyService


class ChannelOutboundService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.policy = ChannelPolicyService()

    async def send(self, message: NormalizedOutboundMessage) -> ProviderSendResult:
        idempotency_key = message.metadata.get(
            "idempotency_key",
            f"outbound:{message.channel_account_id}:{message.external_chat_id}:{message.text}",
        )
        existing = self.db.scalar(
            select(ChannelMessage).where(
                ChannelMessage.channel_account_id == message.channel_account_id,
                ChannelMessage.direction == MessageDirection.OUTBOUND,
                ChannelMessage.idempotency_key == idempotency_key,
            )
        )
        if existing and existing.external_message_id:
            return ProviderSendResult(
                provider=message.provider,
                success=True,
                external_message_id=existing.external_message_id,
                raw_response=existing.raw_payload_json,
            )
        conversation_window = None
        if message.metadata.get("conversation_id"):
            channel_conversation = self.db.scalar(
                select(ChannelConversation).where(
                    ChannelConversation.conversation_id
                    == message.metadata.get("conversation_id"),
                    ChannelConversation.channel_account_id
                    == message.channel_account_id,
                )
            )
            conversation_window = (
                channel_conversation.messaging_window_expires_at
                if channel_conversation
                else None
            )
        decision = self.policy.evaluate_outbound(message, conversation_window)
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
        channel_message = existing or ChannelMessage(
            shop_id=account.shop_id,
            provider=message.provider,
            channel_account_id=account.id,
            conversation_id=message.metadata.get("conversation_id"),
            direction=MessageDirection.OUTBOUND,
            message_type=message.message_type,
            text=message.text,
            media_json={
                "items": [m.model_dump(mode="json") for m in message.media_items]
            },
            interactive_json={"buttons": [b.model_dump() for b in message.buttons]},
            raw_payload_json={},
            normalized_payload_json=message.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            is_simulation=bool(message.metadata.get("is_simulation", False)),
        )
        if not channel_message.conversation_id:
            return ProviderSendResult(
                provider=message.provider,
                success=False,
                error_code="conversation_required",
                error_message="conversation_id metadata is required",
            )
        if existing is None:
            self.db.add(channel_message)
            try:
                self.db.commit()
            except IntegrityError:
                self.db.rollback()
                duplicate = self.db.scalar(
                    select(ChannelMessage).where(
                        ChannelMessage.channel_account_id == message.channel_account_id,
                        ChannelMessage.direction == MessageDirection.OUTBOUND,
                        ChannelMessage.idempotency_key == idempotency_key,
                    )
                )
                return ProviderSendResult(
                    provider=message.provider,
                    success=bool(duplicate and duplicate.external_message_id),
                    external_message_id=(
                        duplicate.external_message_id if duplicate else None
                    ),
                    raw_response=duplicate.raw_payload_json if duplicate else None,
                    error_code=None if duplicate else "duplicate_outbound",
                )
        if channel_message.is_simulation:
            return ProviderSendResult(
                provider=message.provider,
                success=True,
                raw_response={"simulation": True},
            )
        result = await adapter_for_provider(message.provider, account).send_message(
            message
        )
        channel_message.external_message_id = result.external_message_id
        channel_message.raw_payload_json = result.raw_response or {}
        if not result.success:
            self.db.add(
                FailedJob(
                    shop_id=account.shop_id,
                    queue_name="channel_outbound",
                    job_type=f"{message.provider.value}.send_message",
                    payload={
                        "channel_message_id": str(channel_message.id),
                        "channel_account_id": str(account.id),
                        "provider": message.provider.value,
                        "external_chat_id": message.external_chat_id,
                        "idempotency_key": idempotency_key,
                    },
                    error_message=result.error_message or result.error_code,
                    status=FailedJobStatus.FAILED,
                )
            )
        self.db.commit()
        return result

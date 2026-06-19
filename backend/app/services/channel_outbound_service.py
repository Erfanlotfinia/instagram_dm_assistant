from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import (
    ChannelAccountStatus,
    ChannelMessageType,
    ChannelProvider,
    FailedJobStatus,
    MessageChannel,
    MessageDirection,
    MessageType,
)
from app.domain.models import (
    ChannelAccount,
    ChannelConversation,
    ChannelMessage,
    Conversation,
    FailedJob,
    Message,
)
from app.schemas.channels import NormalizedOutboundMessage, ProviderSendResult
from app.services.channel_account_service import ChannelAccountService, adapter_for_provider
from app.services.channel_policy_service import ChannelPolicyService
from app.services.pilot_service import PilotService

logger = logging.getLogger(__name__)


class ChannelOutboundError(RuntimeError):
    """Raised when an outbound provider send does not succeed."""

    def __init__(self, result: ProviderSendResult) -> None:
        self.result = result
        super().__init__(result.error_message or result.error_code or "Outbound send failed")


class ChannelOutboundService:
    """Single production boundary for every provider outbound message."""

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.policy = ChannelPolicyService()

    @staticmethod
    def _result(message: NormalizedOutboundMessage, **kwargs: Any) -> ProviderSendResult:
        return ProviderSendResult(provider=message.provider, **kwargs)

    @staticmethod
    def _result_from_existing(
        message: NormalizedOutboundMessage, existing: ChannelMessage
    ) -> ProviderSendResult:
        if existing.external_message_id:
            return ChannelOutboundService._result(
                message,
                success=True,
                external_message_id=existing.external_message_id,
                raw_response=existing.raw_payload_json,
            )
        return ChannelOutboundService._result(
            message,
            success=False,
            raw_response=existing.raw_payload_json,
            error_code="outbound_send_in_flight",
            error_message="An outbound message with this idempotency key is already pending",
            retryable=True,
        )

    @staticmethod
    def _safe_error(value: str | None, credentials: list[str | None]) -> str | None:
        if value is None:
            return None
        safe = value
        for credential in credentials:
            if credential:
                safe = safe.replace(credential, "[REDACTED]")
        return safe

    async def send(
        self, message: NormalizedOutboundMessage, *, commit: bool = True
    ) -> ProviderSendResult:
        idempotency_key = str(
            message.metadata.get("idempotency_key")
            or hashlib.sha256(
                f"{message.channel_account_id}:{message.external_chat_id}:{message.text}:{message.message_type.value}".encode()
            ).hexdigest()
        )
        existing = self.db.scalar(
            select(ChannelMessage).where(
                ChannelMessage.channel_account_id == message.channel_account_id,
                ChannelMessage.direction == MessageDirection.OUTBOUND,
                ChannelMessage.idempotency_key == idempotency_key,
            )
        )
        if existing:
            return self._result_from_existing(message, existing)

        account = self.db.get(ChannelAccount, message.channel_account_id)
        if account is None:
            return self._result(
                message,
                success=False,
                error_code="channel_account_not_found",
                error_message="Channel account not found",
            )
        requested_shop = message.metadata.get("shop_id")
        if requested_shop and str(account.shop_id) != str(requested_shop):
            return self._result(
                message,
                success=False,
                error_code="shop_ownership_mismatch",
                error_message="Channel account does not belong to the requested shop",
            )
        if account.provider != message.provider:
            return self._result(
                message,
                success=False,
                error_code="provider_account_mismatch",
                error_message="Channel account provider does not match message provider",
            )
        if account.status not in {
            ChannelAccountStatus.CONNECTED,
            ChannelAccountStatus.WEBHOOK_CONFIGURED,
        }:
            return self._result(
                message,
                success=False,
                error_code="channel_account_unavailable",
                error_message=f"Channel account status is {account.status.value}",
            )

        missing = ChannelAccountService._missing_required_credentials(account)
        if missing:
            return self._result(
                message,
                success=False,
                error_code="missing_credentials",
                error_message="Missing required channel credential: " + ", ".join(missing),
            )
        if PilotService(self.db).is_emergency_stop_active(account.shop_id):
            return self._result(
                message,
                success=False,
                error_code="emergency_stop_enabled",
                error_message="Outbound sending is disabled by emergency stop",
            )

        conversation_id = message.metadata.get("conversation_id")
        if not conversation_id:
            return self._result(
                message,
                success=False,
                error_code="conversation_required",
                error_message="conversation_id metadata is required",
            )
        conversation = self.db.get(Conversation, UUID(str(conversation_id)))
        if (
            conversation is None
            or conversation.shop_id != account.shop_id
            or conversation.channel_account_id != account.id
        ):
            return self._result(
                message,
                success=False,
                error_code="conversation_ownership_mismatch",
                error_message="Conversation does not belong to the channel account",
            )

        channel_conversation = self.db.scalar(
            select(ChannelConversation).where(
                ChannelConversation.conversation_id == conversation.id,
                ChannelConversation.channel_account_id == account.id,
            )
        )
        decision = self.policy.evaluate_outbound(
            message,
            channel_conversation.messaging_window_expires_at if channel_conversation else None,
        )
        adapter = adapter_for_provider(message.provider, account)
        capabilities = adapter.get_capabilities()
        capability_error = self._capability_error(message, capabilities)
        if not decision.allowed or capability_error:
            return self._result(
                message,
                success=False,
                error_code=decision.reason or capability_error,
                error_message=decision.reason or capability_error,
            )

        intent = ChannelMessage(
            shop_id=account.shop_id,
            provider=message.provider,
            channel_account_id=account.id,
            conversation_id=conversation.id,
            direction=MessageDirection.OUTBOUND,
            message_type=message.message_type,
            text=message.text,
            media_json={"items": [item.model_dump(mode="json") for item in message.media_items]},
            interactive_json={"buttons": [button.model_dump() for button in message.buttons]},
            raw_payload_json={},
            normalized_payload_json=message.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            is_simulation=bool(message.metadata.get("is_simulation", False)),
        )
        self.db.add(intent)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            duplicate = self.db.scalar(
                select(ChannelMessage).where(
                    ChannelMessage.channel_account_id == account.id,
                    ChannelMessage.direction == MessageDirection.OUTBOUND,
                    ChannelMessage.idempotency_key == idempotency_key,
                )
            )
            if duplicate:
                return self._result_from_existing(message, duplicate)
            raise

        if intent.is_simulation or not self.settings.enable_real_provider_send:
            result = self._result(
                message,
                success=True,
                raw_response={
                    "simulation": True,
                    "real_provider_send_enabled": self.settings.enable_real_provider_send,
                },
            )
        else:
            try:
                result = await adapter.send_message(message, account)
            except Exception as exc:  # noqa: BLE001
                result = self._result(
                    message,
                    success=False,
                    error_code="provider_exception",
                    error_message=str(exc),
                    retryable=True,
                )

        credentials = [ChannelAccountService(self.db).decrypt_access_token(account)]
        result.error_message = self._safe_error(result.error_message, credentials)
        intent.external_message_id = result.external_message_id
        intent.raw_payload_json = result.raw_response or {}
        if not result.success:
            logger.warning(
                "Provider send failed provider=%s account=%s code=%s retryable=%s",
                message.provider.value,
                account.id,
                result.error_code,
                result.retryable,
            )
            self.db.add(
                FailedJob(
                    shop_id=account.shop_id,
                    queue_name="channel_outbound",
                    job_type=f"{message.provider.value}.send_message",
                    payload={
                        "channel_message_id": str(intent.id),
                        "channel_account_id": str(account.id),
                        "provider": message.provider.value,
                        "external_chat_id": message.external_chat_id,
                        "conversation_id": str(conversation.id),
                        "idempotency_key": idempotency_key,
                    },
                    error_message=result.error_message or result.error_code,
                    status=FailedJobStatus.FAILED,
                    resolved=False,
                )
            )
        if commit:
            self.db.commit()
        else:
            self.db.flush()
        return result

    @staticmethod
    def _capability_error(message: NormalizedOutboundMessage, capabilities: Any) -> str | None:
        required = {
            ChannelMessageType.IMAGE: "supports_images",
            ChannelMessageType.VIDEO: "supports_video",
            ChannelMessageType.AUDIO: "supports_voice",
            ChannelMessageType.VOICE: "supports_voice",
            ChannelMessageType.DOCUMENT: "supports_files",
            ChannelMessageType.INTERACTIVE: "supports_buttons",
        }.get(message.message_type)
        if required and not getattr(capabilities, required, False):
            return f"unsupported_provider_capability:{message.message_type.value}"
        if message.buttons and not capabilities.supports_buttons:
            return "unsupported_provider_capability:buttons"
        return None

    def send_text_message(
        self,
        conversation_id: UUID,
        text: str,
        *,
        commit: bool = True,
        is_simulation: bool = False,
        idempotency_key: str | None = None,
    ) -> Message:
        conversation = self.db.get(Conversation, conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} does not exist")
        if not conversation.channel_account_id or not conversation.external_conversation_id:
            raise ValueError("Conversation is missing channel routing information")
        provider = ChannelProvider(conversation.channel_provider)
        result = asyncio.run(
            self.send(
                NormalizedOutboundMessage(
                    provider=provider,
                    channel_account_id=conversation.channel_account_id,
                    external_chat_id=conversation.external_conversation_id,
                    text=text,
                    metadata={
                        "shop_id": str(conversation.shop_id),
                        "conversation_id": str(conversation.id),
                        "is_simulation": is_simulation,
                        **({"idempotency_key": idempotency_key} if idempotency_key else {}),
                    },
                ),
                commit=commit,
            )
        )
        if not result.success:
            raise ChannelOutboundError(result)
        message = Message(
            shop_id=conversation.shop_id,
            conversation_id=conversation.id,
            customer_id=conversation.customer_id,
            channel_provider=provider,
            channel_account_id=conversation.channel_account_id,
            direction=MessageDirection.OUTBOUND,
            channel=MessageChannel(provider.value),
            message_type=MessageType.TEXT,
            text=text,
            external_message_id=result.external_message_id,
            is_simulation=is_simulation or not self.settings.enable_real_provider_send,
            raw_payload=result.model_dump(mode="json"),
        )
        self.db.add(message)
        if commit:
            self.db.commit()
            self.db.refresh(message)
        else:
            self.db.flush()
        return message

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol

from fastapi import Request

from app.domain.enums import MessageChannel, MessageType, TriggerSourceType
from app.schemas.channels import (
    ChannelCapabilities,
    NormalizedInboundMessage,
    NormalizedOutboundMessage,
    ProviderSendResult,
)


@dataclass(frozen=True)
class ChannelCustomerIdentity:
    provider: MessageChannel
    external_customer_id: str
    display_name: str | None = None
    username: str | None = None
    raw_profile: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChannelConversation:
    provider: MessageChannel
    external_conversation_id: str | None
    customer: ChannelCustomerIdentity
    account_external_id: str | None = None
    raw_context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InboundMessage:
    provider: MessageChannel
    external_message_id: str | None
    conversation: ChannelConversation
    message_type: MessageType
    text: str | None = None
    shared_post_url: str | None = None
    source_type: TriggerSourceType = TriggerSourceType.DIRECT_DM
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OutboundMessage:
    provider: MessageChannel
    conversation: ChannelConversation
    text: str
    reply_to_external_message_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ChannelProvider(Protocol):
    provider: MessageChannel

    def normalize_inbound(self, payload: dict[str, Any]) -> list[InboundMessage]:
        """Convert raw channel webhook payload into channel-independent inbound messages."""

    def send_message(self, message: OutboundMessage) -> str | None:
        """Send a normalized outbound message and return the provider message id."""


class ChannelProviderAdapter(ABC):
    @abstractmethod
    async def verify_webhook(self, request: Request) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse_inbound_update(
        self, payload: dict[str, Any], headers: dict[str, str] | None = None
    ) -> list[NormalizedInboundMessage]:
        raise NotImplementedError

    @abstractmethod
    async def send_message(self, message: NormalizedOutboundMessage) -> ProviderSendResult:
        raise NotImplementedError

    async def send_typing_or_chat_action(
        self, external_chat_id: str, action: str = "typing"
    ) -> ProviderSendResult:
        return ProviderSendResult(
            provider=self.get_capabilities_provider(),
            success=True,
            raw_response={"action": action, "chat_id": external_chat_id},
        )

    async def download_media(self, media_id: str) -> bytes:
        raise NotImplementedError

    async def configure_webhook(
        self, webhook_url: str, secret: str | None = None
    ) -> dict[str, Any]:
        return {"webhook_url": webhook_url, "configured": False, "reason": "not_implemented"}

    async def get_account_profile(self) -> dict[str, Any]:
        return {}

    async def validate_credentials(self) -> bool:
        return True

    @abstractmethod
    def get_capabilities(self) -> ChannelCapabilities:
        raise NotImplementedError

    def get_capabilities_provider(self):  # compatibility helper for default no-op results
        return self.provider

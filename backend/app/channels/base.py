from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.domain.enums import MessageChannel, MessageType, TriggerSourceType


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

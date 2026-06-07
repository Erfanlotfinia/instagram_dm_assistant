from __future__ import annotations

from typing import Any

from app.channels.base import ChannelConversation, ChannelCustomerIdentity, InboundMessage, OutboundMessage
from app.domain.enums import MessageChannel, MessageType, TriggerSourceType


class InstagramChannelProvider:
    """Instagram-specific parsing lives here; order services consume InboundMessage only."""

    provider = MessageChannel.INSTAGRAM

    def normalize_inbound(self, payload: dict[str, Any]) -> list[InboundMessage]:
        messages: list[InboundMessage] = []
        for entry in payload.get("entry", []):
            account_id = str(entry.get("id") or "")
            for event in entry.get("messaging", []):
                sender_id = str((event.get("sender") or {}).get("id") or "")
                message = event.get("message") or {}
                text = message.get("text")
                shared_post_url = self._extract_shared_post_url(message)
                external_message_id = message.get("mid") or event.get("message_id")
                identity = ChannelCustomerIdentity(
                    provider=self.provider,
                    external_customer_id=sender_id,
                    raw_profile={"sender": event.get("sender") or {}},
                )
                conversation = ChannelConversation(
                    provider=self.provider,
                    external_conversation_id=sender_id,
                    customer=identity,
                    account_external_id=account_id,
                    raw_context={"entry_id": account_id},
                )
                messages.append(
                    InboundMessage(
                        provider=self.provider,
                        external_message_id=external_message_id,
                        conversation=conversation,
                        message_type=MessageType.SHARED_POST if shared_post_url else MessageType.TEXT,
                        text=text,
                        shared_post_url=shared_post_url,
                        source_type=TriggerSourceType.DIRECT_DM,
                        raw_payload=event,
                    )
                )
            for change in entry.get("changes", []):
                value: dict[str, Any] = change.get("value") or {}
                text = value.get("text") or value.get("message") or value.get("comment_text")
                source_type = self._source_type(change.get("field"), value)
                sender_id = str(value.get("from", {}).get("id") or value.get("user_id") or value.get("sender_id") or "")
                identity = ChannelCustomerIdentity(provider=self.provider, external_customer_id=sender_id, raw_profile=value.get("from") or {})
                conversation = ChannelConversation(provider=self.provider, external_conversation_id=sender_id, customer=identity, account_external_id=account_id, raw_context=value)
                messages.append(InboundMessage(provider=self.provider, external_message_id=value.get("id") or value.get("comment_id"), conversation=conversation, message_type=MessageType.TEXT, text=text, source_type=source_type, raw_payload=change))
        return messages

    def send_message(self, message: OutboundMessage) -> str | None:
        raise NotImplementedError("Use InstagramSendService for authenticated production sends.")

    def _extract_shared_post_url(self, message: dict[str, Any]) -> str | None:
        for attachment in message.get("attachments") or []:
            payload: dict[str, Any] = attachment.get("payload") or {}
            url = payload.get("url") or payload.get("instagram_post_url")
            if url:
                return str(url)
        return None

    def _source_type(self, field: str | None, value: dict[str, Any]) -> TriggerSourceType:
        if value.get("ad_id"):
            return TriggerSourceType.AD_COMMENT
        if field == "story_insights" or value.get("story_id"):
            return TriggerSourceType.STORY_REPLY
        if value.get("media_product_type") == "REELS":
            return TriggerSourceType.REEL_COMMENT
        return TriggerSourceType.COMMENT

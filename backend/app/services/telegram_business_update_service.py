from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import ChannelProvider, ConversationEventType, MessageDirection
from app.domain.models import ChannelAccount, ChannelMessage, Message
from app.services.conversation_event_service import ConversationEventService
from app.services.telegram_business_connection_service import TelegramBusinessConnectionService

logger = logging.getLogger(__name__)


class TelegramBusinessUpdateService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.business_service = TelegramBusinessConnectionService(db)

    def handle_update(self, account: ChannelAccount, payload: dict[str, Any]) -> bool:
        if payload.get("business_connection"):
            self.business_service.connect(account, payload["business_connection"])
            return True
        if payload.get("deleted_business_messages"):
            self._handle_deleted(account, payload["deleted_business_messages"])
            return True
        if payload.get("edited_business_message"):
            self._handle_edited(account, payload["edited_business_message"])
            return True
        return False

    def _handle_edited(self, account: ChannelAccount, msg: dict[str, Any]) -> None:
        message_id = str(msg.get("message_id"))
        chat_id = str(msg.get("chat", {}).get("id"))
        new_text = msg.get("text") or msg.get("caption")
        channel_message = self.db.scalar(
            select(ChannelMessage).where(
                ChannelMessage.provider == ChannelProvider.TELEGRAM,
                ChannelMessage.channel_account_id == account.id,
                ChannelMessage.external_message_id == message_id,
                ChannelMessage.direction == MessageDirection.INBOUND,
            )
        )
        if channel_message is None:
            return
        channel_message.text = new_text
        if channel_message.internal_message_id:
            internal = self.db.get(Message, channel_message.internal_message_id)
            if internal:
                internal.text = new_text
                internal.content = new_text
                meta = internal.normalized_payload_json or {}
                meta["edited"] = True
                internal.normalized_payload_json = meta
        ConversationEventService(self.db).record(
            channel_message.conversation_id,
            ConversationEventType.INBOUND_MESSAGE,
            description=f"Message edited: {(new_text or '')[:180]}",
            metadata={"external_message_id": message_id, "chat_id": chat_id, "edited": True},
        )
        self.db.commit()

    def _handle_deleted(self, account: ChannelAccount, deleted: dict[str, Any]) -> None:
        chat_id = str(deleted.get("chat", {}).get("id"))
        message_ids = deleted.get("message_ids") or []
        for mid in message_ids:
            message_id = str(mid)
            channel_message = self.db.scalar(
                select(ChannelMessage).where(
                    ChannelMessage.channel_account_id == account.id,
                    ChannelMessage.external_message_id == message_id,
                    ChannelMessage.direction == MessageDirection.INBOUND,
                )
            )
            if channel_message is None:
                continue
            raw = channel_message.raw_payload_json or {}
            raw["deleted"] = True
            channel_message.raw_payload_json = raw
            if channel_message.internal_message_id:
                internal = self.db.get(Message, channel_message.internal_message_id)
                if internal:
                    internal_meta = internal.raw_payload or {}
                    internal_meta["deleted"] = True
                    internal.raw_payload = internal_meta
            ConversationEventService(self.db).record(
                channel_message.conversation_id,
                ConversationEventType.INBOUND_MESSAGE,
                description="Message deleted",
                metadata={"external_message_id": message_id, "chat_id": chat_id, "deleted": True},
            )
        self.db.commit()

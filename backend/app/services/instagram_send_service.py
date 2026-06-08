from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import MessageChannel, MessageDirection, MessageType
from app.domain.models import Message
from app.repositories.message_repository import MessageRepository

logger = logging.getLogger(__name__)


class InstagramSendService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.messages = MessageRepository(db)

    def send_text_message(
        self,
        conversation_id: UUID,
        text: str,
        *,
        commit: bool = True,
        is_simulation: bool = False,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            direction=MessageDirection.OUTBOUND,
            channel=MessageChannel.INSTAGRAM,
            message_type=MessageType.TEXT,
            text=text,
            is_simulation=is_simulation,
            raw_payload={"mode": "placeholder"},
        )

        if self.settings.enable_real_instagram_send:
            logger.warning("Real Instagram send is enabled but API integration is not implemented yet")
            message.raw_payload = {"mode": "real_send_not_implemented", "text": text}
        else:
            logger.info(
                "Placeholder outbound Instagram message stored for conversation %s: %s",
                conversation_id,
                text,
            )
            message.raw_payload = {"mode": "placeholder", "text": text}

        created = self.messages.create(message)
        if commit:
            self.db.commit()
            self.db.refresh(created)
        else:
            self.db.flush()
        return created

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Message


class MessageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, message_id: UUID) -> Message | None:
        return self.db.get(Message, message_id)

    def get_by_instagram_message_id(self, instagram_message_id: str) -> Message | None:
        stmt = select(Message).where(Message.instagram_message_id == instagram_message_id)
        return self.db.scalar(stmt)

    def list_for_conversation(self, conversation_id: UUID) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def create(self, message: Message) -> Message:
        self.db.add(message)
        self.db.flush()
        return message

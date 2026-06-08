from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import ConversationEvent


class ConversationEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, event: ConversationEvent) -> ConversationEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def list_for_conversation(self, conversation_id: UUID, *, limit: int = 100) -> list[ConversationEvent]:
        stmt = (
            select(ConversationEvent)
            .where(ConversationEvent.conversation_id == conversation_id)
            .order_by(ConversationEvent.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

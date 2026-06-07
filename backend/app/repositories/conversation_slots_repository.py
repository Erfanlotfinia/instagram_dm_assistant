from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import ConversationSlots


class ConversationSlotsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_conversation(self, conversation_id: UUID) -> ConversationSlots | None:
        stmt = select(ConversationSlots).where(ConversationSlots.conversation_id == conversation_id)
        return self.db.scalar(stmt)

    def get_or_create(self, conversation_id: UUID) -> ConversationSlots:
        slots = self.get_for_conversation(conversation_id)
        if slots is not None:
            return slots
        slots = ConversationSlots(conversation_id=conversation_id, missing_fields=[], confidence={})
        self.db.add(slots)
        self.db.flush()
        return slots

    def save(self, slots: ConversationSlots) -> ConversationSlots:
        self.db.add(slots)
        self.db.flush()
        return slots

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import AgentAction


class AgentActionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, action: AgentAction) -> AgentAction:
        self.db.add(action)
        self.db.flush()
        return action

    def list_for_conversation(self, conversation_id: UUID, limit: int = 50) -> list[AgentAction]:
        stmt = (
            select(AgentAction)
            .where(AgentAction.conversation_id == conversation_id)
            .order_by(AgentAction.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

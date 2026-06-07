from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import AgentRun


class AgentRunRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, agent_run: AgentRun) -> AgentRun:
        self.db.add(agent_run)
        self.db.flush()
        return agent_run

    def list_for_conversation(self, conversation_id: UUID, limit: int = 20) -> list[AgentRun]:
        stmt = (
            select(AgentRun)
            .where(AgentRun.conversation_id == conversation_id)
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

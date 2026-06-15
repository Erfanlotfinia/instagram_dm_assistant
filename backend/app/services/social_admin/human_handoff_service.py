from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.models import Conversation


@dataclass(frozen=True)
class HumanHandoffResult:
    required: bool
    reason: str
    conversation_id: str | None = None


class HumanHandoffService:
    """Final safety layer after automation, catalog logic, scenario routing, and LLM fallback."""

    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def trigger(
        self, conversation_id: UUID | str | None, reason: str = "human_handoff_required"
    ) -> HumanHandoffResult:
        if self.db is not None and conversation_id is not None:
            conv = self.db.get(Conversation, UUID(str(conversation_id)))
            if conv is not None:
                conv.handoff_required = True
                conv.handoff_reason = reason
                self.db.add(conv)
        return HumanHandoffResult(True, reason, str(conversation_id) if conversation_id else None)

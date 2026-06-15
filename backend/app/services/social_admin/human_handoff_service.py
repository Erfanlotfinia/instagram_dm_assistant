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
        conversation_id_str = str(conversation_id) if conversation_id is not None else None
        internal_conversation_id = self._try_parse_internal_conversation_id(conversation_id)
        if self.db is not None and internal_conversation_id is not None:
            conv = self.db.get(Conversation, internal_conversation_id)
            if conv is not None:
                conv.handoff_required = True
                conv.handoff_reason = reason
                self.db.add(conv)
        return HumanHandoffResult(True, reason, conversation_id_str)

    @staticmethod
    def _try_parse_internal_conversation_id(conversation_id: UUID | str | None) -> UUID | None:
        """Return an internal conversation UUID, or None for external channel ids.

        Modira normalized messages carry channel-agnostic string conversation ids
        such as Telegram chat ids or provider conversation keys. Persisting handoff
        state requires the internal database UUID, so external ids must not crash
        the safety path.
        """
        if conversation_id is None:
            return None
        if isinstance(conversation_id, UUID):
            return conversation_id
        try:
            return UUID(str(conversation_id))
        except ValueError:
            return None

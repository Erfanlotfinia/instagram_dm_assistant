from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.domain.models import Conversation, Customer, Message
from app.schemas.conversation import ConversationListFilters


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        return self.db.get(Conversation, conversation_id)

    def get_for_shop(self, shop_id: UUID, conversation_id: UUID) -> Conversation | None:
        stmt = (
            select(Conversation)
            .options(joinedload(Conversation.customer), joinedload(Conversation.instagram_account))
            .where(Conversation.id == conversation_id, Conversation.shop_id == shop_id)
        )
        return self.db.scalar(stmt)

    def list_for_shop(self, shop_id: UUID, filters: ConversationListFilters | None = None) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .options(joinedload(Conversation.customer), joinedload(Conversation.slots), joinedload(Conversation.shop))
            .where(Conversation.shop_id == shop_id)
        )
        if filters is not None:
            if filters.state is not None:
                stmt = stmt.where(Conversation.state == filters.state)
            if filters.handoff_required is not None:
                stmt = stmt.where(Conversation.handoff_required.is_(filters.handoff_required))
            if filters.assigned_operator_id is not None:
                stmt = stmt.where(Conversation.assigned_operator_id == filters.assigned_operator_id)
            if filters.updated_from is not None:
                stmt = stmt.where(Conversation.updated_at >= filters.updated_from)
            if filters.updated_to is not None:
                stmt = stmt.where(Conversation.updated_at <= filters.updated_to)
            if filters.search:
                term = f"%{filters.search.strip()}%"
                stmt = stmt.join(Customer, Customer.id == Conversation.customer_id).where(
                    or_(
                        Customer.full_name.ilike(term),
                        Customer.instagram_user_id.ilike(term),
                    )
                )
        stmt = stmt.order_by(Conversation.last_message_at.desc().nullslast(), Conversation.updated_at.desc())
        return list(self.db.scalars(stmt).unique().all())

    def get_open_for_participants(
        self,
        shop_id: UUID,
        instagram_account_id: UUID,
        customer_id: UUID,
    ) -> Conversation | None:
        stmt = (
            select(Conversation)
            .where(
                Conversation.shop_id == shop_id,
                Conversation.instagram_account_id == instagram_account_id,
                Conversation.customer_id == customer_id,
            )
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def create(self, conversation: Conversation) -> Conversation:
        self.db.add(conversation)
        self.db.flush()
        return conversation

    def get_last_message(self, conversation_id: UUID) -> Message | None:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

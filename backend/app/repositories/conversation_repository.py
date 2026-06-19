from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.domain.enums import AgentWorkflowState, ChannelProvider, ConversationState
from app.domain.models import Conversation, ConversationSlots, Customer, Message, Order, Product
from app.schemas.conversation import ConversationListFilters


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        stmt = (
            select(Conversation)
            .options(joinedload(Conversation.slots), joinedload(Conversation.customer))
            .where(Conversation.id == conversation_id)
        )
        return self.db.scalar(stmt)

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
            .options(
                joinedload(Conversation.customer),
                joinedload(Conversation.slots),
                joinedload(Conversation.shop),
                joinedload(Conversation.assigned_operator),
            )
            .where(Conversation.shop_id == shop_id)
        )
        if filters is not None:
            if filters.state is not None:
                stmt = stmt.where(Conversation.state == filters.state)
            if filters.handoff_required is not None:
                stmt = stmt.where(Conversation.handoff_required.is_(filters.handoff_required))
            if filters.assigned_operator_id is not None:
                stmt = stmt.where(Conversation.assigned_operator_id == filters.assigned_operator_id)
            if filters.unassigned is True:
                stmt = stmt.where(Conversation.assigned_operator_id.is_(None))
            if filters.updated_from is not None:
                stmt = stmt.where(Conversation.updated_at >= filters.updated_from)
            if filters.updated_to is not None:
                stmt = stmt.where(Conversation.updated_at <= filters.updated_to)
            if filters.is_simulation is not None:
                stmt = stmt.where(Conversation.is_simulation.is_(filters.is_simulation))
            if filters.needs_attention is True:
                stmt = stmt.where(Conversation.needs_attention.is_(True))
            if filters.priority_level is not None:
                stmt = stmt.where(Conversation.priority_level == filters.priority_level)
            if filters.priority_levels:
                stmt = stmt.where(Conversation.priority_level.in_(filters.priority_levels))
            if filters.waiting_for_payment is True:
                stmt = stmt.where(
                    Conversation.workflow_state == AgentWorkflowState.WAITING_FOR_PAYMENT
                )
            if filters.ready_to_order is True:
                stmt = stmt.where(
                    Conversation.workflow_state == AgentWorkflowState.WAITING_FOR_CONFIRMATION
                )
            if filters.low_confidence is True:
                stmt = stmt.where(Conversation.preview_required.is_(True))
            if filters.search:
                term = f"%{filters.search.strip()}%"
                product_subq = (
                    select(ConversationSlots.conversation_id)
                    .join(Product, Product.id == ConversationSlots.product_id)
                    .where(Product.title.ilike(term))
                )
                stmt = stmt.outerjoin(Customer, Customer.id == Conversation.customer_id).outerjoin(
                    Order, Order.conversation_id == Conversation.id
                )
                stmt = stmt.where(
                    or_(
                        Customer.full_name.ilike(term),
                        Customer.instagram_user_id.ilike(term),
                        Customer.phone.ilike(term),
                        Order.id.cast(str).ilike(term),
                        Conversation.id.in_(product_subq),
                    )
                )
        stmt = stmt.order_by(
            Conversation.priority_score.desc(),
            Conversation.last_message_at.desc().nullslast(),
            Conversation.updated_at.desc(),
        )
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

    def get_or_create_conversation_by_channel(
        self,
        *,
        shop_id: UUID,
        customer_id: UUID,
        provider: ChannelProvider,
        channel_account_id: UUID,
        external_conversation_id: str,
        external_thread_id: str | None = None,
    ) -> Conversation:
        conversation = self.db.scalar(
            select(Conversation).where(
                Conversation.shop_id == shop_id,
                Conversation.channel_provider == provider.value,
                Conversation.channel_account_id == channel_account_id,
                Conversation.external_conversation_id == external_conversation_id,
                Conversation.external_thread_id == external_thread_id,
                Conversation.state == ConversationState.OPEN,
            )
        )
        if conversation is not None:
            return conversation
        return self.create(
            Conversation(
                shop_id=shop_id,
                customer_id=customer_id,
                channel_provider=provider.value,
                channel_account_id=channel_account_id,
                external_conversation_id=external_conversation_id,
                external_thread_id=external_thread_id,
                channel_conversation_id=external_conversation_id,
                state=ConversationState.OPEN,
            )
        )

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

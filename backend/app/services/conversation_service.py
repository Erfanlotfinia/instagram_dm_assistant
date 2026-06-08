from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.roles import has_minimum_role
from app.domain.enums import ConversationState, SuggestedReplyStatus, UserRole
from app.domain.enums import AgentWorkflowState
from app.repositories.agent_action_repository import AgentActionRepository
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.conversation_slots_repository import ConversationSlotsRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.agent import AgentActionRead, AgentRunRead, ConversationSlotsRead
from app.schemas.conversation import (
    ConversationDetailRead,
    ConversationHandoffResponse,
    ConversationListFilters,
    ConversationRead,
    ConversationResolveResponse,
    CustomerRead,
    CustomerUpdate,
    LinkedOrderSummary,
    LinkedProductSummary,
    MessageCreate,
    MessageRead,
)
from app.schemas.order import OrderRead
from app.schemas.suggested_reply import SuggestedReplyRead
from app.services.audit_service import AuditService
from app.services.instagram_send_service import InstagramSendService
from app.services.order_service import OrderService
from app.services.shop_service import ShopService
from app.domain.models import SuggestedReply
from sqlalchemy import select


class ConversationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)
        self.slots = ConversationSlotsRepository(db)
        self.agent_runs = AgentRunRepository(db)
        self.agent_actions = AgentActionRepository(db)
        self.customers = CustomerRepository(db)
        self.orders = OrderRepository(db)
        self.products = ProductRepository(db)
        self.shop_service = ShopService(db)

    def list_conversations(
        self,
        shop_id: UUID,
        user,
        filters: ConversationListFilters | None = None,
    ) -> list[ConversationRead]:
        self.shop_service.get_shop(shop_id, user)
        items: list[ConversationRead] = []
        for conversation in self.conversations.list_for_shop(shop_id, filters):
            read = self._to_conversation_read(conversation)
            last_message = self.conversations.get_last_message(conversation.id)
            if last_message is not None:
                read.last_message_text = last_message.text
                read.last_message_direction = last_message.direction
            items.append(read)
        return items

    def get_conversation_detail(
        self,
        shop_id: UUID,
        conversation_id: UUID,
        user,
    ) -> ConversationDetailRead:
        self.shop_service.get_shop(shop_id, user)
        conversation = self.conversations.get_for_shop(shop_id, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        detail = ConversationDetailRead.model_validate(conversation)
        detail.confidence_score = self._extract_confidence(conversation)
        if conversation.customer is not None:
            detail.customer = CustomerRead.model_validate(conversation.customer)

        last_message = self.conversations.get_last_message(conversation.id)
        if last_message is not None:
            detail.last_message_text = last_message.text
            detail.last_message_direction = last_message.direction

        include_raw = has_minimum_role(user.role, UserRole.ADMIN)
        detail.messages = [
            self._to_message_read(message, include_raw=include_raw)
            for message in self.messages.list_for_conversation(conversation.id)
        ]
        slots = self.slots.get_for_conversation(conversation.id)
        if slots is not None:
            detail.slots = ConversationSlotsRead.model_validate(slots)
            if slots.product_id is not None:
                product = self.products.get_by_id(slots.product_id)
                if product is not None:
                    detail.linked_product = LinkedProductSummary(id=product.id, title=product.title)

        active_order = self.orders.get_active_for_conversation(conversation.id)
        if active_order is not None:
            detail.linked_order = LinkedOrderSummary(
                id=active_order.id,
                status=active_order.status.value,
                payment_status=active_order.payment_status.value,
                total_amount=str(active_order.total_amount),
            )

        detail.agent_runs = [
            AgentRunRead.model_validate(run) for run in self.agent_runs.list_for_conversation(conversation.id)
        ]
        detail.agent_actions = [
            AgentActionRead.model_validate(action)
            for action in self.agent_actions.list_for_conversation(conversation.id)
        ]
        suggested_stmt = (
            select(SuggestedReply)
            .where(
                SuggestedReply.conversation_id == conversation.id,
                SuggestedReply.status == SuggestedReplyStatus.PENDING,
            )
            .order_by(SuggestedReply.created_at.desc())
        )
        detail.suggested_replies = [SuggestedReplyRead.model_validate(item) for item in self.db.scalars(suggested_stmt).all()]
        return detail

    def send_manual_message(
        self,
        shop_id: UUID,
        conversation_id: UUID,
        user,
        payload: MessageCreate,
    ) -> MessageRead:
        self.shop_service.get_shop(shop_id, user)
        conversation = self._get_conversation_or_404(shop_id, conversation_id)
        if not conversation.agent_paused and conversation.assigned_operator_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Take over the conversation before sending manual messages",
            )
        message = InstagramSendService(self.db).send_text_message(conversation.id, payload.text)
        conversation.last_message_at = message.created_at
        self.db.commit()
        self.db.refresh(message)
        return self._to_message_read(message, include_raw=has_minimum_role(user.role, UserRole.ADMIN))

    def take_over(
        self,
        shop_id: UUID,
        conversation_id: UUID,
        user,
    ) -> ConversationHandoffResponse:
        self.shop_service.get_shop(shop_id, user)
        conversation = self._get_conversation_or_404(shop_id, conversation_id)
        conversation.agent_paused = True
        conversation.assigned_operator_id = user.id
        conversation.workflow_state = AgentWorkflowState.HUMAN_HANDOFF
        conversation.handoff_required = True
        if not conversation.handoff_reason:
            conversation.handoff_reason = f"Operator {user.full_name} took over"
        AuditService(self.db).log(
            action="handoff_take",
            entity_type="conversation",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(conversation.id),
        )
        self.db.commit()
        self.db.refresh(conversation)
        return self._handoff_response(conversation)

    def release_to_agent(
        self,
        shop_id: UUID,
        conversation_id: UUID,
        user,
    ) -> ConversationHandoffResponse:
        self.shop_service.get_shop(shop_id, user)
        conversation = self._get_conversation_or_404(shop_id, conversation_id)
        conversation.agent_paused = False
        conversation.assigned_operator_id = None
        conversation.handoff_required = False
        conversation.handoff_reason = None
        conversation.workflow_state = AgentWorkflowState.IDLE
        conversation.state = ConversationState.OPEN
        conversation.agent_failure_count = 0
        AuditService(self.db).log(
            action="handoff_release",
            entity_type="conversation",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(conversation.id),
        )
        self.db.commit()
        self.db.refresh(conversation)
        return self._handoff_response(conversation)

    def mark_resolved(
        self,
        shop_id: UUID,
        conversation_id: UUID,
        user,
    ) -> ConversationResolveResponse:
        self.shop_service.get_shop(shop_id, user)
        conversation = self._get_conversation_or_404(shop_id, conversation_id)
        conversation.state = ConversationState.CLOSED
        conversation.handoff_required = False
        conversation.agent_paused = False
        conversation.assigned_operator_id = None
        self.db.commit()
        self.db.refresh(conversation)
        return ConversationResolveResponse(conversation_id=conversation.id, state=conversation.state)

    def update_customer(
        self,
        shop_id: UUID,
        conversation_id: UUID,
        user,
        payload: CustomerUpdate,
    ) -> CustomerRead:
        self.shop_service.get_shop(shop_id, user)
        conversation = self._get_conversation_or_404(shop_id, conversation_id)
        customer = self.customers.get_by_id(conversation.customer_id)
        if customer is None or customer.shop_id != shop_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(customer, field, value)
        self.db.commit()
        self.db.refresh(customer)
        return CustomerRead.model_validate(customer)

    def create_order_from_conversation(
        self,
        shop_id: UUID,
        conversation_id: UUID,
        user,
    ) -> OrderRead:
        self.shop_service.get_shop(shop_id, user)
        conversation = self._get_conversation_or_404(shop_id, conversation_id)
        slots = self.slots.get_for_conversation(conversation.id)
        if slots is None or slots.product_id is None or slots.product_variant_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conversation slots must include product and variant before creating an order",
            )

        from app.repositories.variant_repository import VariantRepository

        product = self.products.get_by_id(slots.product_id)
        variant = VariantRepository(self.db).get_by_id(slots.product_variant_id)
        if product is None or variant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product or variant not found")

        order_service = OrderService(self.db)
        order = order_service.upsert_draft_from_conversation(conversation, slots, product, variant)
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create order: missing required customer or slot information",
            )
        return order_service._to_read(order)

    def _get_conversation_or_404(self, shop_id: UUID, conversation_id: UUID):
        conversation = self.conversations.get_for_shop(shop_id, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        return conversation

    @staticmethod
    def _handoff_response(conversation) -> ConversationHandoffResponse:
        return ConversationHandoffResponse(
            conversation_id=conversation.id,
            workflow_state=conversation.workflow_state,
            handoff_required=conversation.handoff_required,
            handoff_reason=conversation.handoff_reason,
            agent_paused=conversation.agent_paused,
            assigned_operator_id=conversation.assigned_operator_id,
        )

    @staticmethod
    def _to_message_read(message, include_raw: bool) -> MessageRead:
        data = MessageRead.model_validate(message)
        if not include_raw:
            data.raw_payload = None
        return data

    @staticmethod
    def _extract_confidence(conversation) -> float | None:
        if conversation.slots is not None and conversation.slots.confidence:
            confidence = conversation.slots.confidence
            if isinstance(confidence, dict):
                values = [v for v in (confidence.get("intent"), confidence.get("slots")) if isinstance(v, (int, float))]
                if values:
                    return sum(values) / len(values)
        return None

    @staticmethod
    def _to_conversation_read(conversation) -> ConversationRead:
        read = ConversationRead.model_validate(conversation)
        read.confidence_score = ConversationService._extract_confidence(conversation)
        if conversation.shop is not None and conversation.shop.agent_studio_settings is not None:
            read.agent_mode = conversation.shop.agent_studio_settings.mode
        return read

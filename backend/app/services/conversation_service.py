from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.roles import has_minimum_role
from app.domain.enums import (
    AgentActionStatus,
    AgentWorkflowState,
    ChannelProvider,
    ConversationEventType,
    ConversationResponseMode,
    ConversationState,
    MessageDirection,
    SuggestedReplyStatus,
    UserRole,
)
from app.domain.models import AgentAction, AgentDecisionTrace, Message, SuggestedReply, User
from app.repositories.agent_action_repository import AgentActionRepository
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.conversation_slots_repository import ConversationSlotsRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.agent import AgentActionRead, AgentRunRead, ConversationSlotsRead
from app.schemas.conversation import (
    ConversationAssignResponse,
    ConversationDetailRead,
    ConversationEventRead,
    ConversationHandoffResponse,
    ConversationListFilters,
    ConversationRead,
    ConversationResolveResponse,
    CustomerRead,
    CustomerSummary,
    InventoryStatusRead,
    LinkedOrderSummary,
    LinkedProductSummary,
    MessageCreate,
    MessageRead,
    OperatorSummary,
)
from app.schemas.customer import CustomerUpdate
from app.schemas.order import OrderRead
from app.schemas.suggested_reply import SuggestedReplyRead
from app.services.audit_service import AuditService
from app.services.conversation_event_service import ConversationEventService
from app.services.conversation_priority_service import ConversationPriorityService
from app.services.customer_service import CustomerService
from app.services.channel_outbound_service import ChannelOutboundService, operator_action_send_key
from app.services.order_service import OrderService
from app.services.shop_service import ShopService


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
        self.variants = VariantRepository(db)
        self.shop_service = ShopService(db)
        self.priority_service = ConversationPriorityService(db)
        self.event_service = ConversationEventService(db)

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
            active_order = self.orders.get_linked_for_conversation(conversation.id)
            if active_order is not None:
                read.linked_order = LinkedOrderSummary(
                    id=active_order.id,
                    status=active_order.status.value,
                    payment_status=active_order.payment_status.value,
                    total_amount=str(active_order.total_amount),
                )
            if conversation.slots and conversation.slots.product_id:
                product = self.products.get_by_id(conversation.slots.product_id)
                if product is not None:
                    read.linked_product = LinkedProductSummary(id=product.id, title=product.title)
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
            detail.customer_profile = CustomerService(self.db).get_profile(
                shop_id, conversation.customer_id, user
            )
        if conversation.assigned_operator is not None:
            detail.assigned_operator = OperatorSummary(
                id=conversation.assigned_operator.id,
                full_name=conversation.assigned_operator.full_name,
            )

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
            if slots.product_variant_id is not None:
                variant = self.variants.get_by_id(slots.product_variant_id)
                if variant is not None:
                    available = variant.stock_quantity - variant.reserved_quantity
                    detail.inventory_status = InventoryStatusRead(
                        variant_id=variant.id,
                        in_stock=available > 0,
                        available_quantity=available,
                    )

        active_order = self.orders.get_linked_for_conversation(conversation.id)
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
        detail.suggested_replies = [
            SuggestedReplyRead.model_validate(item) for item in self.db.scalars(suggested_stmt).all()
        ]
        detail.events = [
            ConversationEventRead.model_validate(event)
            for event in self.event_service.list_for_conversation(conversation.id)
        ]
        detail.decision_trace_summary = self._decision_trace_summary_for_conversation(
            conversation.id,
            detail.agent_actions,
        )
        return detail

    async def mark_telegram_business_read(
        self,
        shop_id: UUID,
        conversation_id: UUID,
    ) -> None:
        conversation = self.conversations.get_for_shop(shop_id, conversation_id)
        if conversation is None or conversation.channel_provider != ChannelProvider.TELEGRAM.value:
            return

        from app.domain.enums import TelegramConnectionMode
        from app.services.channel_account_service import ChannelAccountService
        from app.services.telegram_business_connection_service import (
            TelegramBusinessConnectionService,
        )

        account = ChannelAccountService(self.db).get(conversation.shop_id, conversation.channel_account_id)
        if account is None:
            return
        mode = account.connection_mode or TelegramConnectionMode.BOT
        if mode not in {TelegramConnectionMode.BUSINESS, TelegramConnectionMode.HYBRID}:
            return
        if not account.telegram_business_enabled:
            return

        last_inbound = self.db.scalar(
            select(Message)
            .where(
                Message.conversation_id == conversation.id,
                Message.direction == MessageDirection.INBOUND,
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        if last_inbound is None or not last_inbound.external_message_id:
            return

        connection_id = None
        meta = last_inbound.normalized_payload_json or {}
        if isinstance(meta.get("business_connection_id"), str):
            connection_id = meta["business_connection_id"]
        elif isinstance(meta.get("raw_payload"), dict):
            connection_id = meta["raw_payload"].get("business_connection_id")

        await TelegramBusinessConnectionService(self.db).mark_read(
            account,
            conversation.external_conversation_id,
            last_inbound.external_message_id,
            connection_id=connection_id,
        )

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
        action = AgentAction(
            conversation_id=conversation.id,
            action_name="manual_send",
            input_json={"text": payload.text},
            output_json={},
            status=AgentActionStatus.SUCCESS,
        )
        self.agent_actions.create(action)
        self.db.flush()
        message = ChannelOutboundService(self.db).send_text_message(
            conversation.id,
            payload.text,
            idempotency_key=operator_action_send_key(action.id),
        )
        conversation.last_message_at = message.created_at
        conversation.last_operator_action_at = datetime.now(UTC)
        self.event_service.record(
            conversation.id,
            ConversationEventType.OUTBOUND_MESSAGE,
            description=payload.text[:200],
            metadata={"message_id": str(message.id)},
            created_by_user_id=user.id,
        )
        AuditService(self.db).log(
            action="manual_message_sent",
            entity_type="conversation",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(conversation.id),
            metadata={"message_id": str(message.id)},
        )
        self.priority_service.refresh(conversation.id)
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
        conversation.response_mode = ConversationResponseMode.HUMAN
        conversation.workflow_state = AgentWorkflowState.HUMAN_HANDOFF
        conversation.handoff_required = True
        conversation.last_operator_action_at = datetime.now(UTC)
        if not conversation.handoff_reason:
            conversation.handoff_reason = f"Operator {user.full_name} took over"
        self.event_service.record(
            conversation.id,
            ConversationEventType.OPERATOR_TOOK_OVER,
            created_by_user_id=user.id,
        )
        AuditService(self.db).log(
            action="operator_took_over",
            entity_type="conversation",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(conversation.id),
        )
        self.priority_service.refresh(conversation.id)
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
        conversation.response_mode = ConversationResponseMode.AI
        conversation.handoff_required = False
        conversation.handoff_reason = None
        conversation.workflow_state = AgentWorkflowState.IDLE
        conversation.state = ConversationState.OPEN
        conversation.agent_failure_count = 0
        conversation.last_operator_action_at = datetime.now(UTC)
        self.event_service.record(
            conversation.id,
            ConversationEventType.OPERATOR_RELEASED_AGENT,
            created_by_user_id=user.id,
        )
        AuditService(self.db).log(
            action="operator_released_agent",
            entity_type="conversation",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(conversation.id),
        )
        self.priority_service.refresh(conversation.id)
        self.db.commit()
        self.db.refresh(conversation)
        return self._handoff_response(conversation)

    def set_response_mode(
        self,
        shop_id: UUID,
        conversation_id: UUID,
        mode: ConversationResponseMode,
        user,
    ) -> ConversationHandoffResponse:
        self.shop_service.get_shop(shop_id, user)
        conversation = self._get_conversation_or_404(shop_id, conversation_id)
        previous = conversation.response_mode
        conversation.response_mode = mode
        if mode == ConversationResponseMode.HUMAN:
            conversation.agent_paused = True
            conversation.assigned_operator_id = user.id
            conversation.workflow_state = AgentWorkflowState.HUMAN_HANDOFF
            conversation.handoff_required = True
        elif mode == ConversationResponseMode.AI:
            conversation.agent_paused = False
            conversation.assigned_operator_id = None
            conversation.handoff_required = False
            conversation.handoff_reason = None
            conversation.workflow_state = AgentWorkflowState.IDLE
        elif mode == ConversationResponseMode.HYBRID:
            conversation.agent_paused = False
            conversation.preview_required = True
            conversation.preview_reason = "hybrid_response_mode"
        elif mode == ConversationResponseMode.PAUSED:
            conversation.agent_paused = True
            conversation.preview_required = False
        conversation.last_operator_action_at = datetime.now(UTC)
        AuditService(self.db).log(
            action="conversation_response_mode_changed",
            entity_type="conversation",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(conversation.id),
            metadata={"from": previous.value, "to": mode.value},
        )
        self.priority_service.refresh(conversation.id)
        self.db.commit()
        self.db.refresh(conversation)
        return self._handoff_response(conversation)

    def assign_conversation(
        self,
        shop_id: UUID,
        conversation_id: UUID,
        operator_id: UUID,
        user,
    ) -> ConversationAssignResponse:
        self.shop_service.get_shop(shop_id, user)
        conversation = self._get_conversation_or_404(shop_id, conversation_id)
        operator = self.db.get(User, operator_id)
        if operator is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")
        conversation.assigned_operator_id = operator_id
        conversation.last_operator_action_at = datetime.now(UTC)
        self.event_service.record(
            conversation.id,
            ConversationEventType.CONVERSATION_ASSIGNED,
            description=f"Assigned to {operator.full_name}",
            metadata={"operator_id": str(operator_id)},
            created_by_user_id=user.id,
        )
        AuditService(self.db).log(
            action="conversation_assigned",
            entity_type="conversation",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(conversation.id),
            metadata={"operator_id": str(operator_id)},
        )
        self.priority_service.refresh(conversation.id)
        self.db.commit()
        return ConversationAssignResponse(
            conversation_id=conversation.id,
            assigned_operator_id=operator_id,
            assigned_operator_name=operator.full_name,
        )

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
        self.priority_service.refresh(conversation.id)
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
        conversation.last_operator_action_at = datetime.now(UTC)
        self.event_service.record(
            conversation.id,
            ConversationEventType.CUSTOMER_PROFILE_UPDATED,
            metadata={"updated_fields": list(updates.keys())},
            created_by_user_id=user.id,
        )
        AuditService(self.db).log(
            action="customer_profile_updated",
            entity_type="customer",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(customer.id),
            metadata={"updated_fields": list(updates.keys())},
        )
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

        product = self.products.get_by_id(slots.product_id)
        variant = self.variants.get_by_id(slots.product_variant_id)
        if product is None or variant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product or variant not found")

        order_service = OrderService(self.db)
        order = order_service.upsert_draft_from_conversation(conversation, slots, product, variant)
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create order: missing required customer or slot information",
            )
        self.event_service.record(
            conversation.id,
            ConversationEventType.DRAFT_ORDER_CREATED,
            metadata={"order_id": str(order.id)},
            created_by_user_id=user.id,
        )
        self.priority_service.refresh(conversation.id)
        self.db.commit()
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
            response_mode=conversation.response_mode,
            assigned_operator_id=conversation.assigned_operator_id,
            priority_score=conversation.priority_score,
            priority_level=conversation.priority_level,
            needs_attention=conversation.needs_attention,
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
                values = [
                    v for v in (confidence.get("intent"), confidence.get("slots")) if isinstance(v, (int, float))
                ]
                if values:
                    return sum(values) / len(values)
        return None

    def _decision_trace_summary_for_conversation(
        self,
        conversation_id: UUID,
        agent_actions: list,
    ) -> str | None:
        summary = self._build_decision_trace_summary(agent_actions)
        if summary is not None:
            return summary

        trace = self.db.scalar(
            select(AgentDecisionTrace)
            .where(AgentDecisionTrace.conversation_id == conversation_id)
            .order_by(AgentDecisionTrace.created_at.desc())
            .limit(1)
        )
        if trace is None:
            return None
        if trace.reasoning_summary:
            return trace.reasoning_summary

        parts: list[str] = []
        if trace.intent:
            parts.append(f"Intent: {trace.intent.replace('_', ' ')}")
        if trace.next_state:
            parts.append(f"State: {trace.next_state.replace('_', ' ')}")
        return " — ".join(parts) if parts else None

    @staticmethod
    def _build_decision_trace_summary(agent_actions: list) -> str | None:
        if not agent_actions:
            return None
        recent = agent_actions[:5]
        parts = [f"{action.action_name} ({action.status})" for action in recent]
        return " → ".join(parts)

    @staticmethod
    def _to_conversation_read(conversation) -> ConversationRead:
        operator_summary = None
        if conversation.assigned_operator is not None:
            operator_summary = OperatorSummary(
                id=conversation.assigned_operator.id,
                full_name=conversation.assigned_operator.full_name,
            )
        customer_summary = None
        if conversation.customer is not None:
            customer_summary = CustomerSummary(
                id=conversation.customer.id,
                instagram_user_id=conversation.customer.instagram_user_id,
                full_name=conversation.customer.full_name,
            )

        read = ConversationRead.model_validate(
            {
                **{
                    field: getattr(conversation, field)
                    for field in ConversationRead.model_fields
                    if field not in {"customer", "assigned_operator", "last_message_text", "last_message_direction", "confidence_score", "agent_mode", "linked_product", "linked_order"}
                    and hasattr(conversation, field)
                },
                "customer": customer_summary,
                "assigned_operator": operator_summary,
            }
        )
        read.confidence_score = ConversationService._extract_confidence(conversation)
        if conversation.shop is not None and conversation.shop.agent_studio_settings is not None:
            read.agent_mode = conversation.shop.agent_studio_settings.mode
        return read

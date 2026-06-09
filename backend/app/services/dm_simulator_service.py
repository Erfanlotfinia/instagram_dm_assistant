from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.enums import ConversationState, MessageChannel, MessageDirection, MessageType, OrderStatus
from app.domain.models import (
    AgentAction,
    AgentDecisionAudit,
    AgentDecisionTrace,
    Conversation,
    Customer,
    Message,
    Order,
    User,
)
from app.repositories.instagram_account_repository import InstagramAccountRepository
from app.schemas.simulator import DMSimulatorRequest, DMSimulatorResponse, SimulatorRunSummary
from app.services.conversation_orchestrator import ConversationOrchestrator
from app.services.shop_service import ShopService


class DMSimulatorService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.shop_service = ShopService(db)
        self.accounts = InstagramAccountRepository(db)

    def run(
        self,
        shop_id: UUID,
        payload: DMSimulatorRequest,
        user: User,
        *,
        orchestrator: ConversationOrchestrator | None = None,
    ) -> DMSimulatorResponse:
        self.shop_service.get_shop(shop_id, user)
        account = next(
            (a for a in self.accounts.list_for_shop(shop_id) if a.id == payload.instagram_account_id),
            None,
        )
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instagram account not found")
        customer = self._get_or_create_customer(shop_id, payload.instagram_user_id)
        conversation = Conversation(
            shop_id=shop_id,
            instagram_account_id=account.id,
            customer_id=customer.id,
            state=ConversationState.OPEN,
            is_simulation=True,
            channel_provider=MessageChannel.INSTAGRAM.value,
            channel_conversation_id=payload.instagram_user_id,
            channel_customer_id=payload.instagram_user_id,
        )
        self.db.add(conversation)
        self.db.flush()
        message = Message(
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
            channel=MessageChannel.INSTAGRAM,
            instagram_message_id=f"simulation-{uuid4()}",
            message_type=MessageType.TEXT,
            text=payload.message_text,
            is_simulation=True,
            raw_payload={"_meta": {"shared_post_url": payload.shared_post_url} if payload.shared_post_url else {}},
        )
        self.db.add(message)
        self.db.flush()
        runner = orchestrator or ConversationOrchestrator(self.db)
        runner.process_inbound_message(conversation.id, message.id)
        self.db.refresh(conversation)
        self.db.refresh(message)

        audit = self.db.scalar(
            select(AgentDecisionAudit)
            .where(AgentDecisionAudit.conversation_id == conversation.id)
            .order_by(AgentDecisionAudit.created_at.desc())
        )
        auto_send_action = self.db.scalar(
            select(AgentAction)
            .where(
                AgentAction.conversation_id == conversation.id,
                AgentAction.action_name == "auto_send_decision",
            )
            .order_by(AgentAction.created_at.desc())
        )
        draft_order = self.db.scalar(
            select(Order)
            .where(
                Order.conversation_id == conversation.id,
                Order.is_simulation.is_(True),
                Order.status.in_(
                    [OrderStatus.DRAFT, OrderStatus.WAITING_FOR_CLARIFICATION, OrderStatus.READY_FOR_CONFIRMATION]
                ),
            )
            .order_by(Order.created_at.desc())
        )

        decision_trace = self._build_decision_trace(conversation, message, audit, auto_send_action)
        if audit is not None:
            trace_row = AgentDecisionTrace(
                conversation_id=conversation.id,
                message_id=message.id,
                intent=audit.extracted_intent,
                extracted_slots=audit.extracted_slots,
                product_candidates=audit.product_candidates,
                selected_product_id=audit.chosen_product_id,
                variant_resolution=audit.variant_resolver_result,
                inventory_result=audit.inventory_result,
                order_action={},
                next_state=audit.next_state,
                auto_send_allowed=auto_send_action.output_json.get("auto_send_allowed", False) if auto_send_action else False,
                human_handoff_required=conversation.handoff_required,
                reasoning_summary=(audit.decision_reason or "Business-level simulator decision")[:500],
            )
            self.db.add(trace_row)
            self.db.commit()

        return DMSimulatorResponse(
            conversation_id=conversation.id,
            message_id=message.id,
            intent=audit.extracted_intent if audit else conversation.last_intent,
            extracted_slots=audit.extracted_slots if audit else {},
            product_resolution={
                "chosen_product_id": str(audit.chosen_product_id) if audit and audit.chosen_product_id else None,
                "product_candidates": audit.product_candidates if audit else [],
            },
            variant_resolution=audit.variant_resolver_result if audit else {},
            inventory_result=audit.inventory_result if audit else {},
            next_state=conversation.workflow_state.value,
            suggested_reply=conversation.suggested_outbound or (audit.outbound_message if audit else None),
            auto_send_decision=auto_send_action.output_json if auto_send_action else {},
            handoff_reason=conversation.handoff_reason,
            draft_order=self._serialize_draft_order(draft_order),
            decision_trace=decision_trace,
        )

    def list_runs(self, shop_id: UUID, user: User, *, limit: int = 20) -> list[SimulatorRunSummary]:
        self.shop_service.get_shop(shop_id, user)
        conversations = list(
            self.db.scalars(
                select(Conversation)
                .where(Conversation.shop_id == shop_id, Conversation.is_simulation.is_(True))
                .order_by(Conversation.created_at.desc())
                .limit(limit)
            ).all()
        )
        summaries: list[SimulatorRunSummary] = []
        for conversation in conversations:
            inbound = self.db.scalar(
                select(Message)
                .where(
                    Message.conversation_id == conversation.id,
                    Message.direction == MessageDirection.INBOUND,
                )
                .order_by(Message.created_at.asc())
            )
            summaries.append(
                SimulatorRunSummary(
                    conversation_id=conversation.id,
                    message_id=inbound.id if inbound else None,
                    created_at=conversation.created_at,
                    intent=conversation.last_intent,
                    next_state=conversation.workflow_state.value if conversation.workflow_state else None,
                    suggested_reply=conversation.suggested_outbound,
                    message_preview=(inbound.text[:120] if inbound and inbound.text else None),
                )
            )
        return summaries

    def reset(self, shop_id: UUID, user: User) -> int:
        self.shop_service.get_shop(shop_id, user)
        ids = list(
            self.db.scalars(
                select(Conversation.id).where(
                    Conversation.shop_id == shop_id,
                    Conversation.is_simulation.is_(True),
                )
            ).all()
        )
        if not ids:
            return 0
        self.db.execute(delete(Conversation).where(Conversation.id.in_(ids)))
        self.db.commit()
        return len(ids)

    def _get_or_create_customer(self, shop_id: UUID, instagram_user_id: str) -> Customer:
        customer = self.db.scalar(
            select(Customer).where(
                Customer.shop_id == shop_id,
                Customer.instagram_user_id == instagram_user_id,
            )
        )
        if customer:
            return customer
        customer = Customer(
            shop_id=shop_id,
            instagram_user_id=instagram_user_id,
            full_name="Simulation Customer",
        )
        self.db.add(customer)
        self.db.flush()
        return customer

    @staticmethod
    def _serialize_draft_order(order: Order | None) -> dict | None:
        if order is None:
            return None
        return {
            "id": str(order.id),
            "status": order.status.value,
            "total_amount": str(order.total_amount),
            "currency": order.currency,
            "is_simulation": order.is_simulation,
        }

    @staticmethod
    def _build_decision_trace(
        conversation: Conversation,
        message: Message,
        audit: AgentDecisionAudit | None,
        auto_send_action: AgentAction | None,
    ) -> dict:
        return {
            "conversation_id": str(conversation.id),
            "message_id": str(message.id),
            "is_simulation": conversation.is_simulation,
            "intent": audit.extracted_intent if audit else conversation.last_intent,
            "extracted_slots": audit.extracted_slots if audit else {},
            "product_candidates": audit.product_candidates if audit else [],
            "chosen_product_id": str(audit.chosen_product_id) if audit and audit.chosen_product_id else None,
            "variant_resolution": audit.variant_resolver_result if audit else {},
            "inventory_result": audit.inventory_result if audit else {},
            "next_state": conversation.workflow_state.value if conversation.workflow_state else None,
            "auto_send_decision": auto_send_action.output_json if auto_send_action else {},
            "handoff_reason": conversation.handoff_reason,
            "preview_required": conversation.preview_required,
        }

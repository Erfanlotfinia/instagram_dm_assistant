from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.enums import ConversationState, MessageChannel, MessageDirection, MessageType
from app.domain.models import AgentAction, AgentDecisionAudit, AgentDecisionTrace, Conversation, Customer, Message, User
from app.repositories.instagram_account_repository import InstagramAccountRepository
from app.schemas.simulator import DMSimulatorRequest, DMSimulatorResponse
from app.services.conversation_orchestrator import ConversationOrchestrator
from app.services.shop_service import ShopService


class DMSimulatorService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.shop_service = ShopService(db)
        self.accounts = InstagramAccountRepository(db)

    def run(self, shop_id: UUID, payload: DMSimulatorRequest, user: User) -> DMSimulatorResponse:
        self.shop_service.get_shop(shop_id, user)
        account = next((a for a in self.accounts.list_for_shop(shop_id) if a.id == payload.instagram_account_id), None)
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
            raw_payload={"_meta": {"shared_post_url": payload.shared_post_url} if payload.shared_post_url else {}},
        )
        self.db.add(message)
        self.db.flush()
        ConversationOrchestrator(self.db).process_inbound_message(conversation.id, message.id)
        self.db.refresh(conversation)
        audit = list(self.db.scalars(select(AgentDecisionAudit).where(AgentDecisionAudit.conversation_id == conversation.id).order_by(AgentDecisionAudit.created_at.desc())).all())
        latest = audit[0] if audit else None
        if latest is not None:
            trace = AgentDecisionTrace(
                conversation_id=conversation.id,
                message_id=message.id,
                intent=latest.extracted_intent,
                extracted_slots=latest.extracted_slots,
                product_candidates=latest.product_candidates,
                selected_product_id=latest.chosen_product_id,
                variant_resolution=latest.variant_resolver_result,
                inventory_result=latest.inventory_result,
                order_action={},
                next_state=latest.next_state,
                auto_send_allowed=not conversation.preview_required and not conversation.handoff_required,
                human_handoff_required=conversation.handoff_required,
                reasoning_summary=(latest.decision_reason or "Business-level simulator decision")[:500],
            )
            self.db.add(trace)
            self.db.commit()
        actions = list(self.db.scalars(select(AgentAction).where(AgentAction.conversation_id == conversation.id).order_by(AgentAction.created_at)).all())
        return DMSimulatorResponse(
            conversation_id=conversation.id,
            extracted_intent=latest.extracted_intent if latest else conversation.last_intent,
            extracted_slots=latest.extracted_slots if latest else {},
            product_resolution={"chosen_product_id": str(latest.chosen_product_id) if latest and latest.chosen_product_id else None},
            variant_resolution=latest.variant_resolver_result if latest else {},
            inventory_result=latest.inventory_result if latest else {},
            next_state=conversation.workflow_state.value,
            suggested_reply=conversation.suggested_outbound or (latest.outbound_message if latest else None),
            auto_send=not conversation.preview_required and not conversation.handoff_required,
            preview_required=conversation.preview_required,
            handoff_required=conversation.handoff_required,
            audit=[{"action": a.action_name, "input": a.input_json, "output": a.output_json} for a in actions],
        )

    def reset(self, shop_id: UUID, user: User) -> int:
        self.shop_service.get_shop(shop_id, user)
        ids = list(self.db.scalars(select(Conversation.id).where(Conversation.shop_id == shop_id, Conversation.is_simulation.is_(True))).all())
        if not ids:
            return 0
        self.db.execute(delete(Conversation).where(Conversation.id.in_(ids)))
        self.db.commit()
        return len(ids)

    def _get_or_create_customer(self, shop_id: UUID, instagram_user_id: str) -> Customer:
        customer = self.db.scalar(select(Customer).where(Customer.shop_id == shop_id, Customer.instagram_user_id == instagram_user_id))
        if customer:
            return customer
        customer = Customer(shop_id=shop_id, instagram_user_id=instagram_user_id, full_name="Simulation Customer")
        self.db.add(customer)
        self.db.flush()
        return customer

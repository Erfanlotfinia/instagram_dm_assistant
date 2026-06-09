from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import (
    AgentWorkflowState,
    ConversationPriorityLevel,
    MessageDirection,
    OrderPaymentStatus,
    OrderStatus,
)
from app.domain.models import Conversation, Message, Order
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.order_repository import OrderRepository

logger = logging.getLogger(__name__)

HIGH_VALUE_THRESHOLD = Decimal("100")
LOW_CONFIDENCE_THRESHOLD = 0.5
UNANSWERED_HOURS = 2

PRIORITY_WEIGHTS: dict[str, int] = {
    "ready_to_pay": 25,
    "payment_waiting": 30,
    "high_value_order": 15,
    "low_confidence": 20,
    "variant_mismatch": 20,
    "customer_complaint": 25,
    "human_handoff": 35,
    "vip_repeat": 10,
    "old_unanswered": 20,
    "failed_agent_run": 25,
    "order_operator_action": 20,
}


class ConversationPriorityService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.conversations = ConversationRepository(db)
        self.orders = OrderRepository(db)

    def refresh(self, conversation_id: UUID) -> Conversation | None:
        conversation = self.conversations.get_by_id(conversation_id)
        if conversation is None:
            return None
        score, reasons = self._calculate(conversation)
        conversation.priority_score = score
        conversation.priority_level = self._level_from_score(score)
        conversation.priority_reason = "; ".join(reasons) if reasons else None
        conversation.needs_attention = (
            conversation.handoff_required
            or conversation.priority_level in {
                ConversationPriorityLevel.URGENT,
                ConversationPriorityLevel.HIGH,
            }
            or score >= 40
        )
        self.db.flush()
        logger.debug(
            "Priority refreshed conversation=%s score=%s level=%s",
            conversation.id,
            score,
            conversation.priority_level.value,
        )
        return conversation

    def _calculate(self, conversation: Conversation) -> tuple[int, list[str]]:
        score = 0
        reasons: list[str] = []

        if conversation.workflow_state == AgentWorkflowState.WAITING_FOR_CONFIRMATION:
            score += PRIORITY_WEIGHTS["ready_to_pay"]
            reasons.append("Customer ready to pay")

        if conversation.workflow_state == AgentWorkflowState.WAITING_FOR_PAYMENT:
            score += PRIORITY_WEIGHTS["payment_waiting"]
            reasons.append("Payment waiting")

        active_order = self.orders.get_active_for_conversation(conversation.id)
        if active_order is not None:
            if active_order.payment_status == OrderPaymentStatus.PENDING:
                score += PRIORITY_WEIGHTS["payment_waiting"]
                if "Payment waiting" not in reasons:
                    reasons.append("Payment waiting")
            if active_order.total_amount >= HIGH_VALUE_THRESHOLD:
                score += PRIORITY_WEIGHTS["high_value_order"]
                reasons.append("High-value order")
            if active_order.status in {
                OrderStatus.DRAFT,
                OrderStatus.WAITING_FOR_CLARIFICATION,
                OrderStatus.READY_FOR_CONFIRMATION,
            }:
                score += PRIORITY_WEIGHTS["order_operator_action"]
                reasons.append("Order waiting for operator action")

        confidence = self._extract_confidence(conversation)
        if confidence is not None and confidence < LOW_CONFIDENCE_THRESHOLD:
            score += PRIORITY_WEIGHTS["low_confidence"]
            reasons.append("Low confidence")

        slots = conversation.slots
        if slots is not None:
            if slots.product_id and not slots.product_variant_id and slots.variant_alternatives:
                score += PRIORITY_WEIGHTS["variant_mismatch"]
                reasons.append("Variant mismatch")
            elif slots.product_id and slots.color and slots.size and not slots.product_variant_id:
                score += PRIORITY_WEIGHTS["variant_mismatch"]
                reasons.append("Variant mismatch")

        if conversation.last_intent in {"human_help", "cancel_order"} or (
            conversation.handoff_reason and "complaint" in conversation.handoff_reason.lower()
        ):
            score += PRIORITY_WEIGHTS["customer_complaint"]
            reasons.append("Customer complaint")

        if conversation.handoff_required:
            score += PRIORITY_WEIGHTS["human_handoff"]
            reasons.append("Human handoff required")

        paid_orders = self._count_paid_orders(conversation.customer_id)
        if paid_orders >= 2:
            score += PRIORITY_WEIGHTS["vip_repeat"]
            reasons.append("VIP/repeat customer")

        if self._has_old_unanswered_message(conversation.id):
            score += PRIORITY_WEIGHTS["old_unanswered"]
            reasons.append("Old unanswered message")

        if conversation.agent_failure_count > 0:
            score += PRIORITY_WEIGHTS["failed_agent_run"]
            reasons.append("Failed agent run")

        return min(score, 100), reasons

    @staticmethod
    def _level_from_score(score: int) -> ConversationPriorityLevel:
        if score >= 75:
            return ConversationPriorityLevel.URGENT
        if score >= 50:
            return ConversationPriorityLevel.HIGH
        if score >= 25:
            return ConversationPriorityLevel.MEDIUM
        return ConversationPriorityLevel.LOW

    @staticmethod
    def _extract_confidence(conversation: Conversation) -> float | None:
        if conversation.slots is not None and conversation.slots.confidence:
            confidence = conversation.slots.confidence
            if isinstance(confidence, dict):
                values = [
                    v for v in (confidence.get("intent"), confidence.get("slots")) if isinstance(v, (int, float))
                ]
                if values:
                    return sum(values) / len(values)
        return None

    def _count_paid_orders(self, customer_id: UUID) -> int:
        stmt = select(func.count()).select_from(Order).where(
            Order.customer_id == customer_id,
            Order.payment_status == OrderPaymentStatus.PAID,
        )
        return int(self.db.scalar(stmt) or 0)

    def _has_old_unanswered_message(self, conversation_id: UUID) -> bool:
        last_message = self.db.scalar(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        if last_message is None or last_message.direction != MessageDirection.INBOUND:
            return False
        cutoff = datetime.now(UTC) - timedelta(hours=UNANSWERED_HOURS)
        return last_message.created_at < cutoff

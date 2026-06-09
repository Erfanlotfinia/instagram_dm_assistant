from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.request_context import get_request_id
from app.domain.enums import OrderCorrectnessAction, OrderTransitionTrigger
from app.domain.models import ActionAttempt, Order, OrderStateTransition
from app.repositories.action_attempt_repository import ActionAttemptRepository
from app.repositories.order_state_transition_repository import OrderStateTransitionRepository

logger = logging.getLogger(__name__)


class OrderAuditService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.transitions = OrderStateTransitionRepository(db)
        self.attempts = ActionAttemptRepository(db)

    def record_transition(
        self,
        order: Order,
        from_status: str,
        to_status: str,
        trigger: OrderTransitionTrigger,
        *,
        actor_user_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OrderStateTransition:
        trace_id = get_request_id()
        transition = OrderStateTransition(
            shop_id=order.shop_id,
            order_id=order.id,
            from_status=from_status,
            to_status=to_status,
            trigger=trigger,
            actor_user_id=actor_user_id,
            trace_id=trace_id,
            conversation_id=order.conversation_id,
            transition_metadata=metadata,
        )
        self.transitions.create(transition)
        logger.info(
            "order_state_transition order_id=%s tenant_id=%s conversation_id=%s from=%s to=%s trace_id=%s",
            order.id,
            order.shop_id,
            order.conversation_id,
            from_status,
            to_status,
            trace_id,
        )
        return transition

    def record_action_attempt(
        self,
        order: Order,
        action: OrderCorrectnessAction,
        allowed: bool,
        *,
        denial_reasons: list[str] | None = None,
        policy_snapshot: dict[str, Any] | None = None,
    ) -> ActionAttempt:
        trace_id = get_request_id()
        attempt = ActionAttempt(
            shop_id=order.shop_id,
            order_id=order.id,
            action=action,
            allowed=allowed,
            denial_reasons=denial_reasons,
            policy_snapshot=policy_snapshot,
            trace_id=trace_id,
        )
        self.attempts.create(attempt)
        logger.info(
            "action_attempt order_id=%s tenant_id=%s action=%s allowed=%s trace_id=%s",
            order.id,
            order.shop_id,
            action.value,
            allowed,
            trace_id,
        )
        return attempt

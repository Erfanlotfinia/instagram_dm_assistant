from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.enums import OrderCorrectnessAction, OrderStatus, OrderTransitionTrigger
from app.domain.models import Order
from app.services.order_audit_service import OrderAuditService

logger = logging.getLogger(__name__)

# Maps action -> allowed (from_status, to_status) transitions
ALLOWED_TRANSITIONS: dict[OrderCorrectnessAction, dict[OrderStatus, OrderStatus]] = {
    OrderCorrectnessAction.CREATE_DRAFT: {
        OrderStatus.DRAFT: OrderStatus.DRAFT,
    },
    OrderCorrectnessAction.CLARIFY: {
        OrderStatus.DRAFT: OrderStatus.WAITING_FOR_CLARIFICATION,
        OrderStatus.READY_FOR_CONFIRMATION: OrderStatus.WAITING_FOR_CLARIFICATION,
    },
    OrderCorrectnessAction.CONFIRM: {
        OrderStatus.DRAFT: OrderStatus.READY_FOR_CONFIRMATION,
        OrderStatus.WAITING_FOR_CLARIFICATION: OrderStatus.READY_FOR_CONFIRMATION,
    },
    OrderCorrectnessAction.RESERVE: {
        OrderStatus.READY_FOR_CONFIRMATION: OrderStatus.RESERVED,
    },
    OrderCorrectnessAction.PAYMENT_LINK: {
        OrderStatus.READY_FOR_CONFIRMATION: OrderStatus.PAYMENT_PENDING,
        OrderStatus.RESERVED: OrderStatus.PAYMENT_PENDING,
    },
    OrderCorrectnessAction.MARK_PAID: {
        OrderStatus.PAYMENT_PENDING: OrderStatus.PAID,
    },
    OrderCorrectnessAction.COMPLETE: {
        OrderStatus.PAID: OrderStatus.ORDER_CREATED,
    },
    OrderCorrectnessAction.CANCEL: {
        OrderStatus.DRAFT: OrderStatus.CANCELLED,
        OrderStatus.WAITING_FOR_CLARIFICATION: OrderStatus.CANCELLED,
        OrderStatus.READY_FOR_CONFIRMATION: OrderStatus.CANCELLED,
        OrderStatus.RESERVED: OrderStatus.CANCELLED,
        OrderStatus.PAYMENT_PENDING: OrderStatus.CANCELLED,
        OrderStatus.FAILED: OrderStatus.CANCELLED,
    },
    OrderCorrectnessAction.EXPIRE: {
        OrderStatus.RESERVED: OrderStatus.EXPIRED,
        OrderStatus.PAYMENT_PENDING: OrderStatus.EXPIRED,
    },
}

FAIL_TRANSITIONS: dict[OrderStatus, OrderStatus] = {
    OrderStatus.PAYMENT_PENDING: OrderStatus.FAILED,
    OrderStatus.PAID: OrderStatus.FAILED,
}


@dataclass
class TransitionContext:
    trigger: OrderTransitionTrigger = OrderTransitionTrigger.API
    actor_user_id: UUID | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    skip_validation: bool = False


class OrderStateMachineService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = OrderAuditService(db)

    def can_transition(
        self, from_status: OrderStatus, action: OrderCorrectnessAction
    ) -> OrderStatus | None:
        mapping = ALLOWED_TRANSITIONS.get(action, {})
        return mapping.get(from_status)

    def transition(
        self,
        order: Order,
        action: OrderCorrectnessAction,
        context: TransitionContext | None = None,
    ) -> Order:
        context = context or TransitionContext()
        from_status = order.status
        if context.skip_validation:
            to_status = context.metadata.get("target_status")
            if to_status is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="target_status required")
            if isinstance(to_status, str):
                to_status = OrderStatus(to_status)
        else:
            to_status = self.can_transition(from_status, action)
            if to_status is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid transition: {from_status.value} via {action.value}",
                )
            if to_status == from_status and action != OrderCorrectnessAction.CREATE_DRAFT:
                return order

        order.status = to_status
        self.audit.record_transition(
            order,
            from_status.value,
            to_status.value,
            context.trigger,
            actor_user_id=context.actor_user_id,
            metadata=context.metadata,
        )
        return order

    def transition_to_failed(
        self,
        order: Order,
        context: TransitionContext | None = None,
    ) -> Order:
        context = context or TransitionContext()
        from_status = order.status
        to_status = FAIL_TRANSITIONS.get(from_status)
        if to_status is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot fail from status {from_status.value}",
            )
        order.status = to_status
        self.audit.record_transition(
            order,
            from_status.value,
            to_status.value,
            context.trigger,
            actor_user_id=context.actor_user_id,
            metadata=context.metadata,
        )
        return order

    def all_valid_pairs(self) -> list[tuple[OrderStatus, OrderCorrectnessAction, OrderStatus]]:
        pairs: list[tuple[OrderStatus, OrderCorrectnessAction, OrderStatus]] = []
        for action, mapping in ALLOWED_TRANSITIONS.items():
            for from_status, to_status in mapping.items():
                pairs.append((from_status, action, to_status))
        return pairs

    def all_invalid_pairs(self) -> list[tuple[OrderStatus, OrderCorrectnessAction]]:
        all_statuses = list(OrderStatus)
        invalid: list[tuple[OrderStatus, OrderCorrectnessAction]] = []
        for action in OrderCorrectnessAction:
            mapping = ALLOWED_TRANSITIONS.get(action, {})
            for from_status in all_statuses:
                if from_status not in mapping:
                    invalid.append((from_status, action))
        return invalid

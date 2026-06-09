from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import (
    OperatorReviewDecision,
    OrderCorrectnessAction,
    OrderPaymentStatus,
    OrderStatus,
    OrderTransitionTrigger,
)
from app.domain.models import Order, OrderItem, OrderItemDraft, OperatorReview, User
from app.repositories.order_item_draft_repository import OrderItemDraftRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.order_state_transition_repository import OrderStateTransitionRepository
from app.repositories.action_attempt_repository import ActionAttemptRepository
from app.repositories.operator_review_repository import OperatorReviewRepository
from app.repositories.inventory_reservation_repository import InventoryReservationRepository
from app.schemas.order_correctness import (
    OrderCancelRequest,
    OrderClarifyRequest,
    OrderConfirmRequest,
    OrderCorrectnessRead,
    OrderDraftCreateRequest,
    OrderItemDraftRead,
    OrderReserveRequest,
    OrderTimelineResponse,
    ReservationSummary,
    TimelineEntry,
)
from app.services.action_policy_service import ActionPolicyService
from app.services.compensation_service import CompensationService
from app.services.inventory_reservation_service import InventoryReservationService
from app.services.order_state_machine_service import OrderStateMachineService, TransitionContext
from app.services.payment_service import PaymentService
from app.services.shop_service import ShopService

logger = logging.getLogger(__name__)


class OrderCorrectnessService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.orders = OrderRepository(db)
        self.draft_items = OrderItemDraftRepository(db)
        self.reservations_repo = InventoryReservationRepository(db)
        self.transitions = OrderStateTransitionRepository(db)
        self.attempts = ActionAttemptRepository(db)
        self.reviews = OperatorReviewRepository(db)
        self.shop_service = ShopService(db)
        self.policy = ActionPolicyService(db)
        self.state_machine = OrderStateMachineService(db)
        self.reservations = InventoryReservationService(db)
        self.compensation = CompensationService(db, self.settings)

    def create_draft(self, payload: OrderDraftCreateRequest, user: User) -> OrderCorrectnessRead:
        shop = self.shop_service.get_shop_entity(payload.shop_id, user)
        evaluation = self.policy.evaluate(None, shop, OrderCorrectnessAction.CREATE_DRAFT, record_attempt=False)
        if not evaluation.allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=evaluation.reasons)

        if payload.idempotency_key:
            existing = self.db.scalar(
                select(Order).where(
                    Order.shop_id == payload.shop_id,
                    Order.idempotency_key == payload.idempotency_key,
                )
            )
            if existing is not None:
                return self._to_read(existing)

        subtotal = sum(
            (item.unit_price * item.quantity for item in payload.items),
            Decimal("0"),
        )
        order = Order(
            shop_id=payload.shop_id,
            customer_id=payload.customer_id,
            conversation_id=payload.conversation_id,
            status=OrderStatus.DRAFT,
            subtotal_amount=subtotal,
            total_amount=subtotal,
            currency=payload.currency,
            customer_name=payload.customer_name,
            phone=payload.phone,
            city=payload.city,
            address=payload.address,
            postal_code=payload.postal_code,
            confidence_score=payload.confidence_score,
            idempotency_key=payload.idempotency_key,
            is_simulation=payload.is_simulation,
            pilot_mode_snapshot=self.policy.build_pilot_snapshot(payload.shop_id),
        )
        self.orders.create(order)
        for item in payload.items:
            self.draft_items.create(
                OrderItemDraft(
                    shop_id=payload.shop_id,
                    order_id=order.id,
                    product_id=item.product_id,
                    product_variant_id=item.product_variant_id,
                    quantity=item.quantity,
                    product_title_snapshot=item.product_title_snapshot,
                    variant_label_snapshot=item.variant_label_snapshot,
                    unit_price=item.unit_price,
                )
            )
        self.state_machine.transition(
            order,
            OrderCorrectnessAction.CREATE_DRAFT,
            TransitionContext(trigger=OrderTransitionTrigger.API, actor_user_id=user.id),
        )
        if payload.items and all(i.product_variant_id for i in payload.items):
            self.state_machine.transition(
                order,
                OrderCorrectnessAction.CONFIRM,
                TransitionContext(trigger=OrderTransitionTrigger.SYSTEM, metadata={"auto_ready": True}),
            )
        self.orders.commit()
        return self._to_read(order)

    def clarify(self, order_id: UUID, user: User, payload: OrderClarifyRequest) -> OrderCorrectnessRead:
        order = self._get_order_for_user(order_id, user)
        shop = self.shop_service.get_shop_entity(order.shop_id, user)
        evaluation = self.policy.evaluate(order, shop, OrderCorrectnessAction.CLARIFY)
        if not evaluation.allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=evaluation.reasons)
        self.state_machine.transition(
            order,
            OrderCorrectnessAction.CLARIFY,
            TransitionContext(
                trigger=OrderTransitionTrigger.API,
                actor_user_id=user.id,
                metadata={"missing_fields": payload.missing_fields, "notes": payload.notes},
            ),
        )
        self.orders.commit()
        return self._to_read(order)

    def confirm(self, order_id: UUID, user: User, payload: OrderConfirmRequest) -> OrderCorrectnessRead:
        order = self._get_order_for_user(order_id, user)
        shop = self.shop_service.get_shop_entity(order.shop_id, user)
        evaluation = self.policy.evaluate(order, shop, OrderCorrectnessAction.CONFIRM)
        if not evaluation.allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=evaluation.reasons)

        order.customer_confirmed_at = datetime.now(UTC)
        order.customer_confirmation_source = payload.confirmation_source

        if payload.operator_decision == OperatorReviewDecision.REJECTED:
            self.reviews.create(
                OperatorReview(
                    shop_id=order.shop_id,
                    order_id=order.id,
                    reviewer_user_id=user.id,
                    decision=OperatorReviewDecision.REJECTED,
                    reason=payload.reason,
                    notes=payload.notes,
                )
            )
            self.state_machine.transition(
                order,
                OrderCorrectnessAction.CANCEL,
                TransitionContext(
                    trigger=OrderTransitionTrigger.API,
                    actor_user_id=user.id,
                    metadata={"reason": payload.reason or "rejected"},
                ),
            )
            self.reservations.release_all_for_order(order.id, reason="Operator rejected")
        else:
            if payload.operator_decision == OperatorReviewDecision.APPROVED:
                self.reviews.create(
                    OperatorReview(
                        shop_id=order.shop_id,
                        order_id=order.id,
                        reviewer_user_id=user.id,
                        decision=OperatorReviewDecision.APPROVED,
                        reason=payload.reason,
                        notes=payload.notes,
                    )
                )
            self.state_machine.transition(
                order,
                OrderCorrectnessAction.CONFIRM,
                TransitionContext(trigger=OrderTransitionTrigger.API, actor_user_id=user.id),
            )

        self.orders.commit()
        return self._to_read(order)

    def reserve(self, order_id: UUID, user: User, payload: OrderReserveRequest) -> OrderCorrectnessRead:
        order = self._get_order_for_user(order_id, user)
        shop = self.shop_service.get_shop_entity(order.shop_id, user)
        evaluation = self.policy.evaluate(order, shop, OrderCorrectnessAction.RESERVE)
        if not evaluation.allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=evaluation.reasons)

        if order.status != OrderStatus.READY_FOR_CONFIRMATION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reserve in status {order.status.value}",
            )

        draft_items = self.draft_items.list_for_order(order.id)
        if not draft_items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No draft items to reserve")

        for item in draft_items:
            if item.product_variant_id is None:
                continue
            reservation = self.reservations.reserve(
                shop_id=order.shop_id,
                order_id=order.id,
                product_variant_id=item.product_variant_id,
                quantity=item.quantity,
                ttl_seconds=payload.ttl_seconds,
            )
            order.active_reservation_id = reservation.id

        self.state_machine.transition(
            order,
            OrderCorrectnessAction.RESERVE,
            TransitionContext(trigger=OrderTransitionTrigger.API, actor_user_id=user.id),
        )
        self.orders.commit()
        return self._to_read(order)

    def payment_link(self, order_id: UUID, user: User) -> OrderCorrectnessRead:
        order = self._get_order_for_user(order_id, user)
        shop = self.shop_service.get_shop_entity(order.shop_id, user)
        evaluation = self.policy.evaluate(order, shop, OrderCorrectnessAction.PAYMENT_LINK)
        if not evaluation.allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=evaluation.reasons)

        active = self.reservations_repo.get_active_for_order(order.id)
        if not active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active reservation required for payment link",
            )

        if order.status not in {OrderStatus.READY_FOR_CONFIRMATION, OrderStatus.RESERVED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot generate payment link in status {order.status.value}",
            )

        for reservation in active:
            self.reservations.confirm_reservation(reservation.id)

        self.state_machine.transition(
            order,
            OrderCorrectnessAction.PAYMENT_LINK,
            TransitionContext(trigger=OrderTransitionTrigger.API, actor_user_id=user.id),
        )
        order.payment_status = OrderPaymentStatus.PENDING
        order.expires_at = datetime.now(UTC) + timedelta(minutes=self.settings.order_expiration_minutes)
        PaymentService(self.db, self.settings).initiate_payment(order)
        self.orders.commit()
        return self._to_read(order)

    def complete(self, order_id: UUID, user: User) -> OrderCorrectnessRead:
        order = self._get_order_for_user(order_id, user)
        shop = self.shop_service.get_shop_entity(order.shop_id, user)
        evaluation = self.policy.evaluate(order, shop, OrderCorrectnessAction.COMPLETE)
        if not evaluation.allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=evaluation.reasons)

        if order.customer_confirmed_at is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Customer confirmation required")

        confirmed_reservations = [
            r for r in order.inventory_reservations
            if r.status.value in ("confirmed", "active")
        ]
        if not confirmed_reservations and not order.items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reservation required")

        try:
            self._copy_draft_to_items(order)
            self.state_machine.transition(
                order,
                OrderCorrectnessAction.COMPLETE,
                TransitionContext(trigger=OrderTransitionTrigger.API, actor_user_id=user.id),
            )
        except Exception as exc:
            self.compensation.handle_order_creation_failed(order, str(exc))
            self.orders.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Order creation failed; compensation initiated",
            ) from exc

        self.orders.commit()
        return self._to_read(order)

    def cancel(self, order_id: UUID, user: User, payload: OrderCancelRequest) -> OrderCorrectnessRead:
        order = self._get_order_for_user(order_id, user)
        shop = self.shop_service.get_shop_entity(order.shop_id, user)
        evaluation = self.policy.evaluate(order, shop, OrderCorrectnessAction.CANCEL)
        if not evaluation.allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=evaluation.reasons)

        self.reservations.release_all_for_order(order.id, reason=payload.reason or "Cancelled")
        self.state_machine.transition(
            order,
            OrderCorrectnessAction.CANCEL,
            TransitionContext(
                trigger=OrderTransitionTrigger.API,
                actor_user_id=user.id,
                metadata={"reason": payload.reason},
            ),
        )
        if payload.reason:
            order.notes = payload.reason
        self.orders.commit()
        return self._to_read(order)

    def get_order(self, order_id: UUID, user: User) -> OrderCorrectnessRead:
        order = self._get_order_for_user(order_id, user)
        return self._to_read(order)

    def get_timeline(self, order_id: UUID, user: User) -> OrderTimelineResponse:
        order = self._get_order_for_user(order_id, user)
        entries: list[TimelineEntry] = []

        for t in self.transitions.list_for_order(order.shop_id, order.id):
            entries.append(
                TimelineEntry(
                    entry_type="state_transition",
                    occurred_at=t.created_at,
                    label=f"{t.from_status} → {t.to_status}",
                    status=t.to_status,
                    metadata=t.transition_metadata,
                )
            )
        for a in self.attempts.list_for_order(order.shop_id, order.id):
            entries.append(
                TimelineEntry(
                    entry_type="action_attempt",
                    occurred_at=a.created_at,
                    label=f"Action {a.action.value}: {'allowed' if a.allowed else 'denied'}",
                    status=a.action.value,
                    metadata={"allowed": a.allowed, "denial_reasons": a.denial_reasons},
                )
            )
        for r in self.reviews.list_for_order(order.shop_id, order.id):
            entries.append(
                TimelineEntry(
                    entry_type="operator_review",
                    occurred_at=r.created_at,
                    label=f"Operator {r.decision.value}",
                    status=r.decision.value,
                    metadata={"reason": r.reason},
                )
            )
        entries.sort(key=lambda e: e.occurred_at)
        return OrderTimelineResponse(order_id=order.id, entries=entries)

    def _get_order_for_user(self, order_id: UUID, user: User) -> Order:
        from app.core.request_context import set_order_context

        order = self.orders.get_by_id(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        self.shop_service.get_shop(order.shop_id, user)
        set_order_context(str(order.shop_id), str(order.id), str(order.conversation_id))
        return order

    def _copy_draft_to_items(self, order: Order) -> None:
        if order.items:
            return
        for draft in self.draft_items.list_for_order(order.id):
            unit_price = Decimal(str(draft.unit_price))
            total = unit_price * draft.quantity
            self.db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=draft.product_id,
                    product_variant_id=draft.product_variant_id,
                    product_title_snapshot=draft.product_title_snapshot,
                    variant_color_snapshot=draft.variant_label_snapshot,
                    variant_size_snapshot=None,
                    sku_snapshot="",
                    quantity=draft.quantity,
                    unit_price=unit_price,
                    total_price=total,
                )
            )

    def _to_read(self, order: Order) -> OrderCorrectnessRead:
        draft_items = [OrderItemDraftRead.model_validate(i) for i in self.draft_items.list_for_order(order.id)]
        reservations = [
            ReservationSummary.model_validate(r)
            for r in self.reservations_repo.list_for_order(order.id)
        ]
        return OrderCorrectnessRead(
            id=order.id,
            shop_id=order.shop_id,
            customer_id=order.customer_id,
            conversation_id=order.conversation_id,
            status=order.status,
            subtotal_amount=order.subtotal_amount,
            total_amount=order.total_amount,
            currency=order.currency,
            payment_status=order.payment_status.value,
            shipping_status=order.shipping_status.value,
            customer_name=order.customer_name,
            phone=order.phone,
            city=order.city,
            address=order.address,
            postal_code=order.postal_code,
            expires_at=order.expires_at,
            customer_confirmed_at=order.customer_confirmed_at,
            customer_confirmation_source=order.customer_confirmation_source,
            confidence_score=order.confidence_score,
            pilot_mode_snapshot=order.pilot_mode_snapshot,
            active_reservation_id=order.active_reservation_id,
            draft_items=draft_items,
            reservations=reservations,
            is_simulation=order.is_simulation,
        )

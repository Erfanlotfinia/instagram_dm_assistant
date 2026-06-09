from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import OrderCorrectnessAction, OrderStatus, OrderTransitionTrigger
from app.domain.models import Order
from app.integrations.rabbitmq import MessagePublisher, RabbitMQPublisher
from app.services.inventory_reservation_service import InventoryReservationService
from app.services.order_state_machine_service import OrderStateMachineService, TransitionContext

logger = logging.getLogger(__name__)


class CompensationService:
    def __init__(
        self,
        db: Session,
        settings: Settings | None = None,
        publisher: MessagePublisher | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.publisher = publisher or RabbitMQPublisher(self.settings)
        self.state_machine = OrderStateMachineService(db)
        self.reservations = InventoryReservationService(db)

    def handle_payment_failed(self, order: Order, reason: str | None = None) -> Order:
        from app.domain.enums import OrderPaymentStatus

        self.reservations.release_all_for_order(order.id, reason=reason or "Payment failed")
        order.payment_status = OrderPaymentStatus.FAILED
        if order.status == OrderStatus.PAYMENT_PENDING:
            self.state_machine.transition_to_failed(
                order,
                TransitionContext(
                    trigger=OrderTransitionTrigger.WEBHOOK,
                    metadata={"reason": reason or "payment_failed"},
                ),
            )
        return order

    def enqueue_compensation(self, order_id: UUID, shop_id: UUID, details: dict[str, Any]) -> None:
        payload = {
            "order_id": str(order_id),
            "shop_id": str(shop_id),
            "details": details,
        }
        self.publisher.publish(self.settings.rabbitmq_queue_order_compensation, payload)
        logger.warning("compensation_enqueued order_id=%s shop_id=%s", order_id, shop_id)

    def enqueue_operator_alert(self, shop_id: UUID, title: str, details: dict[str, Any]) -> None:
        payload = {
            "shop_id": str(shop_id),
            "title": title,
            "details": details,
        }
        self.publisher.publish(self.settings.rabbitmq_queue_operator_alerts, payload)
        logger.warning("operator_alert_enqueued shop_id=%s title=%s", shop_id, title)

    def handle_order_creation_failed(self, order: Order, error: str) -> Order:
        self.enqueue_compensation(
            order.id,
            order.shop_id,
            {"error": error, "status": order.status.value},
        )
        self.enqueue_operator_alert(
            order.shop_id,
            "Order creation failed after payment",
            {"order_id": str(order.id), "error": error},
        )
        if order.status == OrderStatus.PAID:
            self.state_machine.transition_to_failed(
                order,
                TransitionContext(
                    trigger=OrderTransitionTrigger.SYSTEM,
                    metadata={"error": error},
                ),
            )
        return order

    def process_compensation_job(self, payload: dict[str, Any]) -> None:
        order_id = UUID(payload["order_id"])
        from app.repositories.order_repository import OrderRepository

        order = OrderRepository(self.db).get_by_id(order_id)
        if order is None:
            return
        self.reservations.release_all_for_order(order.id, reason="Compensation release")
        if order.status == OrderStatus.FAILED:
            self.state_machine.transition(
                order,
                OrderCorrectnessAction.CANCEL,
                TransitionContext(trigger=OrderTransitionTrigger.WORKER, metadata={"compensation": True}),
            )
        self.db.commit()

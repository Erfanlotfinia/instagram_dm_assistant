from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import OrderCorrectnessAction, OrderStatus, OrderTransitionTrigger
from app.services.compensation_service import CompensationService
from app.services.inventory_reservation_service import InventoryReservationService
from app.services.order_state_machine_service import OrderStateMachineService, TransitionContext
from app.repositories.inventory_reservation_repository import InventoryReservationRepository
from app.repositories.order_repository import OrderRepository

logger = logging.getLogger(__name__)


def handle_reservation_expiry(db: Session, payload: dict[str, Any], settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    reservation_id = UUID(payload["reservation_id"])
    reservations = InventoryReservationService(db)
    state_machine = OrderStateMachineService(db)
    orders = OrderRepository(db)

    reservation = reservations.reservations.get_by_id(reservation_id)
    if reservation is None:
        return
    reservations.expire_reservation(reservation_id)
    order = orders.get_by_id(reservation.order_id)
    if order is not None and order.status == OrderStatus.RESERVED:
        state_machine.transition(
            order,
            OrderCorrectnessAction.EXPIRE,
            TransitionContext(trigger=OrderTransitionTrigger.WORKER),
        )
    db.commit()


def handle_payment_callback(db: Session, payload: dict[str, Any], settings: Settings | None = None) -> None:
    from app.domain.enums import PaymentRecordStatus
    from app.services.payment_service import PaymentService

    payment_id = UUID(payload["payment_id"])
    callback_status = PaymentRecordStatus(payload.get("status", "paid"))
    PaymentService(db, settings).handle_mock_callback(
        payment_id,
        callback_status,
        provider_reference=payload.get("provider_reference"),
        raw_payload=payload.get("raw_payload"),
    )
    db.commit()


def handle_compensation(db: Session, payload: dict[str, Any], settings: Settings | None = None) -> None:
    CompensationService(db, settings).process_compensation_job(payload)


def handle_operator_alert(db: Session, payload: dict[str, Any], settings: Settings | None = None) -> None:
    from app.domain.enums import PilotEventSeverity
    from app.services.pilot_service import PilotService

    shop_id = UUID(payload["shop_id"])
    title = payload.get("title", "Operator alert")
    details = payload.get("details", {})
    PilotService(db).log_event(
        shop_id,
        "operator_alert",
        PilotEventSeverity.CRITICAL,
        title,
        description=json.dumps(details),
        metadata=details,
    )
    db.commit()


def publish_expired_reservations(db: Session, settings: Settings | None = None) -> int:
    from app.integrations.rabbitmq import RabbitMQPublisher

    settings = settings or get_settings()
    publisher = RabbitMQPublisher(settings)
    repo = InventoryReservationRepository(db)
    expired = repo.list_expired_active(datetime.now(UTC))
    for reservation in expired:
        publisher.publish(
            settings.rabbitmq_queue_reservation_expiry,
            {"reservation_id": str(reservation.id)},
        )
    publisher.close()
    return len(expired)

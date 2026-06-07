from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import (
    OrderPaymentStatus,
    OrderStatus,
    PaymentProvider,
    PaymentRecordStatus,
)
from app.domain.models import Order, Payment, User
from app.repositories.payment_repository import PaymentRepository
from app.services.order_service import OrderService
from app.services.payment_providers import get_payment_provider

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.payments = PaymentRepository(db)
        self.order_service = OrderService(db, settings=self.settings)

    def initiate_payment(
        self,
        order: Order,
        provider: PaymentProvider = PaymentProvider.MOCK,
    ) -> Payment:
        payment_provider = get_payment_provider(self.db, provider)
        payment = payment_provider.create_payment(order)
        order.payment_status = OrderPaymentStatus.PENDING
        self.payments.commit()
        logger.info("Payment initiated order=%s payment=%s provider=%s", order.id, payment.id, provider.value)
        return payment

    def handle_mock_callback(
        self,
        payment_id: UUID,
        callback_status: PaymentRecordStatus,
        provider_reference: str | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> Order:
        payment = self.payments.get_by_id(payment_id)
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        if payment.provider != PaymentProvider.MOCK:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a mock payment")

        payment.raw_payload = raw_payload or {}
        if provider_reference:
            payment.provider_reference = provider_reference

        if callback_status == PaymentRecordStatus.PAID:
            if payment.status == PaymentRecordStatus.PAID:
                order = self.order_service.get_order_internal(payment.order_id)
                if order is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
                logger.info("Duplicate payment callback ignored payment=%s", payment.id)
                return order
            if provider_reference:
                existing = self.payments.get_by_provider_reference(provider_reference)
                if existing is not None and existing.id != payment.id:
                    logger.info("Duplicate provider_reference=%s ignored", provider_reference)
                    order = self.order_service.get_order_internal(existing.order_id)
                    if order is None:
                        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
                    return order
            payment.status = PaymentRecordStatus.PAID
            order = self.order_service.mark_paid_internal(payment.order_id, payment=payment)
            from app.core.metrics import PAID_ORDERS

            PAID_ORDERS.inc()
            self.payments.commit()
            logger.info("Mock payment callback paid order=%s payment=%s", order.id, payment.id)
            return order

        if callback_status in {PaymentRecordStatus.FAILED, PaymentRecordStatus.CANCELLED}:
            payment.status = callback_status
            order = self.order_service.get_order_internal(payment.order_id)
            if order:
                order.payment_status = OrderPaymentStatus.FAILED
            self.payments.commit()
            logger.info(
                "Mock payment callback failed order=%s payment=%s status=%s",
                payment.order_id,
                payment.id,
                callback_status.value,
            )
            return order

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported callback status")

    def mark_paid_manually(self, shop_id: UUID, order_id: UUID, user: User) -> Order:
        order = self.order_service.get_order_for_shop(shop_id, order_id, user)
        if order.status not in {OrderStatus.WAITING_FOR_PAYMENT, OrderStatus.CONFIRMED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot mark paid from status {order.status.value}",
            )

        payment = Payment(
            order_id=order.id,
            provider=PaymentProvider.MANUAL,
            status=PaymentRecordStatus.PAID,
            provider_reference=f"manual-{datetime.now(UTC).isoformat()}",
        )
        self.payments.create(payment)
        order = self.order_service.mark_paid_internal(order.id, payment=payment, user=user)
        from app.core.metrics import PAID_ORDERS
        from app.services.audit_service import AuditService

        PAID_ORDERS.inc()
        AuditService(self.db).log(
            action="mark_paid",
            entity_type="order",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(order.id),
            metadata={"payment_id": str(payment.id), "provider": "manual"},
        )
        self.payments.commit()
        return order

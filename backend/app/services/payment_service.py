from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import (
    ConversationEventType,
    InventoryReservationStatus,
    OrderPaymentStatus,
    OrderStatus,
    PaymentProvider,
    PaymentRecordStatus,
    PilotEventSeverity,
    UserRole,
)
from app.domain.models import Order, Payment, User
from app.repositories.payment_repository import PaymentRepository
from app.services.audit_service import AuditService
from app.services.conversation_event_service import ConversationEventService
from app.services.conversation_priority_service import ConversationPriorityService
from app.services.channel_outbound_service import ChannelOutboundService
from app.services.order_service import OrderService
from app.services.payment_providers import get_payment_provider
from app.services.pilot_service import PilotService
from app.services.shop_service import ShopService
from app.services.state_transition_service import PAYMENT_STATE_MACHINE

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.payments = PaymentRepository(db)
        self.order_service = OrderService(db, settings=self.settings)
        self.shop_service = ShopService(db)

    def initiate_payment(
        self,
        order: Order,
        provider: PaymentProvider = PaymentProvider.MOCK,
    ) -> Payment:
        payment_provider = get_payment_provider(self.db, provider)
        payment = payment_provider.create_payment(order)
        PAYMENT_STATE_MACHINE.transition(payment, PaymentRecordStatus.PENDING)
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
            PAYMENT_STATE_MACHINE.transition(payment, PaymentRecordStatus.PAID)
            payment.callback_processed_at = datetime.now(UTC)
            order = self.order_service.mark_paid_internal(payment.order_id, payment=payment)
            from app.core.metrics import PAID_ORDERS

            PAID_ORDERS.inc()
            self.payments.commit()
            logger.info("Mock payment callback paid order=%s payment=%s", order.id, payment.id)
            return order

        if callback_status in {PaymentRecordStatus.FAILED, PaymentRecordStatus.CANCELLED}:
            PAYMENT_STATE_MACHINE.transition(payment, callback_status)
            payment.callback_processed_at = datetime.now(UTC)
            order = self.order_service.get_order_internal(payment.order_id)
            if order:
                from app.services.compensation_service import CompensationService

                CompensationService(self.db, self.settings).handle_payment_failed(
                    order, reason=f"payment_{callback_status.value}"
                )
                PilotService(self.db).log_event(
                    order.shop_id,
                    "payment_callback_error",
                    PilotEventSeverity.ERROR,
                    "Payment callback failed",
                    description=f"Payment callback status {callback_status.value}",
                    metadata={"payment_id": str(payment.id), "order_id": str(order.id)},
                )
            self.payments.commit()
            logger.info(
                "Mock payment callback failed order=%s payment=%s status=%s",
                payment.order_id,
                payment.id,
                callback_status.value,
            )
            return order or Order()

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported callback status")

    def send_payment_link(
        self,
        shop_id: UUID,
        order_id: UUID,
        user: User,
        *,
        admin_override_reason: str | None = None,
    ) -> Order:
        order = self.order_service.get_order_for_shop(shop_id, order_id, user)
        if order.status == OrderStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order must be confirmed before sending payment link",
            )

        if order.customer_confirmed_at is None:
            if not admin_override_reason:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Customer confirmation is required before sending payment link",
                )
            self._require_admin_override(shop_id, user)
            order.admin_override_reason = admin_override_reason
            AuditService(self.db).log(
                action="payment_link_admin_override",
                entity_type="order",
                shop_id=shop_id,
                actor_user_id=user.id,
                entity_id=str(order.id),
                metadata={"reason": admin_override_reason},
            )

        if order.status != OrderStatus.PAYMENT_PENDING:
            if order.status in {OrderStatus.READY_FOR_CONFIRMATION, OrderStatus.RESERVED}:
                self.order_service._confirm_for_payment(order)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot send payment link for order in status {order.status.value}",
                )

        pending = next(
            (
                p
                for p in order.payments
                if p.status in {PaymentRecordStatus.CREATED, PaymentRecordStatus.PENDING}
            ),
            None,
        )
        payment = pending or self.initiate_payment(order)
        if order.conversation_id and payment.payment_url:
            message_text = f"لینک پرداخت سفارش شما:\n{payment.payment_url}"
            ChannelOutboundService(self.db).send_text_message(order.conversation_id, message_text)
            ConversationEventService(self.db).record(
                order.conversation_id,
                ConversationEventType.PAYMENT_LINK_SENT,
                metadata={"order_id": str(order.id), "payment_id": str(payment.id)},
                created_by_user_id=user.id,
            )
            ConversationPriorityService(self.db).refresh(order.conversation_id)

        AuditService(self.db).log(
            action="payment_link_sent",
            entity_type="order",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(order.id),
            metadata={"payment_id": str(payment.id), "payment_url": payment.payment_url},
        )
        self.payments.commit()
        return order

    def mark_paid_manually(self, shop_id: UUID, order_id: UUID, user: User) -> Order:
        self._require_admin_override(shop_id, user)
        order = self.order_service.get_order_for_shop(shop_id, order_id, user)

        if order.status == OrderStatus.READY_FOR_CONFIRMATION:
            if order.customer_confirmed_at is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Customer confirmation is required before manual payment",
                )
            self.order_service._confirm_for_payment(order)
            self.payments.commit()
            order = self.order_service.get_order_for_shop(shop_id, order_id, user)

        if order.status != OrderStatus.PAYMENT_PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot mark paid from status {order.status.value}",
            )

        from app.services.inventory_reservation_service import InventoryReservationService

        reservations = InventoryReservationService(self.db).reservations.list_for_order(order.id)
        active = [
            r
            for r in reservations
            if r.status in {InventoryReservationStatus.ACTIVE, InventoryReservationStatus.CONFIRMED}
        ]
        if not active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active inventory reservation is required before marking paid",
            )

        idempotency_ref = f"manual-{order.id}"
        existing = self.payments.get_by_provider_reference(idempotency_ref)
        if existing is not None and existing.status == PaymentRecordStatus.PAID:
            return self.order_service.get_order_internal(order.id) or order

        payment = Payment(
            order_id=order.id,
            provider=PaymentProvider.MANUAL,
            status=PaymentRecordStatus.PAID,
            provider_reference=idempotency_ref,
        )
        self.payments.create(payment)
        order = self.order_service.mark_paid_internal(order.id, payment=payment, user=user)
        from app.core.metrics import PAID_ORDERS

        PAID_ORDERS.inc()
        if order.conversation_id:
            ConversationEventService(self.db).record(
                order.conversation_id,
                ConversationEventType.PAYMENT_RECEIVED,
                metadata={"order_id": str(order.id), "payment_id": str(payment.id)},
                created_by_user_id=user.id,
            )
            ConversationPriorityService(self.db).refresh(order.conversation_id)
        AuditService(self.db).log(
            action="manual_payment_confirmed",
            entity_type="order",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(order.id),
            metadata={"payment_id": str(payment.id), "provider": "manual"},
        )
        self.payments.commit()
        return order

    def _require_admin_override(self, shop_id: UUID, user: User) -> None:
        membership = self.shop_service.get_membership(shop_id, user.id)
        if membership is None or membership.role not in {UserRole.OWNER, UserRole.ADMIN}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires admin role or higher")

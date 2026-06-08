from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import (
    AgentWorkflowState,
    InventoryMovementType,
    OrderPaymentStatus,
    OrderRecoveryStatus,
    OrderShippingStatus,
    OrderStatus,
)
from app.domain.models import (
    AdminAuditLog,
    Conversation,
    ConversationSlots,
    InventoryMovement,
    Order,
    OrderItem,
    Payment,
    Product,
    ProductVariant,
    User,
)
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.order import OrderCancelRequest, OrderListFilters, OrderRead, OrderTimelineEvent
from app.services.shop_service import ShopService
from app.services.slot_merge_service import compute_missing_fields

logger = logging.getLogger(__name__)

ACTIVE_ORDER_STATUSES = {
    OrderStatus.DRAFT,
    OrderStatus.WAITING_FOR_CONFIRMATION,
    OrderStatus.CONFIRMED,
    OrderStatus.WAITING_FOR_PAYMENT,
}


class OrderService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.orders = OrderRepository(db)
        self.variants = VariantRepository(db)
        self.inventory = InventoryRepository(db)
        self.audit_logs = AuditLogRepository(db)
        self.shop_service = ShopService(db)

    @staticmethod
    def can_create_draft(slots: ConversationSlots, variant: ProductVariant | None) -> bool:
        if slots.product_id is None or slots.product_variant_id is None or variant is None:
            return False
        quantity = slots.quantity or 0
        if quantity < 1:
            return False
        customer_missing = compute_missing_fields(slots, require_variant=False)
        customer_missing = [
            field
            for field in customer_missing
            if field not in ("product", "color", "size", "quantity", "stock")
        ]
        return len(customer_missing) == 0

    def list_orders(self, shop_id: UUID, user: User, filters: OrderListFilters) -> list[OrderRead]:
        self.shop_service.get_shop(shop_id, user)
        orders = self.orders.list_for_shop(
            shop_id,
            status=filters.status,
            payment_status=filters.payment_status,
            shipping_status=filters.shipping_status,
            created_from=filters.created_from,
            created_to=filters.created_to,
        )
        return [self._to_read(order) for order in orders]

    def get_order_for_shop(self, shop_id: UUID, order_id: UUID, user: User) -> Order:
        self.shop_service.get_shop(shop_id, user)
        order = self.orders.get_for_shop(shop_id, order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return order

    def get_order_read(self, shop_id: UUID, order_id: UUID, user: User) -> OrderRead:
        order = self.get_order_for_shop(shop_id, order_id, user)
        return self._to_read(order)

    def get_order_internal(self, order_id: UUID) -> Order | None:
        return self.orders.get_by_id(order_id)

    def upsert_draft_from_conversation(
        self,
        conversation: Conversation,
        slots: ConversationSlots,
        product: Product,
        variant: ProductVariant,
    ) -> Order | None:
        if not self.can_create_draft(slots, variant):
            return None

        quantity = slots.quantity or 1
        unit_price = Decimal(str(variant.price))
        subtotal = unit_price * quantity

        existing = self.orders.get_active_for_conversation(conversation.id)
        if existing is not None and existing.status not in {
            OrderStatus.DRAFT,
            OrderStatus.WAITING_FOR_CONFIRMATION,
        }:
            return existing

        if existing is None:
            order = Order(
                shop_id=conversation.shop_id,
                customer_id=conversation.customer_id,
                conversation_id=conversation.id,
                status=OrderStatus.WAITING_FOR_CONFIRMATION,
                subtotal_amount=subtotal,
                total_amount=subtotal,
                currency=product.currency,
                customer_name=slots.customer_name or "",
                phone=slots.phone or "",
                city=slots.city or "",
                address=slots.address or "",
                postal_code=slots.postal_code or "",
            )
            self.orders.create(order)
        else:
            order = existing
            order.status = OrderStatus.WAITING_FOR_CONFIRMATION
            order.subtotal_amount = subtotal
            order.total_amount = subtotal
            order.currency = product.currency
            order.customer_name = slots.customer_name or ""
            order.phone = slots.phone or ""
            order.city = slots.city or ""
            order.address = slots.address or ""
            order.postal_code = slots.postal_code or ""
            order.items.clear()

        order.items.append(
            OrderItem(
                product_id=product.id,
                product_variant_id=variant.id,
                product_title_snapshot=product.title,
                variant_color_snapshot=variant.color,
                variant_size_snapshot=variant.size,
                sku_snapshot=variant.sku,
                quantity=quantity,
                unit_price=unit_price,
                total_price=subtotal,
            )
        )
        self.orders.commit()
        logger.info("Draft order upserted order=%s conversation=%s", order.id, conversation.id)
        return order

    def confirm_order(
        self,
        shop_id: UUID,
        order_id: UUID,
        user: User,
    ) -> OrderRead:
        order = self.get_order_for_shop(shop_id, order_id, user)
        confirmed = self._confirm_for_payment(order)
        self.audit(
            shop_id=shop_id,
            user_id=user.id,
            action="confirm_order",
            entity_type="order",
            entity_id=str(order.id),
            details={"status": confirmed.status.value},
        )
        self.orders.commit()
        return self._to_read(confirmed)

    def confirm_after_customer(self, order: Order) -> Order:
        if order.status != OrderStatus.WAITING_FOR_CONFIRMATION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot confirm order in status {order.status.value}",
            )
        return self._confirm_for_payment(order)

    def _confirm_for_payment(self, order: Order) -> Order:
        if order.status == OrderStatus.WAITING_FOR_PAYMENT:
            logger.info("Order already confirmed for payment order=%s (idempotent)", order.id)
            return order
        if order.status not in {
            OrderStatus.WAITING_FOR_CONFIRMATION,
            OrderStatus.DRAFT,
            OrderStatus.CONFIRMED,
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot confirm order in status {order.status.value}",
            )

        for item in order.items:
            if item.product_variant_id is None:
                continue
            self._reserve_inventory(
                variant_id=item.product_variant_id,
                quantity=item.quantity,
                order_id=order.id,
            )

        order.status = OrderStatus.WAITING_FOR_PAYMENT
        order.payment_status = OrderPaymentStatus.PENDING
        order.expires_at = datetime.now(UTC) + timedelta(minutes=self.settings.order_expiration_minutes)
        order.recovery_status = OrderRecoveryStatus.NONE
        order.recovery_attempt_count = 0
        order.last_recovery_at = None
        self.orders.commit()
        logger.info("Order confirmed for payment order=%s expires_at=%s", order.id, order.expires_at)
        return order

    def cancel_order(
        self,
        shop_id: UUID,
        order_id: UUID,
        user: User,
        payload: OrderCancelRequest | None = None,
    ) -> OrderRead:
        order = self.get_order_for_shop(shop_id, order_id, user)
        reason = payload.reason if payload else None
        cancelled = self._cancel_order_internal(order, reason=reason)
        self.audit(
            shop_id=shop_id,
            user_id=user.id,
            action="cancel_order",
            entity_type="order",
            entity_id=str(order.id),
            details={"reason": reason},
        )
        if cancelled.conversation_id:
            from app.domain.enums import ConversationEventType
            from app.services.conversation_event_service import ConversationEventService
            from app.services.conversation_priority_service import ConversationPriorityService

            ConversationEventService(self.db).record(
                cancelled.conversation_id,
                ConversationEventType.ORDER_CANCELLED,
                metadata={"order_id": str(cancelled.id), "reason": reason},
                created_by_user_id=user.id,
            )
            ConversationPriorityService(self.db).refresh(cancelled.conversation_id)
        self.orders.commit()
        return self._to_read(cancelled)

    def cancel_active_for_conversation(self, conversation_id: UUID, reason: str | None = None) -> Order | None:
        order = self.orders.get_active_for_conversation(conversation_id)
        if order is None:
            return None
        return self._cancel_order_internal(order, reason=reason)

    def _cancel_order_internal(self, order: Order, reason: str | None = None) -> Order:
        if order.status in {OrderStatus.CANCELLED, OrderStatus.EXPIRED, OrderStatus.COMPLETED}:
            return order

        if order.status == OrderStatus.WAITING_FOR_PAYMENT:
            self._release_order_inventory(order, reason=reason or "Order cancelled")

        order.status = OrderStatus.CANCELLED
        order.payment_status = (
            OrderPaymentStatus.UNPAID
            if order.payment_status == OrderPaymentStatus.PENDING
            else order.payment_status
        )
        order.expires_at = None
        from app.services.order_recovery_service import OrderRecoveryService

        OrderRecoveryService(self.db, settings=self.settings).on_order_terminal(order)
        if reason:
            order.notes = reason
        self.orders.commit()
        logger.info("Order cancelled order=%s reason=%s", order.id, reason)
        return order

    def expire_order(self, order: Order) -> Order:
        if order.status != OrderStatus.WAITING_FOR_PAYMENT:
            return order
        self._release_order_inventory(order, reason="Order expired")
        order.status = OrderStatus.EXPIRED
        order.payment_status = OrderPaymentStatus.UNPAID
        order.expires_at = None
        from app.services.order_recovery_service import OrderRecoveryService

        OrderRecoveryService(self.db, settings=self.settings).on_order_terminal(order)
        self.orders.commit()
        logger.info("Order expired order=%s", order.id)
        return order

    def mark_paid_internal(
        self,
        order_id: UUID,
        *,
        payment: Payment | None = None,
        user: User | None = None,
    ) -> Order:
        order = self.orders.get_by_id(order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.status == OrderStatus.PAID and order.payment_status == OrderPaymentStatus.PAID:
            logger.info("Duplicate mark paid ignored order=%s", order.id)
            return order
        if order.status not in {OrderStatus.WAITING_FOR_PAYMENT, OrderStatus.CONFIRMED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot mark paid from status {order.status.value}",
            )

        order.status = OrderStatus.PAID
        order.payment_status = OrderPaymentStatus.PAID
        order.expires_at = None
        order.shipping_status = OrderShippingStatus.PREPARING
        from app.services.customer_preferences_service import CustomerPreferencesService
        from app.services.order_recovery_service import OrderRecoveryService

        CustomerPreferencesService(self.db).update_from_paid_order(order)
        OrderRecoveryService(self.db, settings=self.settings).on_order_paid(order)
        self.orders.commit()
        order.payment_callback_status = payment.status.value if payment else "manual_paid"
        logger.info("Order marked paid order=%s payment=%s", order.id, payment.id if payment else None)
        return order

    def audit(
        self,
        *,
        shop_id: UUID,
        user_id: UUID | None,
        action: str,
        entity_type: str,
        entity_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.audit_logs.create(
            AdminAuditLog(
                shop_id=shop_id,
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details or {},
            )
        )

    def _reserve_inventory(self, variant_id: UUID, quantity: int, order_id: UUID) -> None:
        locked = self.variants.get_for_update(variant_id)
        if locked is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")

        available = locked.stock_quantity - locked.reserved_quantity
        if quantity > available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient available stock: {available} available, {quantity} requested",
            )

        existing = self.db.scalar(select(InventoryMovement).where(InventoryMovement.product_variant_id == variant_id, InventoryMovement.movement_type == InventoryMovementType.RESERVE, InventoryMovement.reference_type == "order", InventoryMovement.reference_id == str(order_id)))
        if existing is not None:
            logger.info("Duplicate inventory reservation ignored order=%s variant=%s", order_id, variant_id)
            return
        locked.reserved_quantity += quantity
        movement = InventoryMovement(
            product_variant_id=locked.id,
            movement_type=InventoryMovementType.RESERVE,
            quantity=quantity,
            reason="Order confirmed for payment",
            reference_type="order",
            reference_id=str(order_id),
        )
        self.inventory.create(movement)

    def _release_order_inventory(self, order: Order, reason: str) -> None:
        for item in order.items:
            if item.product_variant_id is None:
                continue
            locked = self.variants.get_for_update(item.product_variant_id)
            if locked is None:
                continue
            release_qty = min(item.quantity, locked.reserved_quantity)
            if release_qty <= 0:
                continue
            locked.reserved_quantity -= release_qty
            movement = InventoryMovement(
                product_variant_id=locked.id,
                movement_type=InventoryMovementType.RELEASE,
                quantity=release_qty,
                reason=reason,
                reference_type="order",
                reference_id=str(order.id),
            )
            self.inventory.create(movement)

    def _to_read(self, order: Order) -> OrderRead:
        data = OrderRead.model_validate(order)
        data.timeline = self.build_timeline(order)
        return data

    def build_timeline(self, order: Order) -> list[OrderTimelineEvent]:
        events: list[OrderTimelineEvent] = [
            OrderTimelineEvent(
                status="created",
                label="Order created",
                occurred_at=order.created_at,
                source="system",
            ),
        ]
        if order.status != OrderStatus.DRAFT:
            events.append(
                OrderTimelineEvent(
                    status=order.status.value,
                    label=f"Status: {order.status.value}",
                    occurred_at=order.updated_at,
                    source="system",
                )
            )
        for payment in order.payments:
            events.append(
                OrderTimelineEvent(
                    status=f"payment_{payment.status.value}",
                    label=f"Payment {payment.status.value} ({payment.provider.value})",
                    occurred_at=payment.created_at,
                    source="payment",
                )
            )
        for shipment in order.shipments:
            occurred = shipment.shipped_at or shipment.created_at
            events.append(
                OrderTimelineEvent(
                    status=f"shipment_{shipment.status.value}",
                    label=f"Shipment {shipment.status.value}",
                    occurred_at=occurred,
                    source="shipping",
                )
            )
        audit_entries = self.audit_logs.list_for_entity(order.shop_id, "order", str(order.id))
        for entry in audit_entries:
            events.append(
                OrderTimelineEvent(
                    status=entry.action,
                    label=f"Admin: {entry.action}",
                    occurred_at=entry.created_at,
                    source="admin",
                )
            )
        events.sort(key=lambda event: event.occurred_at)
        return events

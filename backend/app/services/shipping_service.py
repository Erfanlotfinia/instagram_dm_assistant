from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.enums import (
    ConversationEventType,
    OrderShippingStatus,
    OrderStatus,
    ShipmentProvider,
    ShipmentStatus,
)
from app.domain.models import Order, Shipment, User
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.shipment_repository import ShipmentRepository
from app.schemas.order import OrderShipRequest
from app.services.audit_service import AuditService
from app.services.conversation_event_service import ConversationEventService
from app.services.conversation_priority_service import ConversationPriorityService
from app.services.channel_outbound_service import ChannelOutboundService, operator_action_send_key
from app.services.order_service import OrderService
from app.services.shop_service import ShopService

logger = logging.getLogger(__name__)


class ShippingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.shipments = ShipmentRepository(db)
        self.audit_logs = AuditLogRepository(db)
        self.shop_service = ShopService(db)
        self.order_service = OrderService(db)

    def ship_order(
        self,
        shop_id: UUID,
        order_id: UUID,
        payload: OrderShipRequest,
        user: User,
    ) -> Order:
        self.shop_service.get_shop(shop_id, user)
        order = self.orders.get_for_shop(shop_id, order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        if order.status not in {OrderStatus.PAID, OrderStatus.ORDER_CREATED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot ship order in status {order.status.value}",
            )

        now = datetime.now(UTC)
        shipment = Shipment(
            order_id=order.id,
            provider=payload.provider,
            status=ShipmentStatus.SHIPPED,
            tracking_code=payload.tracking_code,
            tracking_url=payload.tracking_url,
            shipped_at=now,
        )
        self.shipments.create(shipment)

        if order.status == OrderStatus.PAID:
            order.status = OrderStatus.ORDER_CREATED
        order.shipping_status = OrderShippingStatus.SHIPPED

        self.order_service.audit(
            shop_id=shop_id,
            user_id=user.id,
            action="ship_order",
            entity_type="order",
            entity_id=str(order.id),
            details={
                "tracking_code": payload.tracking_code,
                "tracking_url": payload.tracking_url,
                "provider": payload.provider.value,
            },
        )
        self.shipments.commit()
        self.orders.refresh(order)
        logger.info("Order shipped order=%s tracking=%s", order.id, payload.tracking_code)
        return order

    def send_tracking_code(
        self,
        shop_id: UUID,
        order_id: UUID,
        payload: OrderShipRequest,
        user: User,
    ) -> Order:
        order = self.ship_order(shop_id, order_id, payload, user)
        if order.conversation_id:
            tracking_text = f"کد رهگیری سفارش شما: {payload.tracking_code}"
            if payload.tracking_url:
                tracking_text += f"\n{payload.tracking_url}"
            shipment = self.shipments.get_latest_for_order(order.id)
            idempotency_key = (
                operator_action_send_key(shipment.id, "send-tracking")
                if shipment is not None
                else operator_action_send_key(order.id, "send-tracking")
            )
            ChannelOutboundService(self.db).send_text_message(
                order.conversation_id,
                tracking_text,
                idempotency_key=idempotency_key,
            )
            ConversationEventService(self.db).record(
                order.conversation_id,
                ConversationEventType.ORDER_SHIPPED,
                metadata={
                    "order_id": str(order.id),
                    "tracking_code": payload.tracking_code,
                },
                created_by_user_id=user.id,
            )
            ConversationPriorityService(self.db).refresh(order.conversation_id)
        AuditService(self.db).log(
            action="tracking_code_sent",
            entity_type="order",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(order.id),
            metadata={"tracking_code": payload.tracking_code},
        )
        self.shipments.commit()
        return order

    def create_pending_shipment(self, order: Order, provider: ShipmentProvider = ShipmentProvider.MANUAL) -> Shipment:
        shipment = Shipment(
            order_id=order.id,
            provider=provider,
            status=ShipmentStatus.PREPARING,
        )
        self.shipments.create(shipment)
        order.shipping_status = OrderShippingStatus.PREPARING
        return shipment

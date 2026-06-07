from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.domain.enums import OrderPaymentStatus, OrderShippingStatus, OrderStatus
from app.domain.models import Order


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, order_id: UUID) -> Order | None:
        return self.db.get(Order, order_id)

    def get_for_shop(self, shop_id: UUID, order_id: UUID) -> Order | None:
        stmt = (
            select(Order)
            .options(
                joinedload(Order.items),
                joinedload(Order.payments),
                joinedload(Order.shipments),
            )
            .where(Order.id == order_id, Order.shop_id == shop_id)
        )
        return self.db.scalar(stmt)

    def get_active_for_conversation(self, conversation_id: UUID) -> Order | None:
        active_statuses = {
            OrderStatus.DRAFT,
            OrderStatus.WAITING_FOR_CONFIRMATION,
            OrderStatus.CONFIRMED,
            OrderStatus.WAITING_FOR_PAYMENT,
        }
        stmt = (
            select(Order)
            .options(joinedload(Order.items))
            .where(Order.conversation_id == conversation_id, Order.status.in_(active_statuses))
            .order_by(Order.created_at.desc())
        )
        return self.db.scalar(stmt)

    def list_for_shop(
        self,
        shop_id: UUID,
        *,
        status: OrderStatus | None = None,
        payment_status: OrderPaymentStatus | None = None,
        shipping_status: OrderShippingStatus | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> list[Order]:
        stmt = select(Order).where(Order.shop_id == shop_id)
        if status is not None:
            stmt = stmt.where(Order.status == status)
        if payment_status is not None:
            stmt = stmt.where(Order.payment_status == payment_status)
        if shipping_status is not None:
            stmt = stmt.where(Order.shipping_status == shipping_status)
        if created_from is not None:
            stmt = stmt.where(Order.created_at >= created_from)
        if created_to is not None:
            stmt = stmt.where(Order.created_at <= created_to)
        stmt = stmt.order_by(Order.created_at.desc())
        return list(self.db.scalars(stmt).unique().all())

    def list_expired_candidates(self, now: datetime) -> list[Order]:
        stmt = select(Order).where(
            Order.status == OrderStatus.WAITING_FOR_PAYMENT,
            Order.expires_at.is_not(None),
            Order.expires_at < now,
        )
        return list(self.db.scalars(stmt).all())

    def create(self, order: Order) -> Order:
        self.db.add(order)
        self.db.flush()
        return order

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, order: Order) -> Order:
        self.db.refresh(order)
        return order

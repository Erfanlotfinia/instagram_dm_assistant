from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import OrderStateTransition


class OrderStateTransitionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, transition: OrderStateTransition) -> OrderStateTransition:
        self.db.add(transition)
        self.db.flush()
        return transition

    def list_for_order(self, shop_id: UUID, order_id: UUID) -> list[OrderStateTransition]:
        stmt = (
            select(OrderStateTransition)
            .where(
                OrderStateTransition.shop_id == shop_id,
                OrderStateTransition.order_id == order_id,
            )
            .order_by(OrderStateTransition.created_at)
        )
        return list(self.db.scalars(stmt).all())

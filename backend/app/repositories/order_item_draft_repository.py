from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import OrderItemDraft


class OrderItemDraftRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, item: OrderItemDraft) -> OrderItemDraft:
        self.db.add(item)
        self.db.flush()
        return item

    def list_for_order(self, order_id: UUID) -> list[OrderItemDraft]:
        stmt = select(OrderItemDraft).where(OrderItemDraft.order_id == order_id)
        return list(self.db.scalars(stmt).all())

    def delete_for_order(self, order_id: UUID) -> None:
        for item in self.list_for_order(order_id):
            self.db.delete(item)
        self.db.flush()

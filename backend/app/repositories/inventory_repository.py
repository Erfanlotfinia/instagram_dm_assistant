from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import InventoryMovement


class InventoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, movement: InventoryMovement) -> InventoryMovement:
        self.db.add(movement)
        self.db.flush()
        return movement

    def list_for_variant(self, variant_id: UUID) -> list[InventoryMovement]:
        stmt = (
            select(InventoryMovement)
            .where(InventoryMovement.product_variant_id == variant_id)
            .order_by(InventoryMovement.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def commit(self) -> None:
        self.db.commit()

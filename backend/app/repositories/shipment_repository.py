from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Shipment


class ShipmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_latest_for_order(self, order_id: UUID) -> Shipment | None:
        stmt = (
            select(Shipment)
            .where(Shipment.order_id == order_id)
            .order_by(Shipment.created_at.desc())
        )
        return self.db.scalar(stmt)

    def create(self, shipment: Shipment) -> Shipment:
        self.db.add(shipment)
        self.db.flush()
        return shipment

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, shipment: Shipment) -> Shipment:
        self.db.refresh(shipment)
        return shipment

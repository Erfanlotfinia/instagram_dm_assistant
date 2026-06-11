from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import InventoryReservationStatus
from app.domain.models import InventoryReservation


class InventoryReservationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, reservation: InventoryReservation) -> InventoryReservation:
        self.db.add(reservation)
        self.db.flush()
        return reservation

    def get_by_id(self, reservation_id: UUID) -> InventoryReservation | None:
        return self.db.get(InventoryReservation, reservation_id)

    def get_active_for_order(self, order_id: UUID) -> list[InventoryReservation]:
        stmt = select(InventoryReservation).where(
            InventoryReservation.order_id == order_id,
            InventoryReservation.status == InventoryReservationStatus.ACTIVE,
        )
        return list(self.db.scalars(stmt).all())

    def get_active_for_order_variant(
        self, order_id: UUID, variant_id: UUID
    ) -> InventoryReservation | None:
        stmt = select(InventoryReservation).where(
            InventoryReservation.order_id == order_id,
            InventoryReservation.product_variant_id == variant_id,
            InventoryReservation.status == InventoryReservationStatus.ACTIVE,
        )
        return self.db.scalar(stmt)

    def list_for_order(self, order_id: UUID) -> list[InventoryReservation]:
        stmt = select(InventoryReservation).where(InventoryReservation.order_id == order_id)
        return list(self.db.scalars(stmt).all())

    def list_expired_active(self, before: datetime) -> list[InventoryReservation]:
        stmt = select(InventoryReservation).where(
            InventoryReservation.status == InventoryReservationStatus.ACTIVE,
            InventoryReservation.expires_at <= before,
        )
        return list(self.db.scalars(stmt).all())

    def list_active_for_variant(self, variant_id: UUID) -> list[InventoryReservation]:
        stmt = select(InventoryReservation).where(
            InventoryReservation.product_variant_id == variant_id,
            InventoryReservation.status == InventoryReservationStatus.ACTIVE,
        )
        return list(self.db.scalars(stmt).all())

    def commit(self) -> None:
        self.db.commit()

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import InventoryMovementType, InventoryReservationStatus
from app.domain.models import InventoryMovement, InventoryReservation
from app.integrations.redis_cache import RedisCacheService
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.inventory_reservation_repository import InventoryReservationRepository
from app.repositories.variant_repository import VariantRepository
from app.services.state_transition_service import INVENTORY_RESERVATION_STATE_MACHINE

logger = logging.getLogger(__name__)


class InventoryReservationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.reservations = InventoryReservationRepository(db)
        self.variants = VariantRepository(db)
        self.inventory = InventoryRepository(db)
        self.cache = RedisCacheService()

    def reserve(
        self,
        *,
        shop_id: UUID,
        order_id: UUID,
        product_variant_id: UUID,
        quantity: int,
        ttl_seconds: int,
    ) -> InventoryReservation:
        if quantity < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be positive")

        existing = self.reservations.get_active_for_order_variant(order_id, product_variant_id)
        if existing is not None:
            logger.info("Idempotent reserve reservation_id=%s order_id=%s", existing.id, order_id)
            return existing

        locked = self.variants.get_for_update(product_variant_id)
        if locked is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")

        available = locked.stock_quantity - locked.reserved_quantity
        if quantity > available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock: {available} available, {quantity} requested",
            )

        existing_movement = self.db.scalar(
            select(InventoryMovement).where(
                InventoryMovement.product_variant_id == product_variant_id,
                InventoryMovement.movement_type == InventoryMovementType.RESERVE,
                InventoryMovement.reference_type == "reservation",
                InventoryMovement.reference_id == str(order_id),
            )
        )
        if existing_movement is None:
            locked.reserved_quantity += quantity
            self.inventory.create(
                InventoryMovement(
                    product_variant_id=product_variant_id,
                    movement_type=InventoryMovementType.RESERVE,
                    quantity=quantity,
                    reason="Inventory reservation",
                    reference_type="reservation",
                    reference_id=str(order_id),
                )
            )

        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        reservation = InventoryReservation(
            shop_id=shop_id,
            order_id=order_id,
            product_variant_id=product_variant_id,
            quantity=quantity,
            status=InventoryReservationStatus.ACTIVE,
            expires_at=expires_at,
            ttl_seconds=ttl_seconds,
        )
        self.reservations.create(reservation)
        self._cache_reservation(reservation)
        logger.info(
            "reservation_created reservation_id=%s order_id=%s variant_id=%s qty=%s",
            reservation.id,
            order_id,
            product_variant_id,
            quantity,
        )
        self.reservations.commit()
        return reservation

    def refresh_reservation(self, reservation_id: UUID, ttl_seconds: int) -> InventoryReservation:
        reservation = self.reservations.get_by_id(reservation_id)
        if reservation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
        if reservation.status != InventoryReservationStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot refresh reservation in status {reservation.status.value}",
            )
        reservation.expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        reservation.ttl_seconds = ttl_seconds
        self._cache_reservation(reservation)
        self.reservations.commit()
        return reservation

    def release_reservation(self, reservation_id: UUID, reason: str = "Released") -> InventoryReservation:
        reservation = self.reservations.get_by_id(reservation_id)
        if reservation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
        if reservation.status in {
            InventoryReservationStatus.RELEASED,
            InventoryReservationStatus.EXPIRED,
        }:
            return reservation

        locked = self.variants.get_for_update(reservation.product_variant_id)
        if locked is not None:
            release_qty = min(reservation.quantity, locked.reserved_quantity)
            if release_qty > 0:
                locked.reserved_quantity -= release_qty
                existing_release = self.db.scalar(
                    select(InventoryMovement).where(
                        InventoryMovement.product_variant_id == reservation.product_variant_id,
                        InventoryMovement.movement_type == InventoryMovementType.RELEASE,
                        InventoryMovement.reference_type == "reservation",
                        InventoryMovement.reference_id == str(reservation.id),
                    )
                )
                if existing_release is None:
                    self.inventory.create(
                        InventoryMovement(
                            product_variant_id=reservation.product_variant_id,
                            movement_type=InventoryMovementType.RELEASE,
                            quantity=release_qty,
                            reason=reason,
                            reference_type="reservation",
                            reference_id=str(reservation.id),
                        )
                    )

        INVENTORY_RESERVATION_STATE_MACHINE.transition(reservation, InventoryReservationStatus.RELEASED)
        reservation.released_at = datetime.now(UTC)
        self.cache.delete_reservation_cache(str(reservation.id))
        logger.info("reservation_released reservation_id=%s reason=%s", reservation_id, reason)
        self.reservations.commit()
        return reservation

    def confirm_reservation(self, reservation_id: UUID) -> InventoryReservation:
        reservation = self.reservations.get_by_id(reservation_id)
        if reservation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
        if reservation.status == InventoryReservationStatus.CONFIRMED:
            return reservation
        if reservation.status != InventoryReservationStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot confirm reservation in status {reservation.status.value}",
            )
        INVENTORY_RESERVATION_STATE_MACHINE.transition(reservation, InventoryReservationStatus.CONFIRMED)
        reservation.confirmed_at = datetime.now(UTC)
        self.cache.delete_reservation_cache(str(reservation.id))
        logger.info("reservation_confirmed reservation_id=%s", reservation_id)
        self.reservations.commit()
        return reservation

    def expire_reservation(self, reservation_id: UUID) -> InventoryReservation:
        reservation = self.reservations.get_by_id(reservation_id)
        if reservation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")
        if reservation.status != InventoryReservationStatus.ACTIVE:
            return reservation
        self.release_reservation(reservation_id, reason="Reservation expired")
        INVENTORY_RESERVATION_STATE_MACHINE.transition(reservation, InventoryReservationStatus.EXPIRED)
        return reservation

    def release_all_for_order(self, order_id: UUID, reason: str = "Order released") -> None:
        for reservation in self.reservations.list_for_order(order_id):
            if reservation.status in {
                InventoryReservationStatus.ACTIVE,
                InventoryReservationStatus.CONFIRMED,
            }:
                self.release_reservation(reservation.id, reason=reason)

    def _cache_reservation(self, reservation: InventoryReservation) -> None:
        ttl = max(1, int((reservation.expires_at - datetime.now(UTC)).total_seconds()))
        self.cache.set_reservation_cache(
            str(reservation.id),
            {
                "id": str(reservation.id),
                "order_id": str(reservation.order_id),
                "product_variant_id": str(reservation.product_variant_id),
                "quantity": reservation.quantity,
                "status": reservation.status.value,
                "expires_at": reservation.expires_at.isoformat(),
            },
            ttl,
        )

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.enums import InventoryMovementType
from app.domain.models import InventoryMovement, User
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.inventory import InventoryMovementRead, InventoryReleaseRequest, InventoryReserveRequest
from app.services.audit_service import AuditService
from app.services.shop_service import ShopService


class InventoryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.variants = VariantRepository(db)
        self.inventory = InventoryRepository(db)
        self.shop_service = ShopService(db)

    @staticmethod
    def available_stock(stock_quantity: int, reserved_quantity: int) -> int:
        return stock_quantity - reserved_quantity

    def list_movements(
        self,
        shop_id: UUID,
        variant_id: UUID,
        user: User,
    ) -> list[InventoryMovementRead]:
        self.shop_service.get_shop(shop_id, user)
        variant = self._get_variant_for_shop_or_404(shop_id, variant_id)
        movements = self.inventory.list_for_variant(variant.id)
        return [InventoryMovementRead.model_validate(m) for m in movements]

    def reserve(
        self,
        shop_id: UUID,
        variant_id: UUID,
        payload: InventoryReserveRequest,
        user: User,
    ) -> VariantInventorySnapshot:
        self.shop_service.get_shop(shop_id, user)
        snapshot = self._apply_movement(
            shop_id=shop_id,
            variant_id=variant_id,
            movement_type=InventoryMovementType.RESERVE,
            quantity=payload.quantity,
            reason=payload.reason,
            reference_type=payload.reference_type,
            reference_id=payload.reference_id,
        )
        AuditService(self.db).log(
            action="inventory_reserve",
            entity_type="variant",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(variant_id),
            metadata={"quantity": payload.quantity, "reason": payload.reason},
        )
        self.inventory.commit()
        return snapshot

    def release(
        self,
        shop_id: UUID,
        variant_id: UUID,
        payload: InventoryReleaseRequest,
        user: User,
    ) -> VariantInventorySnapshot:
        self.shop_service.get_shop(shop_id, user)
        snapshot = self._apply_movement(
            shop_id=shop_id,
            variant_id=variant_id,
            movement_type=InventoryMovementType.RELEASE,
            quantity=payload.quantity,
            reason=payload.reason,
            reference_type=payload.reference_type,
            reference_id=payload.reference_id,
        )
        AuditService(self.db).log(
            action="inventory_release",
            entity_type="variant",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(variant_id),
            metadata={"quantity": payload.quantity, "reason": payload.reason},
        )
        self.inventory.commit()
        return snapshot

    def _apply_movement(
        self,
        shop_id: UUID,
        variant_id: UUID,
        movement_type: InventoryMovementType,
        quantity: int,
        reason: str,
        reference_type: str | None,
        reference_id: str | None,
    ) -> "VariantInventorySnapshot":
        variant = self.variants.get_for_shop(shop_id, variant_id)
        if variant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")

        locked = self.variants.get_for_update(variant_id)
        if locked is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")

        if movement_type == InventoryMovementType.RESERVE:
            available = self.available_stock(locked.stock_quantity, locked.reserved_quantity)
            if quantity > available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient available stock: {available} available, {quantity} requested",
                )
            locked.reserved_quantity += quantity
        elif movement_type == InventoryMovementType.RELEASE:
            if quantity > locked.reserved_quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot release more than reserved: {locked.reserved_quantity} reserved",
                )
            locked.reserved_quantity -= quantity
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported movement type")

        if self.available_stock(locked.stock_quantity, locked.reserved_quantity) < 0:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Operation would result in negative available stock",
            )

        movement = InventoryMovement(
            product_variant_id=locked.id,
            movement_type=movement_type,
            quantity=quantity,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        self.inventory.create(movement)
        self.inventory.commit()
        self.variants.refresh(locked)

        return VariantInventorySnapshot(
            variant_id=locked.id,
            stock_quantity=locked.stock_quantity,
            reserved_quantity=locked.reserved_quantity,
            available_stock=self.available_stock(locked.stock_quantity, locked.reserved_quantity),
        )

    def _get_variant_for_shop_or_404(self, shop_id: UUID, variant_id: UUID):
        variant = self.variants.get_for_shop(shop_id, variant_id)
        if variant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
        return variant


class VariantInventorySnapshot:
    def __init__(
        self,
        variant_id: UUID,
        stock_quantity: int,
        reserved_quantity: int,
        available_stock: int,
    ) -> None:
        self.variant_id = variant_id
        self.stock_quantity = stock_quantity
        self.reserved_quantity = reserved_quantity
        self.available_stock = available_stock

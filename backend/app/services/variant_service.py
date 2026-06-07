from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.models import ProductVariant, User
from app.repositories.product_repository import ProductRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.variant import VariantCreate, VariantRead, VariantUpdate
from app.services.shop_service import ShopService


class VariantService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.variants = VariantRepository(db)
        self.products = ProductRepository(db)
        self.shop_service = ShopService(db)

    def list_variants(self, shop_id: UUID, product_id: UUID, user: User) -> list[VariantRead]:
        self._require_product(shop_id, product_id, user)
        variants = self.variants.list_for_product(product_id)
        return [VariantRead.from_variant(v) for v in variants]

    def create_variant(
        self,
        shop_id: UUID,
        product_id: UUID,
        payload: VariantCreate,
        user: User,
    ) -> VariantRead:
        self._require_product(shop_id, product_id, user)
        self._ensure_unique_sku(shop_id, payload.sku)
        variant = ProductVariant(
            product_id=product_id,
            color=payload.color,
            size=payload.size,
            sku=payload.sku,
            price=payload.price,
            stock_quantity=payload.stock_quantity,
            reserved_quantity=0,
            is_active=payload.is_active,
        )
        try:
            created = self.variants.create(variant)
            self.variants.commit()
            self.variants.refresh(created)
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="SKU already exists for this product",
            ) from exc
        return VariantRead.from_variant(created)

    def update_variant(
        self,
        shop_id: UUID,
        variant_id: UUID,
        payload: VariantUpdate,
        user: User,
    ) -> VariantRead:
        self.shop_service.get_shop(shop_id, user)
        variant = self._get_variant_for_shop_or_404(shop_id, variant_id)
        updates = payload.model_dump(exclude_unset=True)

        if "sku" in updates and updates["sku"] is not None:
            self._ensure_unique_sku(shop_id, updates["sku"], exclude_variant_id=variant_id)

        if "stock_quantity" in updates and updates["stock_quantity"] is not None:
            new_stock = updates["stock_quantity"]
            if new_stock - variant.reserved_quantity < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Stock quantity cannot be less than reserved quantity",
                )

        for field, value in updates.items():
            setattr(variant, field, value)

        try:
            self.variants.commit()
            self.variants.refresh(variant)
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="SKU already exists for this shop",
            ) from exc
        return VariantRead.from_variant(variant)

    def _require_product(self, shop_id: UUID, product_id: UUID, user: User) -> None:
        self.shop_service.get_shop(shop_id, user)
        product = self.products.get_for_shop(shop_id, product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    def _get_variant_for_shop_or_404(self, shop_id: UUID, variant_id: UUID) -> ProductVariant:
        variant = self.variants.get_for_shop(shop_id, variant_id)
        if variant is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
        return variant

    def _ensure_unique_sku(
        self,
        shop_id: UUID,
        sku: str,
        exclude_variant_id: UUID | None = None,
    ) -> None:
        existing = self.variants.get_by_sku_for_shop(shop_id, sku, exclude_variant_id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="SKU already exists for this shop",
            )

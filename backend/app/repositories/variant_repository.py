from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.domain.models import Product, ProductVariant


class VariantRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, variant_id: UUID) -> ProductVariant | None:
        stmt = (
            select(ProductVariant)
            .options(joinedload(ProductVariant.product))
            .where(ProductVariant.id == variant_id)
        )
        return self.db.scalar(stmt)

    def get_for_product(self, product_id: UUID, variant_id: UUID) -> ProductVariant | None:
        stmt = select(ProductVariant).where(
            ProductVariant.id == variant_id,
            ProductVariant.product_id == product_id,
        )
        return self.db.scalar(stmt)

    def list_for_product(self, product_id: UUID) -> list[ProductVariant]:
        stmt = (
            select(ProductVariant)
            .where(ProductVariant.product_id == product_id)
            .order_by(ProductVariant.created_at)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_sku_for_shop(self, shop_id: UUID, sku: str, exclude_variant_id: UUID | None = None) -> ProductVariant | None:
        stmt = (
            select(ProductVariant)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(Product.shop_id == shop_id, ProductVariant.sku == sku)
        )
        if exclude_variant_id is not None:
            stmt = stmt.where(ProductVariant.id != exclude_variant_id)
        return self.db.scalar(stmt)

    def get_for_shop(self, shop_id: UUID, variant_id: UUID) -> ProductVariant | None:
        stmt = (
            select(ProductVariant)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(Product.shop_id == shop_id, ProductVariant.id == variant_id)
        )
        return self.db.scalar(stmt)

    def get_for_update(self, variant_id: UUID) -> ProductVariant | None:
        stmt = (
            select(ProductVariant)
            .where(ProductVariant.id == variant_id)
            .with_for_update()
        )
        return self.db.scalar(stmt)

    def create(self, variant: ProductVariant) -> ProductVariant:
        self.db.add(variant)
        self.db.flush()
        return variant

    def delete(self, variant: ProductVariant) -> None:
        self.db.delete(variant)
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, variant: ProductVariant) -> ProductVariant:
        self.db.refresh(variant)
        return variant

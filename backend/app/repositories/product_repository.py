from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import ProductStatus
from app.domain.models import Product


class ProductRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, product_id: UUID) -> Product | None:
        return self.db.get(Product, product_id)

    def get_for_shop(self, shop_id: UUID, product_id: UUID) -> Product | None:
        stmt = select(Product).where(Product.id == product_id, Product.shop_id == shop_id)
        return self.db.scalar(stmt)

    def list_active(self, limit: int = 50) -> list[Product]:
        stmt = (
            select(Product)
            .where(Product.status == ProductStatus.ACTIVE)
            .order_by(Product.updated_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def list_for_shop(self, shop_id: UUID) -> list[Product]:
        stmt = (
            select(Product)
            .where(Product.shop_id == shop_id)
            .order_by(Product.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def create(self, product: Product) -> Product:
        self.db.add(product)
        self.db.flush()
        return product

    def delete(self, product: Product) -> None:
        self.db.delete(product)

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, product: Product) -> Product:
        self.db.refresh(product)
        return product

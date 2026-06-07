from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.models import Product, User
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.audit_service import AuditService
from app.services.shop_service import ShopService


class ProductService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.shop_service = ShopService(db)

    def list_products(self, shop_id: UUID, user: User) -> list[ProductRead]:
        self.shop_service.get_shop(shop_id, user)
        return [ProductRead.model_validate(p) for p in self.products.list_for_shop(shop_id)]

    def get_product(self, shop_id: UUID, product_id: UUID, user: User) -> ProductRead:
        self.shop_service.get_shop(shop_id, user)
        product = self._get_product_or_404(shop_id, product_id)
        return ProductRead.model_validate(product)

    def create_product(self, shop_id: UUID, payload: ProductCreate, user: User) -> ProductRead:
        shop = self.shop_service.get_shop(shop_id, user)
        currency = payload.currency or shop.default_currency
        product = Product(
            shop_id=shop_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            base_price=payload.base_price,
            currency=currency,
            main_image_url=payload.main_image_url,
        )
        self.products.create(product)
        AuditService(self.db).log(
            action="product_create",
            entity_type="product",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(product.id),
            metadata={"title": product.title},
        )
        self.products.commit()
        self.products.refresh(product)
        return ProductRead.model_validate(product)

    def update_product(
        self,
        shop_id: UUID,
        product_id: UUID,
        payload: ProductUpdate,
        user: User,
    ) -> ProductRead:
        self.shop_service.get_shop(shop_id, user)
        product = self._get_product_or_404(shop_id, product_id)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(product, field, value)
        AuditService(self.db).log(
            action="product_update",
            entity_type="product",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(product.id),
            metadata=updates,
        )
        self.products.commit()
        self.products.refresh(product)
        return ProductRead.model_validate(product)

    def delete_product(self, shop_id: UUID, product_id: UUID, user: User) -> None:
        self.shop_service.get_shop(shop_id, user)
        product = self._get_product_or_404(shop_id, product_id)
        self.products.delete(product)
        self.products.commit()

    def _get_product_or_404(self, shop_id: UUID, product_id: UUID) -> Product:
        product = self.products.get_for_shop(shop_id, product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        return product

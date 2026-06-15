from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.domain.enums import ProductStatus
from app.domain.models import Product, ProductVariant


@dataclass(frozen=True)
class GenericProductView:
    product_id: str
    title: str
    description: str | None
    category: str | None
    attributes: dict[str, Any] = field(default_factory=dict)
    variants: list[dict[str, Any]] = field(default_factory=list)
    price: Decimal | None = None
    stock: int = 0
    media: list[dict[str, Any]] = field(default_factory=list)
    availability_rules: dict[str, Any] = field(default_factory=dict)


class ProductDiscoveryService:
    """Channel-agnostic generic product discovery for any online shop domain."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def search(
        self,
        shop_id: UUID,
        query: str | None = None,
        *,
        category: str | None = None,
        limit: int = 10,
    ) -> list[GenericProductView]:
        stmt = select(Product).where(
            Product.shop_id == shop_id, Product.status == ProductStatus.ACTIVE
        )
        if category:
            stmt = stmt.where(Product.category == category)
        if query:
            like = f"%{query}%"
            stmt = stmt.where(or_(Product.title.ilike(like), Product.description.ilike(like)))
        products = self.db.scalars(stmt.order_by(Product.created_at.desc()).limit(limit)).all()
        return [self.to_generic_view(product) for product in products]

    def to_generic_view(self, product: Product) -> GenericProductView:
        variants = self.db.scalars(
            select(ProductVariant).where(
                ProductVariant.product_id == product.id, ProductVariant.is_active.is_(True)
            )
        ).all()
        variant_views = [
            {
                "variant_id": str(v.id),
                "sku": v.sku,
                "attributes": {
                    k: val for k, val in {"color": v.color, "size": v.size}.items() if val
                },
                "price": str(v.price),
                "stock": max((v.stock_quantity or 0) - (v.reserved_quantity or 0), 0),
            }
            for v in variants
        ]
        stock = sum(int(v["stock"]) for v in variant_views)
        price = variants[0].price if variants else product.base_price
        return GenericProductView(
            product_id=str(product.id),
            title=product.title,
            description=product.description,
            category=product.category,
            attributes={"legacy_size_chart": product.size_chart or {}},
            variants=variant_views,
            price=price,
            stock=stock,
            media=(
                [{"url": product.main_image_url, "type": "image"}] if product.main_image_url else []
            ),
            availability_rules={
                "status": product.status.value
                if hasattr(product.status, "value")
                else str(product.status)
            },
        )

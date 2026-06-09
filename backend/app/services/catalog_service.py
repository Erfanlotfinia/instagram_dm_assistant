from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.enums import CatalogAliasSource
from app.domain.models import ProductAlias, User
from app.repositories.catalog_repository import ProductAliasRepository, ProductNormalizedRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.catalog import (
    CatalogProductListResponse,
    ProductAliasRead,
    ProductAliasesPatchRequest,
    ProductAliasesPatchResponse,
    ProductNormalizedRead,
)
from app.services.catalog_normalization_service import CatalogNormalizationService
from app.services.shop_service import ShopService


class CatalogService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.shop_service = ShopService(db)
        self.products = ProductRepository(db)
        self.normalized_repo = ProductNormalizedRepository(db)
        self.alias_repo = ProductAliasRepository(db)
        self.normalizer = CatalogNormalizationService(db)

    def list_products(
        self,
        shop_id: UUID,
        user: User,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> CatalogProductListResponse:
        self.shop_service.get_shop(shop_id, user)
        items, total = self.normalized_repo.list_for_shop(shop_id, page=page, page_size=page_size, search=search)
        return CatalogProductListResponse(
            items=[ProductNormalizedRead.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    def patch_aliases(
        self,
        shop_id: UUID,
        product_id: UUID,
        payload: ProductAliasesPatchRequest,
        user: User,
    ) -> ProductAliasesPatchResponse:
        self.shop_service.get_shop(shop_id, user)
        product = self.products.get_for_shop(shop_id, product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        normalized = self.normalized_repo.get_by_product(shop_id, product_id)
        for alias_text in payload.add:
            cleaned = CatalogNormalizationService._normalize_alias(alias_text)
            conflict = self.alias_repo.find_by_alias(shop_id, cleaned)
            if conflict and conflict.product_id != product_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Alias conflict: '{cleaned}' already mapped to another product",
                )
            if conflict:
                continue
            self.alias_repo.add(
                ProductAlias(
                    shop_id=shop_id,
                    product_id=product_id,
                    normalized_product_id=normalized.id if normalized else None,
                    alias_text=cleaned,
                    language=payload.language,
                    source=CatalogAliasSource.MANUAL,
                    confidence=1.0,
                )
            )

        existing_aliases = self.alias_repo.list_for_product(shop_id, product_id)
        remove_set = {(CatalogNormalizationService._normalize_alias(value)) for value in payload.remove}
        for alias in existing_aliases:
            if alias.alias_text in remove_set:
                self.alias_repo.deactivate(alias)

        self.alias_repo.commit()
        aliases = self.alias_repo.list_for_product(shop_id, product_id)
        return ProductAliasesPatchResponse(
            product_id=product_id,
            aliases=[ProductAliasRead.model_validate(alias) for alias in aliases],
        )

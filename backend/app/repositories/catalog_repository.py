from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import CatalogAliasSource, CatalogImportJobStatus
from app.domain.models import CatalogImportJob, ProductAlias, ProductNormalized


class ProductNormalizedRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_shop(self, shop_id: UUID, normalized_id: UUID) -> ProductNormalized | None:
        stmt = select(ProductNormalized).where(
            ProductNormalized.id == normalized_id,
            ProductNormalized.shop_id == shop_id,
        )
        return self.db.scalar(stmt)

    def get_by_product(self, shop_id: UUID, product_id: UUID) -> ProductNormalized | None:
        stmt = select(ProductNormalized).where(
            ProductNormalized.shop_id == shop_id,
            ProductNormalized.product_id == product_id,
        )
        return self.db.scalar(stmt)

    def list_for_shop(
        self,
        shop_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[ProductNormalized], int]:
        stmt = (
            select(ProductNormalized)
            .where(ProductNormalized.shop_id == shop_id)
            .options(selectinload(ProductNormalized.aliases))
        )
        count_stmt = select(func.count()).select_from(ProductNormalized).where(ProductNormalized.shop_id == shop_id)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(ProductNormalized.normalized_title.ilike(pattern))
            count_stmt = count_stmt.where(ProductNormalized.normalized_title.ilike(pattern))
        total = self.db.scalar(count_stmt) or 0
        offset = max(page - 1, 0) * page_size
        items = list(self.db.scalars(stmt.order_by(ProductNormalized.updated_at.desc()).offset(offset).limit(page_size)))
        return items, int(total)

    def add(self, entity: ProductNormalized) -> ProductNormalized:
        self.db.add(entity)
        self.db.flush()
        return entity

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, entity: ProductNormalized) -> None:
        self.db.refresh(entity)


class ProductAliasRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_product(self, shop_id: UUID, product_id: UUID) -> list[ProductAlias]:
        stmt = select(ProductAlias).where(
            ProductAlias.shop_id == shop_id,
            ProductAlias.product_id == product_id,
            ProductAlias.is_active.is_(True),
        )
        return list(self.db.scalars(stmt))

    def find_by_alias(self, shop_id: UUID, alias_text: str) -> ProductAlias | None:
        stmt = select(ProductAlias).where(
            ProductAlias.shop_id == shop_id,
            ProductAlias.alias_text == alias_text,
            ProductAlias.is_active.is_(True),
        )
        return self.db.scalar(stmt)

    def add(self, entity: ProductAlias) -> ProductAlias:
        self.db.add(entity)
        self.db.flush()
        return entity

    def deactivate(self, alias: ProductAlias) -> None:
        alias.is_active = False

    def commit(self) -> None:
        self.db.commit()


class CatalogImportJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, job_id: UUID) -> CatalogImportJob | None:
        return self.db.get(CatalogImportJob, job_id)

    def get_for_shop(self, shop_id: UUID, job_id: UUID) -> CatalogImportJob | None:
        stmt = select(CatalogImportJob).where(
            CatalogImportJob.id == job_id,
            CatalogImportJob.shop_id == shop_id,
        )
        return self.db.scalar(stmt)

    def add(self, job: CatalogImportJob) -> CatalogImportJob:
        self.db.add(job)
        self.db.flush()
        return job

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, job: CatalogImportJob) -> None:
        self.db.refresh(job)

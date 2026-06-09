from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import CatalogImportJobStatus, ProductStatus
from app.domain.models import CatalogImportJob, Product, ProductVariant, User
from app.repositories.catalog_repository import CatalogImportJobRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.catalog import CatalogImportJobRead, CatalogImportRequest
from app.services.catalog_normalization_service import CatalogNormalizationService
from app.services.shop_service import ShopService

logger = logging.getLogger(__name__)


class CatalogImportService:
    """Backpressure-safe catalog import with resumable checkpoints."""

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.shop_service = ShopService(db)
        self.products = ProductRepository(db)
        self.variants = VariantRepository(db)
        self.jobs = CatalogImportJobRepository(db)
        self.normalizer = CatalogNormalizationService(db)

    def import_catalog(self, payload: CatalogImportRequest, user: User) -> CatalogImportJobRead:
        self.shop_service.get_shop(payload.shop_id, user)
        job = self._resolve_job(payload)
        batch_size = self.settings.catalog_import_batch_size
        start_index = int(job.checkpoint.get("next_index", 0))

        if job.status == CatalogImportJobStatus.PENDING:
            job.status = CatalogImportJobStatus.RUNNING
            job.started_at = datetime.now(UTC)
            job.total_rows = len(payload.rows) if not job.total_rows else job.total_rows

        try:
            for index in range(start_index, len(payload.rows)):
                row = payload.rows[index]
                try:
                    self._import_row(payload.shop_id, row)
                    job.processed_rows += 1
                except Exception as exc:  # noqa: BLE001 - row-level failure tracking
                    job.failed_rows += 1
                    logger.warning("Catalog import row %s failed: %s", index, exc)
                if (index + 1) % batch_size == 0:
                    job.checkpoint = {"next_index": index + 1}
                    self.jobs.commit()
            job.checkpoint = {"next_index": len(payload.rows)}
            job.status = CatalogImportJobStatus.COMPLETED
            job.completed_at = datetime.now(UTC)
        except Exception as exc:  # noqa: BLE001
            job.status = CatalogImportJobStatus.FAILED
            job.error_message = str(exc)
            job.checkpoint = {"next_index": job.checkpoint.get("next_index", start_index)}
            logger.exception("Catalog import job %s failed", job.id)
        self.jobs.commit()
        self.jobs.refresh(job)
        return CatalogImportJobRead.model_validate(job)

    def _resolve_job(self, payload: CatalogImportRequest) -> CatalogImportJob:
        if payload.resume_job_id:
            job = self.jobs.get_for_shop(payload.shop_id, payload.resume_job_id)
            if job is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
            if job.status not in {CatalogImportJobStatus.RUNNING, CatalogImportJobStatus.PAUSED, CatalogImportJobStatus.FAILED}:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Import job is not resumable")
            job.status = CatalogImportJobStatus.RUNNING
            return job
        job = CatalogImportJob(
            shop_id=payload.shop_id,
            status=CatalogImportJobStatus.PENDING,
            source_format=payload.source_format,
            total_rows=len(payload.rows),
        )
        return self.jobs.add(job)

    def _import_row(self, shop_id: UUID, row) -> Product:
        product = Product(
            shop_id=shop_id,
            title=row.title,
            description=row.description,
            status=ProductStatus.ACTIVE,
            base_price=Decimal(str(row.base_price or 0)),
            currency=row.currency or "USD",
            category=row.category,
        )
        self.products.create(product)
        created_variants: list[ProductVariant] = []
        for variant_data in row.variants or []:
            variant = ProductVariant(
                product_id=product.id,
                color=variant_data.get("color"),
                size=variant_data.get("size"),
                sku=variant_data.get("sku") or f"{product.id}-sku",
                price=Decimal(str(variant_data.get("price") or row.base_price or 0)),
                stock_quantity=int(variant_data.get("stock_quantity") or 0),
            )
            self.variants.create(variant)
            created_variants.append(variant)
        self.normalizer.normalize_product(
            product,
            created_variants,
            brand=row.brand,
            material=row.material,
            gender=row.gender,
            collection=row.collection,
            extra_aliases=row.aliases,
        )
        self.products.commit()
        return product

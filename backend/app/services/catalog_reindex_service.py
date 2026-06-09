from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import CatalogImportJobStatus, ProductStatus
from app.domain.models import CatalogImportJob, Product, User
from app.integrations.openai_client import LiveOpenAIEmbeddingClient, OpenAIEmbeddingClient
from app.integrations.qdrant_client import LiveQdrantClient, QdrantClient
from app.repositories.catalog_repository import CatalogImportJobRepository, ProductNormalizedRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.catalog import CatalogReindexJobRead, CatalogReindexRequest
from app.services.catalog_normalization_service import CatalogNormalizationService
from app.services.shop_service import ShopService

logger = logging.getLogger(__name__)


class CatalogReindexService:
    """Safe, resumable Qdrant reindexing for products and variants."""

    def __init__(
        self,
        db: Session,
        qdrant_client: QdrantClient | None = None,
        embedding_client: OpenAIEmbeddingClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.shop_service = ShopService(db)
        self.products = ProductRepository(db)
        self.variants = VariantRepository(db)
        self.normalized_repo = ProductNormalizedRepository(db)
        self.jobs = CatalogImportJobRepository(db)
        self.normalizer = CatalogNormalizationService(db)
        self.qdrant = qdrant_client or LiveQdrantClient(self.settings)
        self.embeddings = embedding_client or LiveOpenAIEmbeddingClient(self.settings)

    def reindex(self, payload: CatalogReindexRequest, user: User) -> CatalogReindexJobRead:
        self.shop_service.get_shop(payload.shop_id, user)
        batch_size = payload.batch_size or self.settings.catalog_reindex_batch_size
        product_ids = payload.product_ids
        if not product_ids:
            product_ids = [product.id for product in self.products.list_for_shop(payload.shop_id)]

        job = self._resolve_job(payload, total=len(product_ids))
        start_index = int(job.checkpoint.get("next_index", 0))
        indexed = int(job.checkpoint.get("indexed_products", 0))

        for index in range(start_index, len(product_ids)):
            product = self.products.get_for_shop(payload.shop_id, product_ids[index])
            if product is None or product.status != ProductStatus.ACTIVE:
                continue
            variants = self.variants.list_for_product(product.id)
            normalized = self.normalizer.normalize_product(product, variants)
            self._index_product(product, normalized, variants)
            indexed += 1
            if (index + 1) % batch_size == 0:
                job.checkpoint = {"next_index": index + 1, "indexed_products": indexed}
                job.processed_rows = indexed
                self.jobs.commit()

        job.checkpoint = {"next_index": len(product_ids), "indexed_products": indexed}
        job.processed_rows = indexed
        job.status = CatalogImportJobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        self.jobs.commit()
        self.jobs.refresh(job)
        return CatalogReindexJobRead(
            job_id=job.id,
            shop_id=payload.shop_id,
            status=job.status.value,
            total_products=len(product_ids),
            indexed_products=indexed,
            checkpoint=job.checkpoint,
        )

    def _resolve_job(self, payload: CatalogReindexRequest, total: int) -> CatalogImportJob:
        if payload.resume_job_id:
            job = self.jobs.get_for_shop(payload.shop_id, payload.resume_job_id)
            if job is None:
                job = CatalogImportJob(
                    id=uuid4(),
                    shop_id=payload.shop_id,
                    status=CatalogImportJobStatus.RUNNING,
                    source_format="reindex",
                    total_rows=total,
                    started_at=datetime.now(UTC),
                )
                return self.jobs.add(job)
            job.status = CatalogImportJobStatus.RUNNING
            return job
        job = CatalogImportJob(
            shop_id=payload.shop_id,
            status=CatalogImportJobStatus.RUNNING,
            source_format="reindex",
            total_rows=total,
            started_at=datetime.now(UTC),
        )
        return self.jobs.add(job)

    def _index_product(self, product: Product, normalized, variants) -> None:
        index_text = self._build_index_text(product, normalized, variants)
        vector = self.embeddings.embed_text(index_text)
        self.qdrant.ensure_collection(len(vector))
        self.qdrant.ensure_variants_collection(len(vector))
        has_stock = any(v.available_stock > 0 for v in variants)
        payload = {
            "title": product.title,
            "normalized_title": normalized.normalized_title,
            "description": product.description or "",
            "shop_id": str(product.shop_id),
            "product_id": str(product.id),
            "brand": normalized.brand,
            "gender": normalized.gender,
            "collection": normalized.collection,
            "status": product.status.value,
            "has_stock": has_stock,
        }
        self.qdrant.upsert_product(product.id, vector, payload, sparse_text=index_text)
        normalized.qdrant_point_id = str(product.id)
        normalized.embedding_model = self.settings.openai_embedding_model
        normalized.dense_vector_dim = len(vector)
        normalized.last_indexed_at = datetime.now(UTC)

        variant_point_ids: dict[str, str] = {}
        for variant in variants:
            variant_text = self._build_variant_text(product, normalized, variant)
            variant_vector = self.embeddings.embed_text(variant_text)
            variant_payload = {
                **payload,
                "variant_id": str(variant.id),
                "sku": variant.sku,
                "color": variant.color,
                "size": variant.size,
                "normalized_color": variant.normalized_color,
                "normalized_size": variant.normalized_size,
                "has_stock": variant.available_stock > 0,
            }
            self.qdrant.upsert_variant(variant.id, variant_vector, variant_payload, sparse_text=variant_text)
            variant_point_ids[str(variant.id)] = str(variant.id)
        normalized.qdrant_variant_point_ids = variant_point_ids
        self.normalized_repo.commit()

    @staticmethod
    def _build_index_text(product: Product, normalized, variants) -> str:
        colors = sorted({v.color for v in variants if v.color})
        sizes = sorted({v.size for v in variants if v.size})
        aliases = normalized.synonym_candidates[:20]
        parts = [
            normalized.normalized_title,
            product.description or "",
            f"brand: {normalized.brand or ''}",
            f"collection: {normalized.collection or ''}",
            f"gender: {normalized.gender or ''}",
            f"colors: {', '.join(colors)}",
            f"sizes: {', '.join(sizes)}",
            f"aliases: {', '.join(aliases)}",
        ]
        return "\n".join(part for part in parts if part.strip())

    @staticmethod
    def _build_variant_text(product: Product, normalized, variant) -> str:
        return "\n".join(
            part
            for part in [
                normalized.normalized_title,
                variant.sku,
                variant.color,
                variant.size,
                normalized.brand,
            ]
            if part
        )

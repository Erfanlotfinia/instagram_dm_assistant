from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.models import Product, ProductVariant, User
from app.integrations.openai_client import LiveOpenAIEmbeddingClient, OpenAIEmbeddingClient
from app.integrations.qdrant_client import LiveQdrantClient, QdrantClient
from app.repositories.product_repository import ProductRepository
from app.schemas.agent import SemanticSearchHit, SemanticSearchRequest, SemanticSearchResponse
from app.services.shop_service import ShopService

logger = logging.getLogger(__name__)

EMBEDDING_VECTOR_SIZE = 8


class ProductSemanticSearchService:
    def __init__(
        self,
        db: Session,
        qdrant_client: QdrantClient | None = None,
        embedding_client: OpenAIEmbeddingClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.products = ProductRepository(db)
        self.shop_service = ShopService(db)
        self.qdrant = qdrant_client or LiveQdrantClient(self.settings)
        self.embeddings = embedding_client or LiveOpenAIEmbeddingClient(self.settings)

    def index_product(self, product: Product, variants: list[ProductVariant], caption: str | None = None) -> None:
        text = self._build_index_text(product, variants, caption)
        vector = self.embeddings.embed_text(text)
        self.qdrant.ensure_collection(len(vector))
        self.qdrant.upsert_product(
            product.id,
            vector,
            {
                "title": product.title,
                "description": product.description,
                "shop_id": str(product.shop_id),
            },
        )
        logger.info("Indexed product %s in Qdrant", product.id)

    def search_for_shop(
        self,
        shop_id: UUID,
        payload: SemanticSearchRequest,
        user: User,
    ) -> SemanticSearchResponse:
        self.shop_service.get_shop(shop_id, user)
        vector = self.embeddings.embed_text(payload.query)
        self.qdrant.ensure_collection(len(vector))
        hits = self.qdrant.search(vector, payload.limit)

        response_hits: list[SemanticSearchHit] = []
        for hit in hits:
            product = self.products.get_for_shop(shop_id, hit.product_id)
            if product is None:
                continue
            response_hits.append(
                SemanticSearchHit(
                    product_id=product.id,
                    title=product.title,
                    score=hit.score,
                    description=product.description,
                )
            )
        return SemanticSearchResponse(query=payload.query, hits=response_hits)

    def search_internal(self, shop_id: UUID, query: str, limit: int = 3) -> list[SemanticSearchHit]:
        vector = self.embeddings.embed_text(query)
        self.qdrant.ensure_collection(len(vector))
        hits = self.qdrant.search(vector, limit)
        results: list[SemanticSearchHit] = []
        for hit in hits:
            product = self.products.get_for_shop(shop_id, hit.product_id)
            if product is None:
                continue
            results.append(
                SemanticSearchHit(
                    product_id=product.id,
                    title=product.title,
                    score=hit.score,
                    description=product.description,
                )
            )
        return results

    @staticmethod
    def _build_index_text(
        product: Product,
        variants: list[ProductVariant],
        caption: str | None,
    ) -> str:
        colors = sorted({variant.color for variant in variants if variant.color})
        sizes = sorted({variant.size for variant in variants if variant.size})
        parts = [
            product.title,
            product.description or "",
            f"colors: {', '.join(colors)}",
            f"sizes: {', '.join(sizes)}",
        ]
        if caption:
            parts.append(f"caption: {caption}")
        return "\n".join(part for part in parts if part)

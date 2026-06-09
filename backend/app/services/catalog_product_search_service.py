from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.models import MediaProductLink, User
from app.integrations.openai_client import LiveOpenAIEmbeddingClient, OpenAIEmbeddingClient
from app.integrations.qdrant_client import LiveQdrantClient, QdrantClient
from app.repositories.catalog_repository import ProductAliasRepository, ProductNormalizedRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.resolve import ProductCandidate, ResolveProductRequest, ResolveProductResponse
from app.services.resolver_confidence_service import ResolverConfidenceService
from app.services.resolver_trace_service import ResolverTraceService
from app.services.shop_service import ShopService


class CatalogProductSearchService:
    """Hybrid Qdrant retrieval with alias matching and business reranking."""

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
        self.normalized_repo = ProductNormalizedRepository(db)
        self.alias_repo = ProductAliasRepository(db)
        self.qdrant = qdrant_client or LiveQdrantClient(self.settings)
        self.embeddings = embedding_client or LiveOpenAIEmbeddingClient(self.settings)
        self.confidence = ResolverConfidenceService(db, self.settings)
        self.trace_service = ResolverTraceService(db)

    def resolve_product(self, payload: ResolveProductRequest, user: User) -> ResolveProductResponse:
        self.shop_service.get_shop(payload.shop_id, user)
        query = payload.message_text.strip()
        rules_fired: list[str] = []
        matched_aliases: list[dict] = []
        missing_slots: list[str] = []

        media_product_id = self._resolve_media(payload.shop_id, payload.media_references)
        if media_product_id:
            rules_fired.append("media_product_link")
            product = self.products.get_for_shop(payload.shop_id, media_product_id)
            if product:
                score = 0.95
                band = self.confidence.band_for_score(payload.shop_id, score)
                candidate = ProductCandidate(
                    product_id=product.id,
                    title=product.title,
                    score=score,
                    confidence_band=band.value,
                    rationale="Matched linked media reference",
                    matched_aliases=[],
                    rules_fired=rules_fired,
                )
                trace = self.trace_service.create_product_trace(
                    shop_id=payload.shop_id,
                    payload=payload,
                    candidates=[candidate.model_dump(mode="json")],
                    matched_aliases=matched_aliases,
                    rules_fired=rules_fired,
                    missing_slots=missing_slots,
                    confidence_score=score,
                    confidence_band=band,
                    rationale=candidate.rationale,
                    qdrant_metadata={"source": "media_link"},
                    conversation_id=payload.conversation_context.conversation_id if payload.conversation_context else None,
                )
                return ResolveProductResponse(
                    trace_id=trace.id,
                    query=query,
                    candidates=[candidate],
                    confidence_band=band.value,
                    confidence_score=score,
                    missing_slots=missing_slots,
                    rationale=candidate.rationale,
                )

        alias_hit = self._match_alias(payload.shop_id, query)
        alias_boost: dict[UUID, float] = {}
        if alias_hit:
            rules_fired.append("alias_exact_match")
            matched_aliases.append({"alias": alias_hit.alias_text, "product_id": str(alias_hit.product_id)})
            alias_boost[alias_hit.product_id] = 0.25

        vector = self.embeddings.embed_text(query)
        self.qdrant.ensure_collection(len(vector))
        fusion = payload.fusion_strategy or self.settings.hybrid_fusion_strategy
        hits = self.qdrant.hybrid_search(
            query_vector=vector,
            query_text=query,
            limit=payload.limit,
            shop_id=payload.shop_id,
            fusion_strategy=fusion,
            rrf_k=self.settings.hybrid_rrf_k,
            apply_rerank=True,
        )
        if not hits:
            missing_slots.append("product")
            band = self.confidence.band_for_score(payload.shop_id, 0.0)
            trace = self.trace_service.create_product_trace(
                shop_id=payload.shop_id,
                payload=payload,
                candidates=[],
                matched_aliases=matched_aliases,
                rules_fired=rules_fired,
                missing_slots=missing_slots,
                confidence_score=0.0,
                confidence_band=band,
                rationale="No catalog matches found",
                qdrant_metadata={"fusion": fusion, "hit_count": 0},
                conversation_id=payload.conversation_context.conversation_id if payload.conversation_context else None,
            )
            return ResolveProductResponse(
                trace_id=trace.id,
                query=query,
                candidates=[],
                confidence_band=band.value,
                confidence_score=0.0,
                missing_slots=missing_slots,
                rationale="No catalog matches found",
            )

        candidates: list[ProductCandidate] = []
        for hit in hits:
            product = self.products.get_for_shop(payload.shop_id, hit.entity_id)
            if product is None:
                continue
            score = min(hit.fused_score + alias_boost.get(hit.entity_id, 0.0), 1.0)
            band = self.confidence.band_for_score(payload.shop_id, score)
            rationale_parts = [f"Hybrid fusion score {score:.3f}"]
            if hit.payload.get("has_stock"):
                rules_fired.append("in_stock_boost")
                rationale_parts.append("in-stock boost applied")
            candidates.append(
                ProductCandidate(
                    product_id=product.id,
                    title=product.title,
                    score=score,
                    confidence_band=band.value,
                    rationale="; ".join(rationale_parts),
                    matched_aliases=[a["alias"] for a in matched_aliases if a.get("product_id") == str(product.id)],
                    rules_fired=list(dict.fromkeys(rules_fired)),
                )
            )

        top_score = candidates[0].score if candidates else 0.0
        top_band = self.confidence.band_for_score(payload.shop_id, top_score)
        trace = self.trace_service.create_product_trace(
            shop_id=payload.shop_id,
            payload=payload,
            candidates=[c.model_dump(mode="json") for c in candidates],
            matched_aliases=matched_aliases,
            rules_fired=list(dict.fromkeys(rules_fired)),
            missing_slots=missing_slots,
            confidence_score=top_score,
            confidence_band=top_band,
            rationale=candidates[0].rationale if candidates else None,
            qdrant_metadata={"fusion": fusion, "hit_count": len(hits)},
            conversation_id=payload.conversation_context.conversation_id if payload.conversation_context else None,
        )
        return ResolveProductResponse(
            trace_id=trace.id,
            query=query,
            candidates=candidates,
            confidence_band=top_band.value,
            confidence_score=top_score,
            missing_slots=missing_slots,
            rationale=candidates[0].rationale if candidates else None,
        )

    def _match_alias(self, shop_id: UUID, query: str):
        from sqlalchemy import select

        from app.domain.models import ProductAlias
        from app.services.catalog_normalization_service import CatalogNormalizationService

        cleaned = CatalogNormalizationService._normalize_alias(query)
        exact = self.alias_repo.find_by_alias(shop_id, cleaned)
        if exact:
            return exact
        stmt = select(ProductAlias).where(
            ProductAlias.shop_id == shop_id,
            ProductAlias.is_active.is_(True),
            ProductAlias.alias_text.ilike(f"%{cleaned[:32]}%"),
        )
        return self.db.scalar(stmt)

    def _resolve_media(self, shop_id: UUID, media_refs) -> UUID | None:
        from sqlalchemy import select

        for ref in media_refs:
            if not ref.media_id:
                continue
            stmt = (
                select(MediaProductLink)
                .where(
                    MediaProductLink.shop_id == shop_id,
                    MediaProductLink.media_id == ref.media_id,
                )
                .order_by(MediaProductLink.is_primary.desc())
            )
            link = self.db.scalar(stmt)
            if link:
                return link.product_id
        return None

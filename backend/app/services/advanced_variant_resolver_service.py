from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.models import Product, ProductAlias, User
from app.integrations.openai_client import LiveOpenAIEmbeddingClient, OpenAIEmbeddingClient
from app.integrations.qdrant_client import LiveQdrantClient, QdrantClient
from app.repositories.product_repository import ProductRepository
from app.repositories.resolver_repository import VariantAliasRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.resolve import ResolveVariantRequest, ResolveVariantResponse, VariantCandidate
from app.services.catalog_product_search_service import CatalogProductSearchService
from app.services.fashion_normalization import ColorNormalizer, SizeNormalizer, clean_fashion_text
from app.services.resolver_confidence_service import ResolverConfidenceService
from app.services.resolver_trace_service import ResolverTraceService
from app.services.shop_service import ShopService
from app.services.variant_resolver import VariantResolver


class AdvancedVariantResolverService:
    """Resolve variants from message text, media, candidates, and conversation context."""

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
        self.variant_aliases = VariantAliasRepository(db)
        self.base_resolver = VariantResolver(db)
        self.product_search = CatalogProductSearchService(db, qdrant_client, embedding_client, settings)
        self.confidence = ResolverConfidenceService(db, settings)
        self.trace_service = ResolverTraceService(db)
        self.color_normalizer = ColorNormalizer(db)
        self.size_normalizer = SizeNormalizer(db)
        self.qdrant = qdrant_client or LiveQdrantClient(self.settings)
        self.embeddings = embedding_client or LiveOpenAIEmbeddingClient(self.settings)

    def resolve_variant(self, payload: ResolveVariantRequest, user: User) -> ResolveVariantResponse:
        self.shop_service.get_shop(payload.shop_id, user)
        rules_fired: list[str] = []
        matched_aliases: list[dict] = []
        missing_slots: list[str] = []

        product_id = payload.product_id
        if product_id is None and payload.candidate_product_ids:
            product_id = payload.candidate_product_ids[0]
        if product_id is None:
            from app.schemas.resolve import ResolveProductRequest

            product_response = self.product_search.resolve_product(
                ResolveProductRequest(
                    shop_id=payload.shop_id,
                    message_text=payload.message_text,
                    media_references=payload.media_references,
                    conversation_context=payload.conversation_context,
                    limit=1,
                ),
                user,
            )
            if product_response.candidates:
                product_id = product_response.candidates[0].product_id
                rules_fired.append("product_inferred_from_message")

        if product_id is None:
            missing_slots.extend(["product", "variant"])
            band = self.confidence.band_for_score(payload.shop_id, 0.0)
            trace = self.trace_service.create_variant_trace(
                shop_id=payload.shop_id,
                payload=payload,
                candidates=[],
                matched_aliases=matched_aliases,
                rules_fired=rules_fired,
                missing_slots=missing_slots,
                confidence_score=0.0,
                confidence_band=band,
                rationale="Could not infer product",
                qdrant_metadata={},
                conversation_id=payload.conversation_context.conversation_id if payload.conversation_context else None,
            )
            return ResolveVariantResponse(
                trace_id=trace.id,
                product_id=None,
                candidates=[],
                confidence_band=band.value,
                confidence_score=0.0,
                missing_slots=missing_slots,
                rationale="Could not infer product",
            )

        product = self.products.get_for_shop(payload.shop_id, product_id)
        if product is None:
            missing_slots.append("product")
            band = self.confidence.band_for_score(payload.shop_id, 0.0)
            trace = self.trace_service.create_variant_trace(
                shop_id=payload.shop_id,
                payload=payload,
                candidates=[],
                matched_aliases=matched_aliases,
                rules_fired=rules_fired,
                missing_slots=missing_slots,
                confidence_score=0.0,
                confidence_band=band,
                rationale="Product not found in shop",
                qdrant_metadata={},
                conversation_id=payload.conversation_context.conversation_id if payload.conversation_context else None,
            )
            return ResolveVariantResponse(
                trace_id=trace.id,
                product_id=product_id,
                candidates=[],
                confidence_band=band.value,
                confidence_score=0.0,
                missing_slots=missing_slots,
                rationale="Product not found in shop",
            )

        raw_color, raw_size = self._extract_slots(payload)
        if not raw_color:
            missing_slots.append("color")
        if not raw_size:
            missing_slots.append("size")

        base_result = self.base_resolver.resolve(
            product_id=product_id,
            raw_color=raw_color,
            raw_size=raw_size,
            quantity=payload.quantity,
            shop_id=payload.shop_id,
            conversation_id=payload.conversation_context.conversation_id if payload.conversation_context else None,
        )

        candidates: list[VariantCandidate] = []
        if base_result.matched and base_result.variant_id:
            variant = self.variants.get_for_shop(payload.shop_id, base_result.variant_id)
            if variant:
                score = base_result.confidence
                band = self.confidence.band_for_score(payload.shop_id, score)
                rules_fired.append("deterministic_variant_match")
                candidates.append(
                    VariantCandidate(
                        variant_id=variant.id,
                        product_id=product_id,
                        sku=variant.sku,
                        color=variant.color,
                        size=variant.size,
                        normalized_color=base_result.normalized_color,
                        normalized_size=base_result.normalized_size,
                        available_stock=base_result.available_stock or variant.available_stock,
                        score=score,
                        confidence_band=band.value,
                        rationale="Exact color/size match with sufficient stock",
                        matched_aliases=[a["alias"] for a in matched_aliases],
                        rules_fired=list(dict.fromkeys(rules_fired)),
                    )
                )

        for alt in base_result.alternatives[: payload.limit]:
            score = 0.45 + (0.1 if "in_stock" in alt.reason else 0.0)
            band = self.confidence.band_for_score(payload.shop_id, score)
            candidates.append(
                VariantCandidate(
                    variant_id=alt.variant_id,
                    product_id=product_id,
                    sku=alt.sku,
                    color=alt.color,
                    size=alt.size,
                    normalized_color=alt.normalized_color,
                    normalized_size=alt.normalized_size,
                    available_stock=alt.available_stock,
                    score=score,
                    confidence_band=band.value,
                    rationale=alt.reason,
                    matched_aliases=[],
                    rules_fired=["alternative_ranking"],
                )
            )

        if not candidates:
            vector = self.embeddings.embed_text(payload.message_text)
            self.qdrant.ensure_variants_collection(len(vector))
            hits = self.qdrant.hybrid_search(
                query_vector=vector,
                query_text=payload.message_text,
                limit=payload.limit,
                shop_id=payload.shop_id,
                collection="variants",
                fusion_strategy=self.settings.hybrid_fusion_strategy,
                rrf_k=self.settings.hybrid_rrf_k,
                filters={"product_id": str(product_id)},
            )
            rules_fired.append("variant_hybrid_search")
            for hit in hits:
                variant = self.variants.get_for_shop(payload.shop_id, hit.entity_id)
                if variant is None:
                    continue
                score = min(hit.fused_score, 1.0)
                band = self.confidence.band_for_score(payload.shop_id, score)
                candidates.append(
                    VariantCandidate(
                        variant_id=variant.id,
                        product_id=product_id,
                        sku=variant.sku,
                        color=variant.color,
                        size=variant.size,
                        normalized_color=variant.normalized_color,
                        normalized_size=variant.normalized_size,
                        available_stock=variant.available_stock,
                        score=score,
                        confidence_band=band.value,
                        rationale=f"Hybrid variant search score {score:.3f}",
                        matched_aliases=[],
                        rules_fired=["variant_hybrid_search"],
                    )
                )

        candidates = candidates[: payload.limit]
        top_score = candidates[0].score if candidates else 0.0
        top_band = self.confidence.band_for_score(payload.shop_id, top_score)
        trace = self.trace_service.create_variant_trace(
            shop_id=payload.shop_id,
            payload=payload,
            candidates=[c.model_dump(mode="json") for c in candidates],
            matched_aliases=matched_aliases,
            rules_fired=list(dict.fromkeys(rules_fired)),
            missing_slots=missing_slots,
            confidence_score=top_score,
            confidence_band=top_band,
            rationale=candidates[0].rationale if candidates else None,
            qdrant_metadata={"candidate_count": len(candidates)},
            conversation_id=payload.conversation_context.conversation_id if payload.conversation_context else None,
        )
        return ResolveVariantResponse(
            trace_id=trace.id,
            product_id=product_id,
            candidates=candidates,
            confidence_band=top_band.value,
            confidence_score=top_score,
            missing_slots=missing_slots,
            rationale=candidates[0].rationale if candidates else None,
        )

    def _extract_slots(self, payload: ResolveVariantRequest) -> tuple[str | None, str | None]:
        raw_color = payload.raw_color
        raw_size = payload.raw_size
        if payload.conversation_context and payload.conversation_context.extracted_slots:
            raw_color = raw_color or payload.conversation_context.extracted_slots.get("color")
            raw_size = raw_size or payload.conversation_context.extracted_slots.get("size")
        if not raw_color or not raw_size:
            inferred_color, inferred_size = self._infer_from_message(payload.message_text)
            raw_color = raw_color or inferred_color
            raw_size = raw_size or inferred_size
        return raw_color, raw_size

    def _infer_from_message(self, message: str) -> tuple[str | None, str | None]:
        cleaned = clean_fashion_text(message) or message.casefold()
        size_match = re.search(r"\b(xs|s|m|l|xl|xxl|xxxl|36|38|40|42|free)\b", cleaned)
        raw_size = size_match.group(1).upper() if size_match else None
        color_tokens = ["black", "white", "red", "blue", "green", "مشکی", "سفید", "قرمز", "آبی", "سبز"]
        raw_color = next((token for token in color_tokens if token in cleaned), None)
        return raw_color, raw_size

    def _match_product_alias(self, shop_id: UUID, query: str) -> ProductAlias | None:
        cleaned = (clean_fashion_text(query) or query).casefold()
        stmt = select(ProductAlias).where(
            ProductAlias.shop_id == shop_id,
            ProductAlias.is_active.is_(True),
            ProductAlias.alias_text == cleaned,
        )
        return self.db.scalar(stmt)

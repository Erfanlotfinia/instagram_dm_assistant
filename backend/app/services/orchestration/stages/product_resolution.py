from __future__ import annotations

from typing import Any

from app.domain.models import Product
from app.schemas.instagram_product_map import ResolveInstagramProductRequest
from app.services.orchestration.base import Stage
from app.services.orchestration.context import CONTINUE, ConversationPipelineContext, StageOutcome
from app.services.orchestration.services import OrchestrationServices
from app.services.state_machine_service import match_variant


def resolve_product(
    services: OrchestrationServices,
    conversation,
    slots,
    shared_post_url: str | None,
    media_id: str | None,
    message_text: str | None,
) -> tuple[Product | None, str]:
    post_url = shared_post_url or slots.instagram_post_url
    if post_url or media_id:
        request = ResolveInstagramProductRequest(
            instagram_post_url=post_url,
            instagram_media_id=media_id,
        )
        resolved = services.product_resolver.resolve_internal(conversation.shop_id, request)
        if resolved.requires_product_selection:
            slots.product_candidates = [candidate.model_dump(mode="json") for candidate in resolved.candidates]
            return None, "instagram_map_multi_product"
        if resolved.product is not None:
            product = services.products.get_for_shop(conversation.shop_id, resolved.product.id)
            slots.product_candidates = [candidate.model_dump(mode="json") for candidate in resolved.candidates]
            return product, "instagram_map"

    query = message_text or post_url or ""
    if query.strip():
        hits = services.semantic_search.search_internal(conversation.shop_id, query, limit=1)
        if hits:
            product = services.products.get_for_shop(conversation.shop_id, hits[0].product_id)
            if product is not None:
                return product, "qdrant_semantic"

    return None, "unresolved"


def resolve_variant(services: OrchestrationServices, product: Product | None, slots):
    if product is None:
        return None, None, None
    result = services.variant_resolver.resolve(
        shop_id=product.shop_id,
        product_id=product.id,
        raw_color=slots.color,
        raw_size=slots.size,
        quantity=slots.quantity or 1,
    )
    variants = services.variants.list_for_product(product.id)
    variant_match = match_variant(
        variants, result.normalized_color or slots.color, result.normalized_size or slots.size
    )
    variant = services.variants.get_by_id(result.variant_id) if result.variant_id else variant_match.variant
    return variant, variant_match, result


def product_context(
    services: OrchestrationServices, product: Product | None
) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    if product is None:
        return None, [], []
    variants = services.variants.list_for_product(product.id)
    colors = sorted({variant.color for variant in variants if variant.color})
    sizes = sorted({variant.size for variant in variants if variant.size})
    info = {
        "id": str(product.id),
        "title": product.title,
        "description": product.description,
        "base_price": str(product.base_price),
        "currency": product.currency,
    }
    return info, colors, sizes


class ProductResolutionStage(Stage):
    """Deterministic product + product-context resolution.

    Variant resolution is deferred to the slot-merge stage because it depends on
    the slots merged from the LLM extraction.
    """

    def run(self, ctx: ConversationPipelineContext) -> StageOutcome:
        services = self.services
        conversation = ctx.conversation
        slots = ctx.slots

        product, resolve_source = resolve_product(
            services,
            conversation,
            slots,
            ctx.shared_post_url,
            ctx.media_id,
            ctx.message.text,
        )
        product_info, valid_colors, valid_sizes = product_context(services, product)

        ctx.resolution.product = product
        ctx.resolution.resolve_source = resolve_source
        ctx.resolution.product_info = product_info
        ctx.resolution.valid_colors = valid_colors
        ctx.resolution.valid_sizes = valid_sizes
        return CONTINUE

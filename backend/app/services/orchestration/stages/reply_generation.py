from __future__ import annotations

from app.services.orchestration.base import Stage
from app.services.orchestration.context import CONTINUE, ConversationPipelineContext, StageOutcome
from app.services.response_generation_service import ReplyFacts
from app.services.slot_merge_service import slots_to_dict


class ReplyGenerationStage(Stage):
    """Deterministic reply generation + state-transition / generate-reply action logs."""

    def run(self, ctx: ConversationPipelineContext) -> StageOutcome:
        services = self.services
        conversation = ctx.conversation
        slots = ctx.slots
        extraction = ctx.extraction
        resolution = ctx.resolution
        product = resolution.product
        variant = resolution.variant
        variant_match = resolution.variant_match
        active_order = ctx.active_order
        upsell_text = ctx.upsell_text

        reply = services.response_service.generate(
            ReplyFacts(
                intent=extraction.intent,
                workflow_state=conversation.workflow_state,
                product=product,
                variant=variant,
                slots=slots,
                missing_fields=slots.missing_fields,
                valid_colors=resolution.valid_colors,
                valid_sizes=resolution.valid_sizes,
                available_stock=(
                    variant.stock_quantity - variant.reserved_quantity if variant else None
                ),
                handoff_reason=conversation.handoff_reason,
                invalid_color=bool(variant_match and variant_match.invalid_color),
                invalid_size=bool(variant_match and variant_match.invalid_size),
                style_hint=extraction.reply_style_hint,
                payment_url=ctx.payment_url,
                order_total=(
                    str(active_order.total_amount) if active_order is not None else None
                ),
                order_currency=active_order.currency if active_order is not None else None,
                upsell_text=upsell_text,
                size_confirmation_needed=ctx.size_confirmation_needed,
            )
        )
        if upsell_text and reply and upsell_text not in reply:
            reply = f"{reply}\n\n{upsell_text}"
        ctx.reply = reply

        services.log_action(
            ctx.conversation_id,
            "state_transition",
            {
                "previous_state": ctx.extraction_input.workflow_state.value,
                "next_state": conversation.workflow_state.value,
                "resolve_source": resolution.resolve_source,
            },
            {"missing_fields": slots.missing_fields},
            confidence=extraction.confidence.intent,
        )
        services.log_action(
            ctx.conversation_id,
            "generate_reply",
            {"facts": slots_to_dict(slots)},
            {"reply": reply},
            confidence=extraction.confidence.slots,
        )
        return CONTINUE

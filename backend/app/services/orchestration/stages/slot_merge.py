from __future__ import annotations

from app.core.metric_labels import HandoffMetricReason
from app.core.metrics import record_handoff
from app.domain.enums import AgentWorkflowState, ConversationState
from app.services.agent_settings_live import resolve_live_agent_settings
from app.services.customer_preferences_service import CustomerPreferencesService
from app.services.handoff_service import evaluate_handoff
from app.services.orchestration.base import Stage
from app.services.orchestration.context import CONTINUE, ConversationPipelineContext, StageOutcome
from app.services.orchestration.stages.product_resolution import resolve_variant
from app.services.slot_merge_service import compute_missing_fields, merge_extracted_slots
from app.services.state_machine_service import check_inventory, decide_next_state


class SlotMergeStage(Stage):
    """Merge extracted slots, resolve the variant, and decide the next workflow state."""

    def run(self, ctx: ConversationPipelineContext) -> StageOutcome:
        services = self.services
        conversation = ctx.conversation
        slots = ctx.slots
        extraction = ctx.extraction
        product = ctx.resolution.product

        merge_extracted_slots(slots, extraction)

        prefs_service = CustomerPreferencesService(services.db)
        size_confirmation_needed = False
        if prefs_service.detect_same_size_request(ctx.message.text) and conversation.customer_id:
            suggested_size, size_confidence, size_confirmation_needed = (
                prefs_service.resolve_size_from_preferences(conversation.customer_id)
            )
            if suggested_size and not slots.size:
                slots.size = suggested_size
                if size_confirmation_needed:
                    slots.missing_fields = list(set(slots.missing_fields or []) | {"size_confirmation"})
        ctx.size_confirmation_needed = size_confirmation_needed
        if product is not None:
            slots.product_id = product.id

        variant, variant_match, variant_result = resolve_variant(services, product, slots)
        slots.normalized_color = variant_result.normalized_color if variant_result else slots.normalized_color
        slots.normalized_size = variant_result.normalized_size if variant_result else slots.normalized_size
        slots.variant_alternatives = [
            a.model_dump(mode="json")
            for a in (variant_result.available_alternatives if variant_result else [])
        ]
        if variant is not None:
            slots.product_variant_id = variant.id
        elif variant_match and (variant_match.invalid_color or variant_match.invalid_size):
            slots.product_variant_id = None

        inventory_available = None
        if variant is not None:
            inventory_available = check_inventory(variant, slots.quantity)

        ctx.resolution.variant = variant
        ctx.resolution.variant_match = variant_match
        ctx.resolution.variant_result = variant_result
        ctx.resolution.inventory_available = inventory_available

        live_agent_settings = resolve_live_agent_settings(conversation.shop)
        ctx.live_agent_settings = live_agent_settings
        # Missing or unavailable variants are recoverable: the agent should ask the
        # customer for the missing detail or offer alternatives (WAITING_FOR_VARIANT),
        # not escalate to a human. Only flag a true mismatch when the customer supplied
        # both color and size yet the requested combination is genuinely unresolvable.
        real_variant_mismatch = bool(
            variant_result
            and slots.color
            and slots.size
            and [
                reason
                for reason in variant_result.mismatch_reasons
                if not reason.startswith("missing_")
            ]
            and not variant_result.available_alternatives
        )
        handoff = evaluate_handoff(
            extraction,
            failure_count=conversation.agent_failure_count,
            settings=services.settings,
            variant_mismatch=real_variant_mismatch,
            order_total=None,
            shop_settings=live_agent_settings,
        )
        ctx.handoff = handoff

        state_decision = decide_next_state(
            conversation.workflow_state,
            extraction.intent,
            slots,
            product_resolved=product is not None,
            variant_resolved=variant is not None,
            inventory_available=inventory_available,
            needs_human=handoff.required,
        )

        if variant_match and (variant_match.invalid_color or variant_match.invalid_size):
            state_decision.next_state = AgentWorkflowState.WAITING_FOR_VARIANT
            state_decision.missing_fields = compute_missing_fields(slots, require_variant=True)
        ctx.state_decision = state_decision

        slots.missing_fields = state_decision.missing_fields
        conversation.workflow_state = state_decision.next_state
        conversation.last_intent = extraction.intent.value

        if handoff.required:
            conversation.handoff_required = True
            conversation.handoff_reason = handoff.reason
            conversation.workflow_state = AgentWorkflowState.HUMAN_HANDOFF
            conversation.state = ConversationState.PENDING_HANDOFF
            record_handoff(conversation.channel_provider, HandoffMetricReason.POLICY)
        return CONTINUE

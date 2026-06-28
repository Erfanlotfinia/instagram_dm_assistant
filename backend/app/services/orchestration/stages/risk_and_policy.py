from __future__ import annotations

from app.domain.enums import AgentIntent, AgentWorkflowState, ConversationState
from app.services.agent_risk_scoring_service import AgentRiskScoringInput
from app.services.auto_send_decision_service import AutoSendDecisionInput, AutoSendDecisionService
from app.services.orchestration.base import Stage
from app.services.orchestration.context import CONTINUE, ConversationPipelineContext, StageOutcome
from app.services.pilot_service import PilotService


class RiskAndPolicyStage(Stage):
    """Risk scoring, first auto-send decision, emergency stop, pilot + trust write gates."""

    def run(self, ctx: ConversationPipelineContext) -> StageOutcome:
        services = self.services
        conversation = ctx.conversation
        slots = ctx.slots
        extraction = ctx.extraction
        product = ctx.resolution.product
        variant = ctx.resolution.variant
        variant_match = ctx.resolution.variant_match
        inventory_available = ctx.resolution.inventory_available

        active_order = services.order_service.orders.get_active_for_conversation(ctx.conversation_id)
        ctx.active_order = active_order
        estimated_order_value = services.estimated_order_value(active_order, variant, slots)
        settings_row = services.get_or_create_agent_settings(conversation.shop_id)
        risk_settings = services.risk_settings(settings_row)
        risk_score = services.risk_scoring.score(
            AgentRiskScoringInput(
                intent_confidence=extraction.confidence.intent,
                slot_confidence=extraction.confidence.slots,
                product_confidence=extraction.confidence.product,
                variant_confidence=extraction.confidence.variant or extraction.confidence.slots,
                address_confidence=extraction.confidence.address,
                order_value=estimated_order_value,
                customer_history=services.customer_history(conversation),
                message_text=ctx.message.text,
                previous_failed_attempts=conversation.agent_failure_count,
                unavailable_variant=bool(variant_match and (variant_match.invalid_color or variant_match.invalid_size)) or inventory_available is False,
                payment_related_message=services.is_payment_related(ctx.message.text),
                complaint_flag=services.is_complaint(ctx.message.text),
                settings=risk_settings,
            )
        )
        if risk_score.requires_handoff:
            conversation.handoff_required = True
            conversation.handoff_reason = ";".join(risk_score.risk_reasons) or "Risk policy requires handoff"
            conversation.workflow_state = AgentWorkflowState.HUMAN_HANDOFF
            conversation.state = ConversationState.PENDING_HANDOFF
        decision = AutoSendDecisionService().decide(
            AutoSendDecisionInput(
                settings=settings_row,
                intent_confidence=extraction.confidence.intent,
                product_confidence=extraction.confidence.product,
                variant_confidence=extraction.confidence.slots,
                address_confidence=extraction.confidence.address,
                order_value=estimated_order_value,
                is_first_order=services.is_first_customer_order(conversation),
                handoff_reason=conversation.handoff_reason if conversation.handoff_required else None,
                message_risk="simulation" if conversation.is_simulation and not services.allow_simulated_order_side_effects else None,
            )
        )
        combined_reasons = [*decision.reasons, *risk_score.risk_reasons]
        preview_reason = ";".join(combined_reasons) if combined_reasons else None
        conversation.preview_required = decision.requires_preview or risk_score.requires_preview
        conversation.preview_reason = preview_reason
        if decision.requires_handoff or risk_score.requires_handoff:
            conversation.handoff_required = True
            conversation.workflow_state = AgentWorkflowState.HUMAN_HANDOFF
            conversation.state = ConversationState.PENDING_HANDOFF

        ctx.payment_url = None
        pilot_service = PilotService(services.db)
        ctx.pilot_service = pilot_service
        # --- SIDE EFFECT BOUNDARY: emergency stop blocks order side effects ---
        if pilot_service.is_emergency_stop_active(conversation.shop_id) and not conversation.is_simulation:
            services.log_action(
                ctx.conversation_id,
                "order_side_effects_blocked",
                {"intent": extraction.intent.value, "reason": "emergency_stop"},
                {"reasons": ["pilot_emergency_stop_enabled"]},
                confidence=extraction.confidence.intent,
            )
            conversation.preview_required = True
            conversation.preview_reason = "pilot_emergency_stop_enabled"
            conversation.suggested_outbound = None
        # --- END SIDE EFFECT BOUNDARY ---
        pilot_order_allowed, pilot_order_reasons = pilot_service.enforce_order_allowed(
            conversation.shop_id, product.id if product is not None else None
        )
        base_order_side_effects_allowed = (
            decision.auto_send_allowed
            and not risk_score.requires_preview
            and not risk_score.requires_handoff
            and (not conversation.is_simulation or services.allow_simulated_order_side_effects)
            and not pilot_service.is_emergency_stop_active(conversation.shop_id)
        )
        draft_order_candidate = (
            product is not None
            and variant is not None
            and services.order_service.can_create_draft(slots, variant)
        )
        write_trust = services.evaluate_trust_layer(
            conversation=conversation,
            pilot_service=pilot_service,
            extraction=extraction,
            handoff_required=conversation.handoff_required,
            variant=variant,
            inventory_available=inventory_available,
            draft_order_candidate=draft_order_candidate,
            would_auto_send=False,
        )
        ctx.policy_eval = write_trust["policy_eval"]
        ctx.operating_mode = write_trust["operating_mode"]
        trust_write_allowed = write_trust["trust_write_allowed"]
        trust_reasons = list(write_trust["reasons"])
        if trust_reasons:
            combined_reasons.extend(trust_reasons)
            preview_reason = ";".join(combined_reasons)
            conversation.preview_required = True
            conversation.preview_reason = preview_reason
        pilot_order_blocks_progression = (
            bool(pilot_order_reasons)
            and base_order_side_effects_allowed
            and (extraction.intent == AgentIntent.CANCEL_ORDER or draft_order_candidate)
        )
        pilot_order_preview_reasons = list(pilot_order_reasons) if pilot_order_blocks_progression else []
        if pilot_order_preview_reasons:
            combined_reasons.extend(pilot_order_preview_reasons)
            preview_reason = ";".join(combined_reasons)
            conversation.preview_required = True
            conversation.preview_reason = preview_reason
        order_side_effects_allowed = (
            base_order_side_effects_allowed and pilot_order_allowed and trust_write_allowed
        )

        ctx.combined_reasons = combined_reasons
        ctx.preview_reason = preview_reason
        ctx.risk.settings_row = settings_row
        ctx.risk.estimated_order_value = estimated_order_value
        ctx.risk.risk_score = risk_score
        ctx.risk.decision = decision
        ctx.side_effects.base_order_side_effects_allowed = base_order_side_effects_allowed
        ctx.side_effects.draft_order_candidate = draft_order_candidate
        ctx.side_effects.pilot_order_allowed = pilot_order_allowed
        ctx.side_effects.pilot_order_reasons = pilot_order_reasons
        ctx.side_effects.pilot_order_preview_reasons = pilot_order_preview_reasons
        ctx.side_effects.trust_write_allowed = trust_write_allowed
        ctx.side_effects.order_side_effects_allowed = order_side_effects_allowed
        return CONTINUE

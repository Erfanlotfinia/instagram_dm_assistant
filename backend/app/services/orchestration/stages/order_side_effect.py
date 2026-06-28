from __future__ import annotations

import logging

from app.core.metrics import record_order_created
from app.domain.enums import AgentIntent, AgentWorkflowState
from app.services.audit_service import AuditService
from app.services.orchestration.base import Stage
from app.services.orchestration.context import CONTINUE, ConversationPipelineContext, StageOutcome
from app.services.upsell_service import UpsellService

logger = logging.getLogger(__name__)


class OrderSideEffectStage(Stage):
    """Order create / cancel / confirm + payment initiation.

    This is the primary state-changing boundary of the pipeline. Every write here
    is gated by ``order_side_effects_allowed`` computed in the risk/policy stage,
    which already folds in auto-send, risk, simulation, emergency-stop, pilot, and
    trust-layer decisions.
    """

    def run(self, ctx: ConversationPipelineContext) -> StageOutcome:
        services = self.services
        conversation = ctx.conversation
        slots = ctx.slots
        extraction = ctx.extraction
        product = ctx.resolution.product
        variant = ctx.resolution.variant
        variant_match = ctx.resolution.variant_match
        inventory_available = ctx.resolution.inventory_available
        state_decision = ctx.state_decision
        handoff = ctx.handoff
        live_agent_settings = ctx.live_agent_settings
        order_side_effects_allowed = ctx.side_effects.order_side_effects_allowed
        draft_order_candidate = ctx.side_effects.draft_order_candidate
        active_order = ctx.active_order

        # --- SIDE EFFECT BOUNDARY: order create / cancel ---
        if order_side_effects_allowed and extraction.intent == AgentIntent.CANCEL_ORDER:
            active_order = services.order_service.cancel_active_for_conversation(
                ctx.conversation_id,
                reason="Customer cancelled via chat",
            )
        elif (
            order_side_effects_allowed
            and product is not None
            and variant is not None
            and draft_order_candidate
        ):
            existing_order = services.order_service.orders.get_active_for_conversation(conversation.id)
            active_order = services.order_service.upsert_draft_from_conversation(
                conversation, slots, product, variant
            )
            order_was_created = active_order is not None and existing_order is None  # noqa: F841
            if active_order is not None:
                record_order_created(conversation.channel_provider)
                AuditService(services.db).log(action="pilot_auto_order_created", entity_type="order", shop_id=conversation.shop_id, entity_id=str(active_order.id), metadata={"conversation_id": str(conversation.id)})
                high_value_threshold = float(live_agent_settings.get("high_value_order_threshold", 500.0))
                preview_high_value_orders = live_agent_settings.get("preview_required_for_high_value_order", True)
                if (
                    preview_high_value_orders
                    and high_value_threshold > 0
                    and float(active_order.total_amount) >= high_value_threshold
                ):
                    risk_flags = list(active_order.risk_flags or [])
                    if "high_value_order" not in risk_flags:
                        risk_flags.append("high_value_order")
                    active_order.risk_flags = risk_flags
                    active_order.approval_source = "operator_required"
        elif not order_side_effects_allowed:
            services.log_action(
                ctx.conversation_id,
                "order_side_effects_blocked",
                {"intent": extraction.intent.value},
                {"reasons": ctx.combined_reasons},
                confidence=extraction.confidence.intent,
            )
        # --- END SIDE EFFECT BOUNDARY ---

        # --- SIDE EFFECT BOUNDARY: order confirmation + payment initiation ---
        if (
            order_side_effects_allowed
            and extraction.intent == AgentIntent.CONFIRM_ORDER
            and active_order is not None
            and state_decision.next_state == AgentWorkflowState.WAITING_FOR_PAYMENT
            and not handoff.required
        ):
            try:
                confirmed = services.order_service.confirm_after_customer(active_order)
                payment = services.payment_service.initiate_payment(confirmed)
                ctx.payment_url = payment.payment_url
                active_order = confirmed
                services.log_action(
                    ctx.conversation_id,
                    "create_payment",
                    {"order_id": str(confirmed.id)},
                    {"payment_id": str(payment.id), "payment_url": ctx.payment_url},
                    confidence=None,
                )
            except Exception as exc:
                logger.warning("Order confirmation failed conversation=%s: %s", ctx.conversation_id, exc)
                conversation.workflow_state = AgentWorkflowState.WAITING_FOR_CONFIRMATION
                if variant_match and (variant_match.invalid_color or variant_match.invalid_size):
                    conversation.workflow_state = AgentWorkflowState.WAITING_FOR_VARIANT
                elif inventory_available is False:
                    conversation.workflow_state = AgentWorkflowState.WAITING_FOR_VARIANT
                    slots.missing_fields = ["stock"]
        # --- END SIDE EFFECT BOUNDARY ---

        upsell_text: str | None = None
        if (
            product is not None
            and active_order is not None
            and conversation.workflow_state
            in {
                AgentWorkflowState.WAITING_FOR_CONFIRMATION,
                AgentWorkflowState.WAITING_FOR_PAYMENT,
            }
        ):
            suggestion = UpsellService(services.db).maybe_suggest_upsell(
                shop_id=conversation.shop_id,
                conversation_id=conversation.id,
                order=active_order,
                source_product_id=product.id,
                intent_confidence=extraction.confidence.intent,
                handoff_required=conversation.handoff_required,
                workflow_clear=variant is not None and not slots.missing_fields,
            )
            if suggestion and suggestion.status.value == "suggested":
                upsell_text = suggestion.suggested_text

        ctx.active_order = active_order
        ctx.upsell_text = upsell_text
        return CONTINUE

from __future__ import annotations

from decimal import Decimal

from app.domain.enums import AgentWorkflowState, ConversationState
from app.services.audit_service import AuditService
from app.services.auto_send_decision_service import AutoSendDecisionInput, AutoSendDecisionService
from app.services.channel_outbound_service import agent_run_outbound_key
from app.services.orchestration.base import Stage
from app.services.orchestration.context import CONTINUE, ConversationPipelineContext, StageOutcome
from app.services.pilot_service import PilotService
from app.services.suggested_reply_service import SuggestedReplyService


class SendOrSuggestStage(Stage):
    """Second auto-send decision + the auto-send vs suggested-reply branch.

    This is the real provider-send boundary. Auto-send only happens when the
    deterministic auto-send decision, risk score, pilot limits, trust gates,
    simulation flag, and emergency stop all permit it; otherwise a suggested reply
    is created for operator preview.
    """

    def run(self, ctx: ConversationPipelineContext) -> StageOutcome:
        services = self.services
        conversation = ctx.conversation
        message = ctx.message
        extraction = ctx.extraction
        reply = ctx.reply
        agent_run = ctx.agent_run
        variant = ctx.resolution.variant
        inventory_available = ctx.resolution.inventory_available
        active_order = ctx.active_order
        risk_score = ctx.risk.risk_score
        pilot_service = ctx.pilot_service
        pilot_order_preview_reasons = ctx.side_effects.pilot_order_preview_reasons

        settings_row = services.get_or_create_agent_settings(conversation.shop_id)
        decision = AutoSendDecisionService().decide(
            AutoSendDecisionInput(
                settings=settings_row,
                intent_confidence=extraction.confidence.intent,
                product_confidence=extraction.confidence.product,
                variant_confidence=extraction.confidence.slots,
                address_confidence=extraction.confidence.address,
                order_value=Decimal(active_order.total_amount) if active_order is not None else Decimal("0"),
                is_first_order=services.is_first_customer_order(conversation),
                handoff_reason=conversation.handoff_reason if conversation.handoff_required else None,
                message_risk="simulation" if conversation.is_simulation and not services.allow_simulated_order_side_effects else None,
            )
        )
        combined_reasons = [*decision.reasons, *risk_score.risk_reasons, *pilot_order_preview_reasons]
        preview_reason = ";".join(combined_reasons) if combined_reasons else None
        force_preview = decision.requires_preview or risk_score.requires_preview or bool(pilot_order_preview_reasons)
        conversation.preview_required = force_preview
        conversation.preview_reason = preview_reason
        conversation.suggested_outbound = reply if force_preview else None
        if decision.requires_handoff or risk_score.requires_handoff:
            conversation.handoff_required = True
            conversation.workflow_state = AgentWorkflowState.HUMAN_HANDOFF
            conversation.state = ConversationState.PENDING_HANDOFF

        services.log_action(
            ctx.conversation_id,
            "auto_send_decision",
            {"reply": reply},
            {
                "auto_send_allowed": decision.auto_send_allowed,
                "requires_preview": decision.requires_preview,
                "requires_handoff": decision.requires_handoff,
                "reasons": combined_reasons,
                "risk_score": risk_score.model_dump(),
            },
            confidence=extraction.confidence.intent,
        )
        outbound = None
        pilot_send_allowed, pilot_send_reasons = PilotService(services.db).enforce_auto_send_allowed(
            conversation.shop_id, conversation.instagram_account_id
        )
        if pilot_send_reasons:
            combined_reasons.extend(pilot_send_reasons)
            preview_reason = ";".join(combined_reasons)
            force_preview = True
            conversation.preview_required = True
            conversation.preview_reason = preview_reason
            conversation.suggested_outbound = reply
        send_trust = services.evaluate_trust_layer(
            conversation=conversation,
            pilot_service=pilot_service,
            extraction=extraction,
            handoff_required=conversation.handoff_required,
            variant=variant,
            inventory_available=inventory_available,
            draft_order_candidate=False,
            would_auto_send=decision.auto_send_allowed and not force_preview and not risk_score.requires_handoff,
        )
        trust_send_allowed = send_trust["trust_send_allowed"]
        if send_trust["reasons"]:
            combined_reasons.extend(send_trust["reasons"])
            preview_reason = ";".join(combined_reasons)
            force_preview = True
            conversation.preview_required = True
            conversation.preview_reason = preview_reason
            conversation.suggested_outbound = reply
        # --- SIDE EFFECT BOUNDARY: real provider auto-send vs suggested reply ---
        if (
            decision.auto_send_allowed
            and not force_preview
            and not risk_score.requires_handoff
            and pilot_send_allowed
            and trust_send_allowed
            and not conversation.is_simulation
            and not pilot_service.is_emergency_stop_active(conversation.shop_id)
        ):
            outbound = services.send_service.send_text_message(
                ctx.conversation_id,
                reply,
                commit=False,
                is_simulation=False,
                idempotency_key=agent_run_outbound_key(agent_run.id),
            )
            AuditService(services.db).log(action="message_auto_sent", entity_type="conversation", shop_id=conversation.shop_id, entity_id=str(conversation.id), metadata={"message_id": str(outbound.id)})
            services.log_action(ctx.conversation_id, "send_outbound", {"reply": reply}, {"message_id": str(outbound.id)}, confidence=None)
        else:
            SuggestedReplyService(services.db).create_agent_suggestion(
                shop_id=conversation.shop_id,
                conversation_id=conversation.id,
                message_id=message.id,
                text=reply,
                reason=preview_reason,
                is_simulation=conversation.is_simulation,
            )
            action = "handoff_required" if (decision.requires_handoff or risk_score.requires_handoff) else "message_blocked_due_to_confidence" if force_preview else "suggested_reply_created"
            AuditService(services.db).log(action=action, entity_type="conversation", shop_id=conversation.shop_id, entity_id=str(conversation.id), metadata={"reasons": combined_reasons})
            services.log_action(ctx.conversation_id, "preview_outbound", {"reply": reply}, {"preview_required": force_preview, "reason": preview_reason, "simulation": conversation.is_simulation}, confidence=extraction.confidence.intent)
        # --- END SIDE EFFECT BOUNDARY ---

        ctx.combined_reasons = combined_reasons
        ctx.preview_reason = preview_reason
        ctx.outbound = outbound
        ctx.reply_decision.decision = decision
        ctx.reply_decision.force_preview = force_preview
        ctx.reply_decision.pilot_send_allowed = pilot_send_allowed
        ctx.reply_decision.pilot_send_reasons = pilot_send_reasons
        ctx.reply_decision.trust_send_allowed = trust_send_allowed
        return CONTINUE

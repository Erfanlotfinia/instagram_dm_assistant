from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.core.log_masking import redact_value
from app.domain.enums import PilotOperatingMode, TraceEventType
from app.domain.models import (
    AgentDecisionAudit,
    AgentDecisionTrace,
    AgentRun,
    Conversation,
    Message,
    Order,
    Product,
    ProductVariant,
)
from app.schemas.agent import AgentExtractionResult
from app.services.conversation_priority_service import ConversationPriorityService
from app.services.orchestration.base import Stage
from app.services.orchestration.context import ConversationPipelineContext, StageOutcome, stop_with
from app.services.slot_merge_service import slots_to_dict

logger = logging.getLogger(__name__)


class TraceAndAuditStage(Stage):
    """Persist decision trace + audit, reset failure counter, save slots, commit."""

    def run(self, ctx: ConversationPipelineContext) -> StageOutcome:
        services = self.services
        conversation = ctx.conversation
        message = ctx.message
        slots = ctx.slots
        extraction = ctx.extraction
        resolution = ctx.resolution
        product = resolution.product
        variant = resolution.variant
        variant_result = resolution.variant_result
        inventory_available = resolution.inventory_available
        handoff = ctx.handoff
        state_decision = ctx.state_decision
        risk_score = ctx.risk.risk_score
        decision = ctx.reply_decision.decision
        outbound = ctx.outbound

        self._create_decision_trace(
            trace_id=ctx.trace_id,
            conversation=conversation,
            message=message,
            agent_run=ctx.agent_run,
            extraction=extraction,
            slots=slots,
            product=product,
            variant_result=variant_result,
            inventory_available=inventory_available,
            risk_score=risk_score.model_dump(),
            decision=decision,
            order=ctx.active_order,
            reply=ctx.reply,
            outbound_message_id=outbound.id if outbound is not None else None,
            handoff_reason=conversation.handoff_reason,
            policy_eval=ctx.policy_eval,
            operating_mode=ctx.operating_mode,
        )
        self._record_trust_trace_events(
            trace_id=ctx.trace_id,
            conversation=conversation,
            extraction=extraction,
            slots=slots,
            product=product,
            variant=variant,
            policy_eval=ctx.policy_eval,
            outbound_created=outbound is not None,
        )

        self._audit_decision(
            conversation=conversation,
            message=message,
            extraction=extraction,
            slots=slots,
            product=product,
            variant_result=variant_result,
            inventory_available=inventory_available,
            reply=ctx.reply,
            reason=handoff.reason or state_decision.next_state.value,
        )

        if not ctx.extraction_error and not handoff.required:
            conversation.agent_failure_count = 0

        services.slots_repo.save(slots)
        ConversationPriorityService(services.db).refresh(ctx.conversation_id)
        services.db.commit()
        logger.info(
            "Orchestrator processed conversation=%s message=%s run=%s state=%s",
            ctx.conversation_id,
            ctx.message_id,
            ctx.agent_run.id,
            conversation.workflow_state.value,
        )
        return stop_with(ctx.extraction_error is None)

    def _create_decision_trace(
        self,
        *,
        trace_id: UUID,
        conversation: Conversation,
        message: Message,
        agent_run: AgentRun,
        extraction: AgentExtractionResult,
        slots,
        product: Product | None,
        variant_result,
        inventory_available: bool | None,
        risk_score: dict[str, Any],
        decision,
        order: Order | None,
        reply: str,
        outbound_message_id: UUID | None,
        handoff_reason: str | None,
        policy_eval=None,
        operating_mode: PilotOperatingMode | None = None,
    ) -> None:
        selected_variant_id = getattr(variant_result, "variant_id", None) if variant_result else None
        enriched_risk = {
            **risk_score,
            "operating_mode": operating_mode.value if operating_mode else None,
            "policy_evaluation": (
                {
                    "allowed": policy_eval.allowed,
                    "checks": [check.__dict__ for check in policy_eval.checks],
                    "blocked_actions": policy_eval.blocked_actions,
                }
                if policy_eval is not None
                else None
            ),
        }
        self.services.db.add(AgentDecisionTrace(
            id=trace_id,
            conversation_id=conversation.id,
            message_id=message.id,
            agent_run_id=agent_run.id,
            intent=extraction.intent.value,
            extracted_slots=redact_value(extraction.slots.model_dump(mode="json")),
            normalized_slots=redact_value(slots_to_dict(slots)),
            product_candidates=getattr(slots, "product_candidates", []) or [],
            selected_product_id=product.id if product is not None else None,
            variant_resolution=variant_result.model_dump(mode="json") if variant_result else {"variant_id": str(selected_variant_id) if selected_variant_id else None},
            inventory_result={"available": inventory_available},
            risk_score=redact_value(enriched_risk),
            order_action={"order_id": str(order.id) if order else None, "status": order.status.value if order else None},
            next_state=conversation.workflow_state.value,
            outbound_message_id=outbound_message_id,
            auto_send_allowed=bool(decision.auto_send_allowed and not risk_score.get("requires_preview") and not risk_score.get("requires_handoff")),
            human_handoff_required=bool(conversation.handoff_required),
            reasoning_summary=(handoff_reason or ";".join(risk_score.get("risk_reasons", [])) or "Deterministic state and safety gates evaluated"),
        ))

    def _record_trust_trace_events(
        self,
        *,
        trace_id: UUID,
        conversation: Conversation,
        extraction: AgentExtractionResult,
        slots,
        product: Product | None,
        variant: ProductVariant | None,
        policy_eval,
        outbound_created: bool,
    ) -> None:
        services = self.services
        services.trace_service.record(
            trace_id=trace_id,
            shop_id=conversation.shop_id,
            event_type=TraceEventType.RETRIEVAL_EVIDENCE,
            payload={
                "product_resolved": product is not None,
                "variant_resolved": variant is not None,
                "resolve_source": "orchestrator",
            },
            conversation_id=conversation.id,
        )
        services.trace_service.record(
            trace_id=trace_id,
            shop_id=conversation.shop_id,
            event_type=TraceEventType.SLOTS_EXTRACTED,
            payload={"slots": slots_to_dict(slots)},
            conversation_id=conversation.id,
        )
        services.trace_service.record(
            trace_id=trace_id,
            shop_id=conversation.shop_id,
            event_type=TraceEventType.CONFIDENCE_BAND,
            payload={
                "intent_band": services.policy_engine.confidence_band(extraction.confidence.intent),
                "scores": {
                    "intent": extraction.confidence.intent,
                    "product": extraction.confidence.product,
                    "variant": extraction.confidence.variant or extraction.confidence.slots,
                },
            },
            conversation_id=conversation.id,
        )
        if policy_eval is not None:
            services.trace_service.record_policy_checks(
                trace_id=trace_id,
                shop_id=conversation.shop_id,
                checks=[check.__dict__ for check in policy_eval.checks],
                conversation_id=conversation.id,
            )
            if policy_eval.allowed and outbound_created:
                services.trace_service.record(
                    trace_id=trace_id,
                    shop_id=conversation.shop_id,
                    event_type=TraceEventType.ACTION_ATTEMPTED,
                    payload={"actions": ["auto_send", "process_inbound_message"]},
                    conversation_id=conversation.id,
                )
            elif not policy_eval.allowed or not outbound_created:
                blocked = list(policy_eval.blocked_actions)
                if not outbound_created:
                    blocked.append("auto_send_blocked")
                services.trace_service.record(
                    trace_id=trace_id,
                    shop_id=conversation.shop_id,
                    event_type=TraceEventType.ACTION_BLOCKED,
                    payload={"blocked_actions": blocked},
                    conversation_id=conversation.id,
                )

    def _audit_decision(
        self,
        *,
        conversation: Conversation,
        message: Message,
        extraction: AgentExtractionResult,
        slots,
        product: Product | None,
        variant_result,
        inventory_available: bool | None,
        reply: str,
        reason: str,
    ) -> None:
        self.services.db.add(AgentDecisionAudit(
            shop_id=conversation.shop_id,
            conversation_id=conversation.id,
            message_id=message.id,
            input_message=message.text,
            extracted_intent=extraction.intent.value,
            extracted_slots=slots_to_dict(slots),
            product_candidates=getattr(slots, "product_candidates", []) or [],
            chosen_product_id=product.id if product is not None else None,
            variant_resolver_result=variant_result.model_dump(mode="json") if variant_result else {},
            inventory_result={"available": inventory_available},
            next_state=conversation.workflow_state.value,
            outbound_message=reply,
            confidence=extraction.confidence.intent,
            decision_reason=reason,
        ))

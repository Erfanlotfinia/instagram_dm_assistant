from __future__ import annotations

import logging
from uuid import UUID

from app.core.metric_labels import HandoffMetricReason
from app.core.metrics import record_handoff
from app.domain.enums import AgentWorkflowState, ConversationState
from app.domain.models import Conversation, Message
from app.services.audit_service import AuditService
from app.services.channel_outbound_service import inbound_message_outbound_key
from app.services.conversation_priority_service import ConversationPriorityService
from app.services.orchestration.base import Stage
from app.services.orchestration.context import (
    CONTINUE,
    ConversationPipelineContext,
    StageOutcome,
    stop_with,
)
from app.services.pilot_service import PilotService
from app.services.social_admin.orchestrator import SocialAdminOrchestrator
from app.services.suggested_reply_service import SuggestedReplyService

logger = logging.getLogger(__name__)


class SocialAdminAutomationStage(Stage):
    """Automation-first social admin layer; short-circuits the legacy LLM path."""

    def run(self, ctx: ConversationPipelineContext) -> StageOutcome:
        services = self.services
        conversation = ctx.conversation
        message = ctx.message
        slots = ctx.slots

        skip_social_admin = bool(
            ctx.shared_post_url
            or ctx.media_id
            or slots.instagram_post_url
            or conversation.workflow_state != AgentWorkflowState.IDLE
        )
        if not skip_social_admin and self._try_social_admin_automation(
            conversation, message, ctx.conversation_id, ctx.message_id, ctx.trace_id
        ):
            ConversationPriorityService(services.db).refresh(ctx.conversation_id)
            services.db.commit()
            return stop_with(True)
        return CONTINUE

    def _try_social_admin_automation(
        self,
        conversation: Conversation,
        message: Message,
        conversation_id: UUID,
        message_id: UUID,
        trace_id: UUID,
    ) -> bool:
        """Automation-first social admin layer; returns True if legacy LLM path should be skipped."""
        services = self.services
        pilot_service = PilotService(services.db)
        if pilot_service.is_emergency_stop_active(conversation.shop_id) and not conversation.is_simulation:
            return False

        result = SocialAdminOrchestrator(services.db, settings=services.settings).try_handle(
            conversation_id,
            message_id,
            trace_id=trace_id,
        )
        if result.status == "fallback_legacy":
            return False

        reply = result.response_text or ""
        if result.status == "needs_human":
            conversation.handoff_required = True
            conversation.handoff_reason = result.handoff_reason or "social_admin_handoff"
            conversation.workflow_state = AgentWorkflowState.HUMAN_HANDOFF
            conversation.state = ConversationState.PENDING_HANDOFF
            record_handoff(conversation.channel_provider, HandoffMetricReason.SOCIAL_ADMIN)
            if reply:
                SuggestedReplyService(services.db).create_agent_suggestion(
                    shop_id=conversation.shop_id,
                    conversation_id=conversation.id,
                    message_id=message.id,
                    text=reply,
                    reason=result.handoff_reason,
                    is_simulation=conversation.is_simulation,
                )
            services.log_action(
                conversation_id,
                "social_admin_handoff",
                {"message": message.text},
                {"reason": result.handoff_reason, "handler": result.decision.handler if result.decision else None},
                confidence=result.decision.confidence if result.decision else None,
            )
            return True

        if result.status in {"handled", "needs_clarification"} and reply:
            # --- SIDE EFFECT BOUNDARY: social admin outbound send vs suggestion ---
            pilot_send_allowed, _ = pilot_service.enforce_auto_send_allowed(
                conversation.shop_id, conversation.instagram_account_id
            )
            can_auto_send = (
                pilot_send_allowed
                and not conversation.is_simulation
                and not pilot_service.is_emergency_stop_active(conversation.shop_id)
            )
            if can_auto_send:
                outbound = services.send_service.send_text_message(
                    conversation_id,
                    reply,
                    commit=False,
                    is_simulation=False,
                    idempotency_key=inbound_message_outbound_key(message_id),
                )
                AuditService(services.db).log(
                    action="message_auto_sent",
                    entity_type="conversation",
                    shop_id=conversation.shop_id,
                    entity_id=str(conversation.id),
                    metadata={"message_id": str(outbound.id), "source": "social_admin"},
                )
                services.log_action(
                    conversation_id,
                    "social_admin_send_outbound",
                    {"reply": reply},
                    {"message_id": str(outbound.id)},
                    confidence=result.decision.confidence if result.decision else None,
                )
            else:
                conversation.suggested_outbound = reply
                SuggestedReplyService(services.db).create_agent_suggestion(
                    shop_id=conversation.shop_id,
                    conversation_id=conversation.id,
                    message_id=message.id,
                    text=reply,
                    reason="social_admin_automation",
                    is_simulation=conversation.is_simulation,
                )
            # --- END SIDE EFFECT BOUNDARY ---
            services.log_action(
                conversation_id,
                "social_admin_handled",
                {"message": message.text},
                {
                    "handler": result.decision.handler if result.decision else None,
                    "scenario": result.decision.scenario_code if result.decision else None,
                    "status": result.status,
                },
                confidence=result.decision.confidence if result.decision else None,
            )
            return True

        return False

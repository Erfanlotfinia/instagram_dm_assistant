from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import TraceEventType
from app.domain.models import Order
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.order_repository import OrderRepository
from app.services.decision_trace_service import DecisionTraceService
from app.services.social_admin.context_graph import ConversationContextService
from app.services.social_admin.handlers import (
    AutomationHandlerRegistry,
    HandlerContext,
    HandlerResult,
)
from app.services.social_admin.human_handoff_service import HumanHandoffService
from app.services.social_admin.llm_fallback_orchestrator import LLMFallbackOrchestrator
from app.services.social_admin.scenario_router import ScenarioDecision, ScenarioRouter


@dataclass
class SocialAdminResult:
    status: str
    response_text: str | None = None
    handoff_reason: str | None = None
    decision: ScenarioDecision | None = None
    handler_result: HandlerResult | None = None
    trace_metadata: dict[str, Any] = field(default_factory=dict)


class SocialAdminOrchestrator:
    def __init__(
        self,
        db: Session,
        *,
        settings: Settings | None = None,
        context_service: ConversationContextService | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)
        self.orders = OrderRepository(db)
        self.trace_service = DecisionTraceService(db)
        self.context_service = context_service or ConversationContextService(db)
        self.router = ScenarioRouter(self.context_service)
        self.handlers = AutomationHandlerRegistry(db, self.context_service, settings=self.settings)
        self.llm_fallback = LLMFallbackOrchestrator()
        self.handoff_service = HumanHandoffService(db)

    def try_handle(
        self,
        conversation_id: UUID,
        message_id: UUID,
        *,
        trace_id: UUID | None = None,
    ) -> SocialAdminResult:
        conversation = self.conversations.get_by_id(conversation_id)
        message = self.messages.get_by_id(message_id)
        if conversation is None or message is None:
            return SocialAdminResult(status="fallback_legacy")

        active_order = self.orders.get_active_for_conversation(conversation_id)
        message_payload = {
            "text": message.text or "",
            "button_id": getattr(message, "button_id", None),
            "payload": getattr(message, "payload_json", None),
        }
        raw_payload = message.raw_payload if hasattr(message, "raw_payload") else {}

        decision = self.router.route(
            message_payload,
            conversation_context={"conversation_id": str(conversation_id)},
            active_order={"id": str(active_order.id)} if active_order else None,
            shop_id=str(conversation.shop_id),
            conversation_id=str(conversation_id),
            raw_provider_payload=raw_payload or {},
        )

        trace_id = trace_id or self.trace_service.new_trace_id()
        self.trace_service.record(
            trace_id=trace_id,
            shop_id=conversation.shop_id,
            conversation_id=conversation_id,
            event_type=TraceEventType.ACTION_ATTEMPTED,
            payload={
                "action": "scenario_routed",
                "scenario_code": decision.scenario_code,
                "handler": decision.handler,
                "confidence": decision.confidence,
                "requires_llm": decision.requires_llm,
                "requires_handoff": decision.requires_handoff,
                "reasons": decision.reasons,
            },
        )

        if decision.requires_handoff:
            reason = decision.reasons[0] if decision.reasons else "handoff_required"
            self.handoff_service.trigger(conversation_id, reason)
            return SocialAdminResult(
                status="needs_human",
                handoff_reason=reason,
                decision=decision,
                trace_metadata={"trace_id": str(trace_id), "route": "scenario_router"},
            )

        if decision.requires_llm:
            return SocialAdminResult(status="fallback_legacy", decision=decision)

        handler_ctx = HandlerContext(
            shop_id=conversation.shop_id,
            conversation_id=conversation_id,
            message_id=message_id,
            message_text=message.text or "",
            provider=str(
                message.channel.value if hasattr(message.channel, "value") else message.channel
            ),
            raw_provider_payload=raw_payload or {},
            active_order=active_order,
            is_simulation=conversation.is_simulation,
        )
        handler_result = self.handlers.dispatch(decision.handler, handler_ctx)

        self.trace_service.record(
            trace_id=trace_id,
            shop_id=conversation.shop_id,
            conversation_id=conversation_id,
            event_type=TraceEventType.ACTION_ATTEMPTED,
            payload={
                "action": "handler_executed",
                "handler": decision.handler,
                "status": handler_result.status,
                "llm_used": handler_result.audit_metadata.get("llm_used", False),
            },
        )

        if handler_result.status == "needs_human":
            self.handoff_service.trigger(
                conversation_id, handler_result.handoff_reason or "handler_requested_handoff"
            )
            return SocialAdminResult(
                status="needs_human",
                handoff_reason=handler_result.handoff_reason,
                decision=decision,
                handler_result=handler_result,
                trace_metadata={"trace_id": str(trace_id)},
            )
        if handler_result.status == "needs_clarification":
            return SocialAdminResult(
                status="needs_clarification",
                response_text=handler_result.response_text,
                decision=decision,
                handler_result=handler_result,
                trace_metadata={"trace_id": str(trace_id)},
            )
        if handler_result.status == "handled":
            return SocialAdminResult(
                status="handled",
                response_text=handler_result.response_text,
                decision=decision,
                handler_result=handler_result,
                trace_metadata={"trace_id": str(trace_id)},
            )

        return SocialAdminResult(status="fallback_legacy", decision=decision)

    def route_message(
        self,
        message: dict[str, Any],
        *,
        shop_id: str,
        conversation_id: str,
        provider: str = "unknown",
        active_order: Any = None,
        raw_provider_payload: dict[str, Any] | None = None,
    ) -> tuple[ScenarioDecision, HandlerResult | None]:
        """Lightweight routing for regression tests without full DB message records."""
        decision = self.router.route(
            message,
            active_order=active_order,
            shop_id=shop_id,
            conversation_id=conversation_id,
            raw_provider_payload=raw_provider_payload,
        )
        if decision.requires_llm or decision.requires_handoff:
            return decision, None
        handler_ctx = HandlerContext(
            shop_id=UUID(shop_id),
            conversation_id=UUID(conversation_id),
            message_text=message.get("text", ""),
            provider=provider,
            raw_provider_payload=raw_provider_payload or {},
            active_order=active_order if isinstance(active_order, Order) else None,
            is_simulation=True,
        )
        handler_result = self.handlers.dispatch(decision.handler, handler_ctx)
        return decision, handler_result

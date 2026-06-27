from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.enums import AgentActionStatus, AgentIntent, PilotOperatingMode
from app.domain.models import (
    AgentAction,
    Conversation,
    Order,
    ProductVariant,
    ShopAgentSettings,
)
from app.repositories.agent_action_repository import AgentActionRepository
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.conversation_slots_repository import ConversationSlotsRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.policy_version_repository import PolicyVersionRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.agent import AgentExtractionResult
from app.services.agent_risk_scoring_service import AgentRiskScoringService
from app.services.channel_outbound_service import ChannelOutboundService
from app.services.decision_trace_service import DecisionTraceService
from app.services.instagram_product_resolver import InstagramProductResolver
from app.services.llm_extraction_service import LLMExtractionProtocol, LLMExtractionService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.pilot_mode_service import PilotModeService
from app.services.pilot_service import PilotService
from app.services.policy_engine import PolicyEngine, PolicyEvaluationContext, merge_policy_config
from app.services.product_semantic_search_service import (
    InternalSemanticSearch,
    ProductSemanticSearchService,
)
from app.services.response_generation_service import ResponseGenerationService
from app.services.variant_resolver import VariantResolver


@dataclass
class OrchestrationServices:
    """Shared collaborators and cross-stage helpers for the pipeline.

    Holds references to the very same repository/service instances created by
    ``ConversationOrchestrator.__init__`` so that no behavior or wiring changes.
    Cross-cutting helpers used by more than one stage are kept here; stage-local
    helpers live on the stages themselves.
    """

    db: Session
    settings: Settings
    conversations: ConversationRepository
    messages: MessageRepository
    slots_repo: ConversationSlotsRepository
    agent_runs: AgentRunRepository
    agent_actions: AgentActionRepository
    products: ProductRepository
    variants: VariantRepository
    product_resolver: InstagramProductResolver
    variant_resolver: VariantResolver
    send_service: ChannelOutboundService
    response_service: ResponseGenerationService
    order_service: OrderService
    payment_service: PaymentService
    risk_scoring: AgentRiskScoringService
    policy_engine: PolicyEngine
    trace_service: DecisionTraceService
    llm_service: LLMExtractionProtocol | LLMExtractionService
    semantic_search: ProductSemanticSearchService | InternalSemanticSearch
    allow_simulated_order_side_effects: bool = False

    # ------------------------------------------------------------------
    # Cross-stage helpers (moved verbatim from ConversationOrchestrator)
    # ------------------------------------------------------------------
    def log_action(
        self,
        conversation_id: UUID,
        action_name: str,
        input_json: dict[str, Any],
        output_json: dict[str, Any],
        confidence: float | None,
    ) -> None:
        self.agent_actions.create(
            AgentAction(
                conversation_id=conversation_id,
                action_name=action_name,
                input_json=input_json,
                output_json=output_json,
                confidence=confidence,
                status=AgentActionStatus.SUCCESS,
            )
        )

    def get_or_create_agent_settings(self, shop_id: UUID) -> ShopAgentSettings:
        settings = self.db.get(ShopAgentSettings, shop_id)
        if settings is None:
            settings = ShopAgentSettings(shop_id=shop_id)
            self.db.add(settings)
            self.db.flush()
        return settings

    def is_first_customer_order(self, conversation: Conversation) -> bool:
        if conversation.customer_id is None:
            return True
        order_count = self.db.query(Order).filter(Order.customer_id == conversation.customer_id).count()
        return order_count <= 1

    def estimated_order_value(
        self, active_order: Order | None, variant: ProductVariant | None, slots
    ) -> Decimal:
        values: list[Decimal] = []
        if active_order is not None:
            values.append(Decimal(active_order.total_amount))
        if variant is not None:
            quantity = slots.quantity or 1
            values.append(Decimal(str(variant.price)) * Decimal(quantity))
        return max(values, default=Decimal("0"))

    def customer_history(self, conversation: Conversation) -> dict[str, Any]:
        if conversation.customer_id is None:
            return {"first_order": True}
        order_count = self.db.query(Order).filter(Order.customer_id == conversation.customer_id).count()
        return {"order_count": order_count, "first_order": order_count == 0}

    def risk_settings(self, settings: ShopAgentSettings) -> dict[str, Any]:
        return {
            "intent_confidence_threshold": float(settings.confidence_threshold_intent),
            "slot_confidence_threshold": float(settings.confidence_threshold_variant),
            "product_confidence_threshold": float(settings.confidence_threshold_product),
            "variant_confidence_threshold": float(settings.confidence_threshold_variant),
            "address_confidence_threshold": float(settings.confidence_threshold_address),
            "high_value_order_threshold": str(settings.high_value_order_threshold),
            **(settings.risk_policy_json or {}),
        }

    @staticmethod
    def is_payment_related(text: str | None) -> bool:
        """Detect payment *problems/disputes*, which warrant escalation.

        A bare mention of payment (e.g. "send the payment link" while confirming an
        order) is a normal request to proceed, not a dispute, so it must not trigger a
        payment-dispute handoff.
        """
        lowered = (text or "").lower()
        dispute_terms = (
            "payment failed", "charged twice", "charged", "refund", "chargeback",
            "پول کم شد", "پرداخت نشد", "پرداخت کردم", "مغایرت",
        )
        if any(term in lowered for term in dispute_terms):
            return True
        has_payment = any(term in lowered for term in ("payment", "پرداخت", "پول"))
        has_problem = any(
            term in lowered
            for term in ("fail", "problem", "issue", "wrong", "مشکل", "خطا", "اشتباه", "کم شد", "نشد")
        )
        return has_payment and has_problem

    @staticmethod
    def is_complaint(text: str | None) -> bool:
        lowered = (text or "").lower()
        return any(term in lowered for term in ("angry", "complaint", "furious", "شکایت", "ناراضی", "خراب"))

    def should_enforce_trust_gates(self, conversation: Conversation) -> bool:
        return not (conversation.is_simulation and self.allow_simulated_order_side_effects)

    @staticmethod
    def derive_policy_action_name(extraction: AgentExtractionResult, draft_order_candidate: bool) -> str | None:
        if extraction.intent == AgentIntent.CONFIRM_ORDER:
            return "confirm"
        if draft_order_candidate:
            return "create_draft"
        if extraction.intent == AgentIntent.CANCEL_ORDER:
            return "cancel"
        return None

    def evaluate_trust_layer(
        self,
        *,
        conversation: Conversation,
        pilot_service: PilotService,
        extraction: AgentExtractionResult,
        handoff_required: bool,
        variant: ProductVariant | None,
        inventory_available: bool | None,
        draft_order_candidate: bool,
        would_auto_send: bool,
    ) -> dict[str, Any]:
        pilot_settings = pilot_service.get_or_create_settings(conversation.shop_id)
        operating_mode = PilotModeService(self.db).resolve_operating_mode(pilot_settings)
        policy_version = PolicyVersionRepository(self.db).get_active(conversation.shop_id)
        policy_config = merge_policy_config(policy_version.config_json if policy_version else None)
        emergency_stop = pilot_service.is_emergency_stop_active(conversation.shop_id)
        stock_reserved = bool(variant and inventory_available is not False)
        action_name = self.derive_policy_action_name(extraction, draft_order_candidate)
        requires_write = bool(action_name or would_auto_send)

        policy_eval = self.policy_engine.evaluate(
            PolicyEvaluationContext(
                shop_id=conversation.shop_id,
                operating_mode=operating_mode,
                intent_confidence=extraction.confidence.intent,
                product_confidence=extraction.confidence.product,
                variant_confidence=extraction.confidence.variant or extraction.confidence.slots,
                customer_confirmed=extraction.intent == AgentIntent.CONFIRM_ORDER,
                stock_reserved=stock_reserved,
                within_messaging_window=True,
                action_name=action_name,
                requires_write=requires_write,
                handoff_required=handoff_required,
                emergency_stop=emergency_stop,
            ),
            policy_config,
        )

        trust_write_allowed = True
        trust_send_allowed = True
        reasons: list[str] = []
        enforce = pilot_settings.pilot_enabled and self.should_enforce_trust_gates(conversation)

        if enforce:
            if operating_mode == PilotOperatingMode.SHADOW and requires_write:
                trust_write_allowed = False
                trust_send_allowed = False
                reasons.append("shadow_mode_no_state_change")
            elif operating_mode == PilotOperatingMode.COPILOT:
                if action_name:
                    trust_write_allowed = False
                    reasons.append("copilot_requires_operator_approval")
                if would_auto_send:
                    trust_send_allowed = False
                    reasons.append("copilot_requires_operator_approval")
            elif operating_mode == PilotOperatingMode.AUTONOMOUS_LOW_RISK:
                if action_name and not PolicyEngine.autonomous_allowed(policy_eval, operating_mode):
                    trust_write_allowed = False
                    reasons.extend(policy_eval.blocked_actions)
                if would_auto_send and not policy_eval.allowed:
                    trust_send_allowed = False
                    reasons.extend(policy_eval.blocked_actions)

        return {
            "policy_eval": policy_eval,
            "operating_mode": operating_mode,
            "trust_write_allowed": trust_write_allowed,
            "trust_send_allowed": trust_send_allowed,
            "reasons": reasons,
        }

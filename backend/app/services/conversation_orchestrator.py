from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.metrics import CREATED_ORDERS, FAILED_AGENT_RUNS, HANDOFF_COUNT
from app.domain.enums import (
    AgentActionStatus,
    AgentIntent,
    AgentRunStatus,
    AgentWorkflowState,
    ConversationEventType,
    ConversationState,
    PilotOperatingMode,
    TraceEventType,
)
from app.domain.models import AgentAction, AgentDecisionAudit, AgentDecisionTrace, AgentRun, Conversation, Message, Order, Product, ProductVariant, ShopAgentSettings
from app.integrations.openai_client import LiveOpenAIChatClient, OpenAIChatClient
from app.integrations.qdrant_client import LiveQdrantClient, QdrantClient
from app.repositories.agent_action_repository import AgentActionRepository
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.conversation_slots_repository import ConversationSlotsRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.policy_version_repository import PolicyVersionRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.agent import AgentExtractionInput, AgentExtractionResult, ExtractionConfidence
from app.schemas.instagram_product_map import ResolveInstagramProductRequest
from app.services.agent_settings_live import resolve_live_agent_settings
from app.services.audit_service import AuditService
from app.services.conversation_event_service import ConversationEventService
from app.services.conversation_priority_service import ConversationPriorityService
from app.services.customer_preferences_service import CustomerPreferencesService
from app.services.auto_send_decision_service import AutoSendDecisionInput, AutoSendDecisionService
from app.services.decision_trace_service import DecisionTraceService
from app.services.handoff_service import evaluate_handoff
from app.services.instagram_product_resolver import InstagramProductResolver
from app.services.instagram_send_service import InstagramSendService
from app.services.llm_extraction_service import LLMExtractionProtocol, LLMExtractionService, mask_sensitive_llm_output
from app.services.order_service import OrderService
from app.services.agent_risk_scoring_service import AgentRiskScoringInput, AgentRiskScoringService
from app.services.payment_service import PaymentService
from app.services.pilot_mode_service import PilotModeService
from app.services.pilot_service import PilotService
from app.services.policy_engine import PolicyEngine, PolicyEvaluationContext, merge_policy_config
from app.services.product_semantic_search_service import InternalSemanticSearch, ProductSemanticSearchService
from app.services.response_generation_service import ReplyFacts, ResponseGenerationService
from app.services.suggested_reply_service import SuggestedReplyService
from app.services.upsell_service import UpsellService
from app.services.variant_resolver import VariantResolver
from app.services.slot_merge_service import compute_missing_fields, merge_extracted_slots, slots_to_dict
from app.services.state_machine_service import (
    check_inventory,
    decide_next_state,
    match_variant,
)

logger = logging.getLogger(__name__)


class ConversationOrchestrator:
    def __init__(
        self,
        db: Session,
        *,
        llm_service: LLMExtractionProtocol | None = None,
        semantic_search: InternalSemanticSearch | None = None,
        chat_client: OpenAIChatClient | None = None,
        qdrant_client: QdrantClient | None = None,
        settings: Settings | None = None,
        allow_simulated_order_side_effects: bool = False,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.conversations = ConversationRepository(db)
        self.messages = MessageRepository(db)
        self.slots_repo = ConversationSlotsRepository(db)
        self.agent_runs = AgentRunRepository(db)
        self.agent_actions = AgentActionRepository(db)
        self.products = ProductRepository(db)
        self.variants = VariantRepository(db)
        self.product_resolver = InstagramProductResolver(db)
        self.variant_resolver = VariantResolver(db)
        self.send_service = InstagramSendService(db, self.settings)
        self.response_service = ResponseGenerationService()
        self.order_service = OrderService(db, settings=self.settings)
        self.payment_service = PaymentService(db, settings=self.settings)
        self.risk_scoring = AgentRiskScoringService()
        self.policy_engine = PolicyEngine()
        self.trace_service = DecisionTraceService(db)
        self.allow_simulated_order_side_effects = allow_simulated_order_side_effects

        chat_client = chat_client or LiveOpenAIChatClient(self.settings)
        qdrant_client = qdrant_client or LiveQdrantClient(self.settings)
        self.llm_service = llm_service or LLMExtractionService(chat_client, self.settings)
        self.semantic_search = semantic_search or ProductSemanticSearchService(
            db,
            qdrant_client=qdrant_client,
            settings=self.settings,
        )

    def process_inbound_message(self, conversation_id: UUID, message_id: UUID) -> bool:
        conversation = self.conversations.get_by_id(conversation_id)
        if conversation is None:
            logger.warning("Conversation %s not found", conversation_id)
            return False

        message = self.messages.get_by_id(message_id)
        if message is None:
            logger.warning("Message %s not found", message_id)
            return False

        existing_run = self.agent_runs.get_by_input_message_id(message_id)
        if existing_run is not None:
            logger.info("Agent run already exists for message %s; skipping duplicate processing", message_id)
            self.db.commit()
            return True

        trace_id = self.trace_service.current_trace_id() or self.trace_service.bind_trace_context()
        policy_eval = None
        operating_mode: PilotOperatingMode | None = None

        ConversationEventService(self.db).record(
            conversation_id,
            ConversationEventType.INBOUND_MESSAGE,
            description=(message.text or "")[:200] or None,
            metadata={"message_id": str(message.id)},
        )
        if conversation.agent_paused or conversation.assigned_operator_id is not None:
            logger.info("Conversation %s is under human control; skipping agent", conversation_id)
            ConversationPriorityService(self.db).refresh(conversation_id)
            self.db.commit()
            return True

        slots = self.slots_repo.get_or_create(conversation_id)
        shared_post_url, media_id = self._extract_post_reference(message)

        product, resolve_source = self._resolve_product(
            conversation,
            slots,
            shared_post_url,
            media_id,
            message.text,
        )

        product_info, valid_colors, valid_sizes = self._product_context(product)
        extraction_input = AgentExtractionInput(
            message_text=message.text,
            shared_post_url=shared_post_url or slots.instagram_post_url,
            workflow_state=conversation.workflow_state,
            known_slots=slots_to_dict(slots),
            product_info=product_info,
            valid_colors=valid_colors,
            valid_sizes=valid_sizes,
        )

        extraction, extraction_error = self.llm_service.extract(extraction_input)
        agent_run = self._store_agent_run(
            conversation_id=conversation_id,
            message_id=message_id,
            extraction_input=extraction_input,
            extraction=extraction,
            error_message=extraction_error,
            is_simulation=conversation.is_simulation,
        )

        if extraction_error:
            conversation.agent_failure_count += 1

        merge_extracted_slots(slots, extraction)

        prefs_service = CustomerPreferencesService(self.db)
        size_confirmation_needed = False
        if prefs_service.detect_same_size_request(message.text) and conversation.customer_id:
            suggested_size, size_confidence, size_confirmation_needed = (
                prefs_service.resolve_size_from_preferences(conversation.customer_id)
            )
            if suggested_size and not slots.size:
                slots.size = suggested_size
                if size_confirmation_needed:
                    slots.missing_fields = list(set(slots.missing_fields or []) | {"size_confirmation"})
        if product is not None:
            slots.product_id = product.id

        variant, variant_match, variant_result = self._resolve_variant(product, slots)
        slots.normalized_color = variant_result.normalized_color if variant_result else slots.normalized_color
        slots.normalized_size = variant_result.normalized_size if variant_result else slots.normalized_size
        slots.variant_alternatives = [a.model_dump(mode="json") for a in (variant_result.available_alternatives if variant_result else [])]
        if variant is not None:
            slots.product_variant_id = variant.id
        elif variant_match and (variant_match.invalid_color or variant_match.invalid_size):
            slots.product_variant_id = None

        inventory_available = None
        if variant is not None:
            inventory_available = check_inventory(variant, slots.quantity)

        live_agent_settings = resolve_live_agent_settings(conversation.shop)
        handoff = evaluate_handoff(
            extraction,
            failure_count=conversation.agent_failure_count,
            settings=self.settings,
            variant_mismatch=bool(variant_result and variant_result.mismatch_reasons),
            order_total=None,
            shop_settings=live_agent_settings,
        )

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

        slots.missing_fields = state_decision.missing_fields
        conversation.workflow_state = state_decision.next_state
        conversation.last_intent = extraction.intent.value

        if handoff.required:
            conversation.handoff_required = True
            conversation.handoff_reason = handoff.reason
            conversation.workflow_state = AgentWorkflowState.HUMAN_HANDOFF
            conversation.state = ConversationState.PENDING_HANDOFF
            HANDOFF_COUNT.inc()

        active_order = self.order_service.orders.get_active_for_conversation(conversation_id)
        estimated_order_value = self._estimated_order_value(active_order, variant, slots)
        settings_row = self._get_or_create_agent_settings(conversation.shop_id)
        risk_settings = self._risk_settings(settings_row)
        risk_score = self.risk_scoring.score(
            AgentRiskScoringInput(
                intent_confidence=extraction.confidence.intent,
                slot_confidence=extraction.confidence.slots,
                product_confidence=extraction.confidence.product,
                variant_confidence=extraction.confidence.variant or extraction.confidence.slots,
                address_confidence=extraction.confidence.address,
                order_value=estimated_order_value,
                customer_history=self._customer_history(conversation),
                message_text=message.text,
                previous_failed_attempts=conversation.agent_failure_count,
                unavailable_variant=bool(variant_match and (variant_match.invalid_color or variant_match.invalid_size)) or inventory_available is False,
                payment_related_message=self._is_payment_related(message.text),
                complaint_flag=self._is_complaint(message.text),
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
                is_first_order=self._is_first_customer_order(conversation),
                handoff_reason=conversation.handoff_reason if conversation.handoff_required else None,
                message_risk="simulation" if conversation.is_simulation and not self.allow_simulated_order_side_effects else None,
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

        payment_url: str | None = None
        pilot_service = PilotService(self.db)
        if pilot_service.is_emergency_stop_active(conversation.shop_id) and not conversation.is_simulation:
            self._log_action(
                conversation_id,
                "order_side_effects_blocked",
                {"intent": extraction.intent.value, "reason": "emergency_stop"},
                {"reasons": ["pilot_emergency_stop_enabled"]},
                confidence=extraction.confidence.intent,
            )
            conversation.preview_required = True
            conversation.preview_reason = "pilot_emergency_stop_enabled"
            conversation.suggested_outbound = None
        pilot_order_allowed, pilot_order_reasons = pilot_service.enforce_order_allowed(
            conversation.shop_id, product.id if product is not None else None
        )
        base_order_side_effects_allowed = (
            decision.auto_send_allowed
            and not risk_score.requires_preview
            and not risk_score.requires_handoff
            and (not conversation.is_simulation or self.allow_simulated_order_side_effects)
            and not pilot_service.is_emergency_stop_active(conversation.shop_id)
        )
        draft_order_candidate = (
            product is not None
            and variant is not None
            and self.order_service.can_create_draft(slots, variant)
        )
        write_trust = self._evaluate_trust_layer(
            conversation=conversation,
            pilot_service=pilot_service,
            extraction=extraction,
            handoff_required=conversation.handoff_required,
            variant=variant,
            inventory_available=inventory_available,
            draft_order_candidate=draft_order_candidate,
            would_auto_send=False,
        )
        policy_eval = write_trust["policy_eval"]
        operating_mode = write_trust["operating_mode"]
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

        if order_side_effects_allowed and extraction.intent == AgentIntent.CANCEL_ORDER:
            active_order = self.order_service.cancel_active_for_conversation(
                conversation_id,
                reason="Customer cancelled via chat",
            )
        elif (
            order_side_effects_allowed
            and product is not None
            and variant is not None
            and draft_order_candidate
        ):
            existing_order = self.order_service.orders.get_active_for_conversation(conversation.id)
            active_order = self.order_service.upsert_draft_from_conversation(
                conversation, slots, product, variant
            )
            order_was_created = active_order is not None and existing_order is None
            if active_order is not None:
                CREATED_ORDERS.inc()
                AuditService(self.db).log(action="pilot_auto_order_created", entity_type="order", shop_id=conversation.shop_id, entity_id=str(active_order.id), metadata={"conversation_id": str(conversation.id)})
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
            if (
                active_order is not None
                and conversation.workflow_state == AgentWorkflowState.WAITING_FOR_PAYMENT
                and extraction.intent == AgentIntent.CONFIRM_ORDER
            ):
                try:
                    confirmed = self.order_service.confirm_after_customer(active_order)
                    payment = self.payment_service.initiate_payment(confirmed)
                    payment_url = payment.payment_url
                    self._log_action(
                        conversation_id,
                        "create_payment",
                        {"order_id": str(confirmed.id)},
                        {"payment_id": str(payment.id), "payment_url": payment_url},
                        confidence=None,
                    )
                except Exception as exc:
                    logger.warning("Order confirmation failed conversation=%s: %s", conversation_id, exc)
                    conversation.workflow_state = AgentWorkflowState.WAITING_FOR_CONFIRMATION
                    if variant_match and (variant_match.invalid_color or variant_match.invalid_size):
                        conversation.workflow_state = AgentWorkflowState.WAITING_FOR_VARIANT
                    elif inventory_available is False:
                        conversation.workflow_state = AgentWorkflowState.WAITING_FOR_VARIANT
                        slots.missing_fields = ["stock"]
        elif not order_side_effects_allowed:
            self._log_action(
                conversation_id,
                "order_side_effects_blocked",
                {"intent": extraction.intent.value},
                {"reasons": combined_reasons},
                confidence=extraction.confidence.intent,
            )

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
            suggestion = UpsellService(self.db).maybe_suggest_upsell(
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

        reply = self.response_service.generate(
            ReplyFacts(
                intent=extraction.intent,
                workflow_state=conversation.workflow_state,
                product=product,
                variant=variant,
                slots=slots,
                missing_fields=slots.missing_fields,
                valid_colors=valid_colors,
                valid_sizes=valid_sizes,
                available_stock=(
                    variant.stock_quantity - variant.reserved_quantity if variant else None
                ),
                handoff_reason=conversation.handoff_reason,
                invalid_color=bool(variant_match and variant_match.invalid_color),
                invalid_size=bool(variant_match and variant_match.invalid_size),
                style_hint=extraction.reply_style_hint,
                payment_url=payment_url,
                order_total=(
                    str(active_order.total_amount) if active_order is not None else None
                ),
                order_currency=active_order.currency if active_order is not None else None,
                upsell_text=upsell_text,
                size_confirmation_needed=size_confirmation_needed,
            )
        )
        if upsell_text and reply and upsell_text not in reply:
            reply = f"{reply}\n\n{upsell_text}"

        self._log_action(
            conversation_id,
            "state_transition",
            {
                "previous_state": extraction_input.workflow_state.value,
                "next_state": conversation.workflow_state.value,
                "resolve_source": resolve_source,
            },
            {"missing_fields": slots.missing_fields},
            confidence=extraction.confidence.intent,
        )
        self._log_action(
            conversation_id,
            "generate_reply",
            {"facts": slots_to_dict(slots)},
            {"reply": reply},
            confidence=extraction.confidence.slots,
        )

        settings_row = self._get_or_create_agent_settings(conversation.shop_id)
        decision = AutoSendDecisionService().decide(
            AutoSendDecisionInput(
                settings=settings_row,
                intent_confidence=extraction.confidence.intent,
                product_confidence=extraction.confidence.product,
                variant_confidence=extraction.confidence.slots,
                address_confidence=extraction.confidence.address,
                order_value=Decimal(active_order.total_amount) if active_order is not None else Decimal("0"),
                is_first_order=self._is_first_customer_order(conversation),
                handoff_reason=conversation.handoff_reason if conversation.handoff_required else None,
                message_risk="simulation" if conversation.is_simulation and not self.allow_simulated_order_side_effects else None,
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

        self._log_action(
            conversation_id,
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
        pilot_send_allowed, pilot_send_reasons = PilotService(self.db).enforce_auto_send_allowed(
            conversation.shop_id, conversation.instagram_account_id
        )
        if pilot_send_reasons:
            combined_reasons.extend(pilot_send_reasons)
            preview_reason = ";".join(combined_reasons)
            force_preview = True
            conversation.preview_required = True
            conversation.preview_reason = preview_reason
            conversation.suggested_outbound = reply
        send_trust = self._evaluate_trust_layer(
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
        if (
            decision.auto_send_allowed
            and not force_preview
            and not risk_score.requires_handoff
            and pilot_send_allowed
            and trust_send_allowed
            and not conversation.is_simulation
            and not pilot_service.is_emergency_stop_active(conversation.shop_id)
        ):
            outbound = self.send_service.send_text_message(
                conversation_id, reply, commit=False, is_simulation=False
            )
            AuditService(self.db).log(action="message_auto_sent", entity_type="conversation", shop_id=conversation.shop_id, entity_id=str(conversation.id), metadata={"message_id": str(outbound.id)})
            self._log_action(conversation_id, "send_outbound", {"reply": reply}, {"message_id": str(outbound.id)}, confidence=None)
        else:
            SuggestedReplyService(self.db).create_agent_suggestion(
                shop_id=conversation.shop_id,
                conversation_id=conversation.id,
                message_id=message.id,
                text=reply,
                reason=preview_reason,
                is_simulation=conversation.is_simulation,
            )
            action = "handoff_required" if (decision.requires_handoff or risk_score.requires_handoff) else "message_blocked_due_to_confidence" if force_preview else "suggested_reply_created"
            AuditService(self.db).log(action=action, entity_type="conversation", shop_id=conversation.shop_id, entity_id=str(conversation.id), metadata={"reasons": combined_reasons})
            self._log_action(conversation_id, "preview_outbound", {"reply": reply}, {"preview_required": force_preview, "reason": preview_reason, "simulation": conversation.is_simulation}, confidence=extraction.confidence.intent)

        self._create_decision_trace(
            trace_id=trace_id,
            conversation=conversation,
            message=message,
            agent_run=agent_run,
            extraction=extraction,
            slots=slots,
            product=product,
            variant_result=variant_result,
            inventory_available=inventory_available,
            risk_score=risk_score.model_dump(),
            decision=decision,
            order=active_order,
            reply=reply,
            outbound_message_id=outbound.id if outbound is not None else None,
            handoff_reason=conversation.handoff_reason,
            policy_eval=policy_eval,
            operating_mode=operating_mode,
        )
        self._record_trust_trace_events(
            trace_id=trace_id,
            conversation=conversation,
            extraction=extraction,
            slots=slots,
            product=product,
            variant=variant,
            policy_eval=policy_eval,
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
            reply=reply,
            reason=handoff.reason or state_decision.next_state.value,
        )

        if not extraction_error and not handoff.required:
            conversation.agent_failure_count = 0

        self.slots_repo.save(slots)
        ConversationPriorityService(self.db).refresh(conversation_id)
        self.db.commit()
        logger.info(
            "Orchestrator processed conversation=%s message=%s run=%s state=%s",
            conversation_id,
            message_id,
            agent_run.id,
            conversation.workflow_state.value,
        )
        return True

    def _resolve_product(
        self,
        conversation: Conversation,
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
            resolved = self.product_resolver.resolve_internal(conversation.shop_id, request)
            if resolved.requires_product_selection:
                slots.product_candidates = [candidate.model_dump(mode="json") for candidate in resolved.candidates]
                return None, "instagram_map_multi_product"
            if resolved.product is not None:
                product = self.products.get_for_shop(conversation.shop_id, resolved.product.id)
                slots.product_candidates = [candidate.model_dump(mode="json") for candidate in resolved.candidates]
                return product, "instagram_map"

        query = message_text or post_url or ""
        if query.strip():
            hits = self.semantic_search.search_internal(conversation.shop_id, query, limit=1)
            if hits:
                product = self.products.get_for_shop(conversation.shop_id, hits[0].product_id)
                if product is not None:
                    return product, "qdrant_semantic"

        return None, "unresolved"

    def _resolve_variant(
        self,
        product: Product | None,
        slots,
    ):
        if product is None:
            return None, None, None
        result = self.variant_resolver.resolve(
            shop_id=product.shop_id,
            product_id=product.id,
            raw_color=slots.color,
            raw_size=slots.size,
            quantity=slots.quantity or 1,
        )
        variants = self.variants.list_for_product(product.id)
        variant_match = match_variant(variants, result.normalized_color or slots.color, result.normalized_size or slots.size)
        variant = self.variants.get_by_id(result.variant_id) if result.variant_id else variant_match.variant
        return variant, variant_match, result

    def _product_context(self, product: Product | None) -> tuple[dict[str, Any] | None, list[str], list[str]]:
        if product is None:
            return None, [], []
        variants = self.variants.list_for_product(product.id)
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

    def _extract_post_reference(self, message: Message) -> tuple[str | None, str | None]:
        meta = message.raw_payload.get("_meta", {}) if message.raw_payload else {}
        shared_post_url = meta.get("shared_post_url")
        media_id = None
        attachment = message.raw_payload.get("message", {}).get("attachments", [])
        if attachment:
            payload = attachment[0].get("payload", {})
            media_id = payload.get("ig_post_media_id") or payload.get("media_id")
        return shared_post_url, media_id

    def _store_agent_run(
        self,
        *,
        conversation_id: UUID,
        message_id: UUID,
        extraction_input: AgentExtractionInput,
        extraction: AgentExtractionResult,
        error_message: str | None,
        is_simulation: bool = False,
    ) -> AgentRun:
        run = AgentRun(
            conversation_id=conversation_id,
            input_message_id=message_id,
            model_name=self.llm_service.model_name,
            prompt_version=self.llm_service.prompt_version,
            input_json=extraction_input.model_dump(mode="json"),
            output_json=self._agent_run_output_json(extraction, error_message),
            status=AgentRunStatus.FAILED if error_message else AgentRunStatus.SUCCESS,
            error_message=error_message,
            is_simulation=is_simulation,
        )
        if error_message:
            FAILED_AGENT_RUNS.inc()
        return self.agent_runs.create(run)


    def _agent_run_output_json(self, extraction: AgentExtractionResult, error_message: str | None) -> dict[str, Any]:
        payload = extraction.model_dump(mode="json")
        if error_message:
            invalid_output = getattr(self.llm_service, "last_invalid_output", None)
            payload["safe_fallback"] = True
            payload["invalid_llm_output"] = mask_sensitive_llm_output(invalid_output) if invalid_output else None
        return payload

    def _risk_settings(self, settings: ShopAgentSettings) -> dict[str, Any]:
        return {
            "intent_confidence_threshold": float(settings.confidence_threshold_intent),
            "slot_confidence_threshold": float(settings.confidence_threshold_variant),
            "product_confidence_threshold": float(settings.confidence_threshold_product),
            "variant_confidence_threshold": float(settings.confidence_threshold_variant),
            "address_confidence_threshold": float(settings.confidence_threshold_address),
            "high_value_order_threshold": str(settings.high_value_order_threshold),
            **(settings.risk_policy_json or {}),
        }

    def _customer_history(self, conversation: Conversation) -> dict[str, Any]:
        if conversation.customer_id is None:
            return {"first_order": True}
        order_count = self.db.query(Order).filter(Order.customer_id == conversation.customer_id).count()
        return {"order_count": order_count, "first_order": order_count == 0}

    @staticmethod
    def _is_payment_related(text: str | None) -> bool:
        lowered = (text or "").lower()
        return any(term in lowered for term in ("payment", "charged", "refund", "پرداخت", "پول"))

    @staticmethod
    def _is_complaint(text: str | None) -> bool:
        lowered = (text or "").lower()
        return any(term in lowered for term in ("angry", "complaint", "furious", "شکایت", "ناراضی", "خراب"))

    def _should_enforce_trust_gates(self, conversation: Conversation) -> bool:
        return not (conversation.is_simulation and self.allow_simulated_order_side_effects)

    @staticmethod
    def _derive_policy_action_name(extraction: AgentExtractionResult, draft_order_candidate: bool) -> str | None:
        if extraction.intent == AgentIntent.CONFIRM_ORDER:
            return "confirm"
        if draft_order_candidate:
            return "create_draft"
        if extraction.intent == AgentIntent.CANCEL_ORDER:
            return "cancel"
        return None

    def _evaluate_trust_layer(
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
        action_name = self._derive_policy_action_name(extraction, draft_order_candidate)
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
        enforce = pilot_settings.pilot_enabled and self._should_enforce_trust_gates(conversation)

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
        self.trace_service.record(
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
        self.trace_service.record(
            trace_id=trace_id,
            shop_id=conversation.shop_id,
            event_type=TraceEventType.SLOTS_EXTRACTED,
            payload={"slots": slots_to_dict(slots)},
            conversation_id=conversation.id,
        )
        self.trace_service.record(
            trace_id=trace_id,
            shop_id=conversation.shop_id,
            event_type=TraceEventType.CONFIDENCE_BAND,
            payload={
                "intent_band": self.policy_engine.confidence_band(extraction.confidence.intent),
                "scores": {
                    "intent": extraction.confidence.intent,
                    "product": extraction.confidence.product,
                    "variant": extraction.confidence.variant or extraction.confidence.slots,
                },
            },
            conversation_id=conversation.id,
        )
        if policy_eval is not None:
            self.trace_service.record_policy_checks(
                trace_id=trace_id,
                shop_id=conversation.shop_id,
                checks=[check.__dict__ for check in policy_eval.checks],
                conversation_id=conversation.id,
            )
            if policy_eval.allowed and outbound_created:
                self.trace_service.record(
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
                self.trace_service.record(
                    trace_id=trace_id,
                    shop_id=conversation.shop_id,
                    event_type=TraceEventType.ACTION_BLOCKED,
                    payload={"blocked_actions": blocked},
                    conversation_id=conversation.id,
                )

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
        self.db.add(AgentDecisionTrace(
            id=trace_id,
            conversation_id=conversation.id,
            message_id=message.id,
            agent_run_id=agent_run.id,
            intent=extraction.intent.value,
            extracted_slots=extraction.slots.model_dump(mode="json"),
            normalized_slots=slots_to_dict(slots),
            product_candidates=getattr(slots, "product_candidates", []) or [],
            selected_product_id=product.id if product is not None else None,
            variant_resolution=variant_result.model_dump(mode="json") if variant_result else {"variant_id": str(selected_variant_id) if selected_variant_id else None},
            inventory_result={"available": inventory_available},
            risk_score=enriched_risk,
            order_action={"order_id": str(order.id) if order else None, "status": order.status.value if order else None},
            next_state=conversation.workflow_state.value,
            outbound_message_id=outbound_message_id,
            auto_send_allowed=bool(decision.auto_send_allowed and not risk_score.get("requires_preview") and not risk_score.get("requires_handoff")),
            human_handoff_required=bool(conversation.handoff_required),
            reasoning_summary=(handoff_reason or ";".join(risk_score.get("risk_reasons", [])) or "Deterministic state and safety gates evaluated"),
        ))


    def _get_or_create_agent_settings(self, shop_id: UUID) -> ShopAgentSettings:
        settings = self.db.get(ShopAgentSettings, shop_id)
        if settings is None:
            settings = ShopAgentSettings(shop_id=shop_id)
            self.db.add(settings)
            self.db.flush()
        return settings


    def _preview_decision(
        self,
        conversation: Conversation,
        confidence: ExtractionConfidence,
        handoff_required: bool,
    ) -> tuple[bool, str | None]:
        settings = resolve_live_agent_settings(conversation.shop)
        if not settings.get("auto_send_enabled", True):
            return True, "auto_send_disabled"
        if handoff_required:
            return True, "handoff_required"

        if settings.get("preview_required_for_low_confidence", True):
            studio_settings = (
                getattr(conversation.shop, "agent_studio_settings", None)
                if conversation.shop is not None
                else None
            )
            if studio_settings is not None:
                low_confidence_checks = (
                    ("intent", confidence.intent, settings.get("intent_confidence_threshold", 0.75)),
                    ("product", confidence.product, settings.get("product_confidence_threshold", 0.80)),
                    ("variant", confidence.slots, settings.get("variant_confidence_threshold", 0.85)),
                    ("address", confidence.address, settings.get("address_confidence_threshold", 0.80)),
                )
                for label, value, threshold in low_confidence_checks:
                    if float(value) < float(threshold):
                        return True, f"low_{label}_confidence:{float(value):.2f}"
            else:
                threshold = float(settings.get("auto_send_confidence_threshold", 0.85))
                if confidence.intent < threshold:
                    return True, f"low_auto_send_confidence:{confidence.intent:.2f}"

        if settings.get("preview_required_for_first_order", False) and self._is_first_customer_order(conversation):
            return True, "first_order_preview"
        if settings.get("preview_required_for_first_24h", True):
            from datetime import UTC, datetime, timedelta
            if conversation.created_at and conversation.created_at >= datetime.now(UTC) - timedelta(hours=24):
                return True, "first_24h_preview"
        return False, None

    def _is_first_customer_order(self, conversation: Conversation) -> bool:
        if conversation.customer_id is None:
            return True
        order_count = self.db.query(Order).filter(Order.customer_id == conversation.customer_id).count()
        return order_count <= 1

    def _estimated_order_value(
        self, active_order: Order | None, variant: ProductVariant | None, slots
    ) -> Decimal:
        values: list[Decimal] = []
        if active_order is not None:
            values.append(Decimal(active_order.total_amount))
        if variant is not None:
            quantity = slots.quantity or 1
            values.append(Decimal(str(variant.price)) * Decimal(quantity))
        return max(values, default=Decimal("0"))

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
        self.db.add(AgentDecisionAudit(
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

    def _log_action(
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

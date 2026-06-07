from __future__ import annotations

import logging
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
    ConversationState,
)
from app.domain.models import AgentAction, AgentRun, Conversation, Message, Product, ProductVariant
from app.integrations.openai_client import LiveOpenAIChatClient, OpenAIChatClient
from app.integrations.qdrant_client import LiveQdrantClient, QdrantClient
from app.repositories.agent_action_repository import AgentActionRepository
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.conversation_slots_repository import ConversationSlotsRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.agent import AgentExtractionInput, AgentExtractionResult
from app.schemas.instagram_product_map import ResolveInstagramProductRequest
from app.services.handoff_service import evaluate_handoff
from app.services.instagram_product_resolver import InstagramProductResolver
from app.services.instagram_send_service import InstagramSendService
from app.services.llm_extraction_service import LLMExtractionService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.product_semantic_search_service import ProductSemanticSearchService
from app.services.response_generation_service import ReplyFacts, ResponseGenerationService
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
        llm_service: LLMExtractionService | None = None,
        semantic_search: ProductSemanticSearchService | None = None,
        chat_client: OpenAIChatClient | None = None,
        qdrant_client: QdrantClient | None = None,
        settings: Settings | None = None,
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
        self.send_service = InstagramSendService(db, self.settings)
        self.response_service = ResponseGenerationService()
        self.order_service = OrderService(db, settings=self.settings)
        self.payment_service = PaymentService(db, settings=self.settings)

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

        if conversation.agent_paused or conversation.assigned_operator_id is not None:
            logger.info("Conversation %s is under human control; skipping agent", conversation_id)
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
        )

        if extraction_error:
            conversation.agent_failure_count += 1

        merge_extracted_slots(slots, extraction)
        if product is not None:
            slots.product_id = product.id

        variant, variant_match = self._resolve_variant(product, slots)
        if variant is not None:
            slots.product_variant_id = variant.id
        elif variant_match and (variant_match.invalid_color or variant_match.invalid_size):
            slots.product_variant_id = None

        inventory_available = None
        if variant is not None:
            inventory_available = check_inventory(variant, slots.quantity)

        handoff = evaluate_handoff(
            extraction,
            failure_count=conversation.agent_failure_count,
            settings=self.settings,
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

        payment_url: str | None = None
        active_order = None

        if extraction.intent == AgentIntent.CANCEL_ORDER:
            self.order_service.cancel_active_for_conversation(
                conversation_id,
                reason="Customer cancelled via chat",
            )
        elif (
            product is not None
            and variant is not None
            and self.order_service.can_create_draft(slots, variant)
        ):
            active_order = self.order_service.upsert_draft_from_conversation(
                conversation, slots, product, variant
            )
            if active_order is not None:
                CREATED_ORDERS.inc()
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
            )
        )

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

        outbound = self.send_service.send_text_message(conversation_id, reply, commit=False)
        self._log_action(
            conversation_id,
            "send_outbound",
            {"reply": reply},
            {"message_id": str(outbound.id)},
            confidence=None,
        )

        if not extraction_error and not handoff.required:
            conversation.agent_failure_count = 0

        self.slots_repo.save(slots)
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
        request = ResolveInstagramProductRequest(
            instagram_post_url=shared_post_url or slots.instagram_post_url,
            instagram_media_id=media_id,
        )
        resolved = self.product_resolver.resolve_internal(conversation.shop_id, request)
        if resolved.product is not None:
            product = self.products.get_for_shop(conversation.shop_id, resolved.product.id)
            return product, "instagram_map"

        query = message_text or shared_post_url or ""
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
            return None, None
        variants = self.variants.list_for_product(product.id)
        variant_match = match_variant(variants, slots.color, slots.size)
        return variant_match.variant, variant_match

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
    ) -> AgentRun:
        run = AgentRun(
            conversation_id=conversation_id,
            input_message_id=message_id,
            model_name=self.llm_service.model_name,
            prompt_version=self.llm_service.prompt_version,
            input_json=extraction_input.model_dump(mode="json"),
            output_json=extraction.model_dump(mode="json"),
            status=AgentRunStatus.FAILED if error_message else AgentRunStatus.SUCCESS,
            error_message=error_message,
        )
        if error_message:
            FAILED_AGENT_RUNS.inc()
        return self.agent_runs.create(run)

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

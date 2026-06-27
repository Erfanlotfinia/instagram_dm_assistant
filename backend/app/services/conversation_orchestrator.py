from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.models import Conversation, Order
from app.integrations.llm_client import build_chat_client, build_embedding_client
from app.integrations.openai_client import OpenAIChatClient
from app.integrations.qdrant_client import LiveQdrantClient, QdrantClient
from app.repositories.agent_action_repository import AgentActionRepository
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.conversation_slots_repository import ConversationSlotsRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.agent import ExtractionConfidence
from app.services.agent_risk_scoring_service import AgentRiskScoringService
from app.services.agent_settings_live import resolve_live_agent_settings
from app.services.channel_outbound_service import ChannelOutboundService
from app.services.decision_trace_service import DecisionTraceService
from app.services.instagram_product_resolver import InstagramProductResolver
from app.services.llm_extraction_service import LLMExtractionProtocol, LLMExtractionService
from app.services.order_service import OrderService
from app.services.orchestration import (
    ConversationPipeline,
    ConversationPipelineContext,
    OrchestrationServices,
)
from app.services.payment_service import PaymentService
from app.services.policy_engine import PolicyEngine
from app.services.product_semantic_search_service import (
    InternalSemanticSearch,
    ProductSemanticSearchService,
)
from app.services.response_generation_service import ResponseGenerationService
from app.services.variant_resolver import VariantResolver

logger = logging.getLogger(__name__)


class ConversationOrchestrator:
    """Thin coordinator over the staged conversation pipeline.

    Construction wiring is preserved for backward compatibility (tests build this
    directly and patch ``self.llm_service``). The actual processing is delegated
    to :class:`ConversationPipeline`, whose stages live under
    ``app.services.orchestration``.
    """

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
        self.send_service = ChannelOutboundService(db, self.settings)
        self.response_service = ResponseGenerationService()
        self.order_service = OrderService(db, settings=self.settings)
        self.payment_service = PaymentService(db, settings=self.settings)
        self.risk_scoring = AgentRiskScoringService()
        self.policy_engine = PolicyEngine()
        self.trace_service = DecisionTraceService(db)
        self.allow_simulated_order_side_effects = allow_simulated_order_side_effects

        if chat_client is None:
            chat_client = build_chat_client(self.settings)
        if qdrant_client is None:
            if self.settings.llm_mode == "mock":
                from app.integrations.qdrant_client import MockQdrantClient

                qdrant_client = MockQdrantClient()
            else:
                qdrant_client = LiveQdrantClient(self.settings)
        self.llm_service = llm_service or LLMExtractionService(chat_client, self.settings)
        if semantic_search is None:
            if self.settings.llm_mode == "mock":
                from app.integrations.openai_client import MockOpenAIEmbeddingClient

                embedding_client = MockOpenAIEmbeddingClient()
            else:
                embedding_client = build_embedding_client(self.settings)
            self.semantic_search = ProductSemanticSearchService(
                db,
                qdrant_client=qdrant_client,
                embedding_client=embedding_client,
                settings=self.settings,
            )
        else:
            self.semantic_search = semantic_search

        self.services = OrchestrationServices(
            db=self.db,
            settings=self.settings,
            conversations=self.conversations,
            messages=self.messages,
            slots_repo=self.slots_repo,
            agent_runs=self.agent_runs,
            agent_actions=self.agent_actions,
            products=self.products,
            variants=self.variants,
            product_resolver=self.product_resolver,
            variant_resolver=self.variant_resolver,
            send_service=self.send_service,
            response_service=self.response_service,
            order_service=self.order_service,
            payment_service=self.payment_service,
            risk_scoring=self.risk_scoring,
            policy_engine=self.policy_engine,
            trace_service=self.trace_service,
            llm_service=self.llm_service,
            semantic_search=self.semantic_search,
            allow_simulated_order_side_effects=self.allow_simulated_order_side_effects,
        )

    def process_inbound_message(self, conversation_id: UUID, message_id: UUID) -> bool:
        ctx = ConversationPipelineContext(
            conversation_id=conversation_id,
            message_id=message_id,
        )
        return ConversationPipeline(self.services).run(ctx)

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

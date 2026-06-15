from uuid import uuid4

from app.domain.enums import ChannelMessageType, ChannelProvider
from app.schemas.channels import MediaItem, NormalizedInboundMessage, NormalizedMessage
from app.services.social_admin.automation_engine import AutomationEngine
from app.services.social_admin.context_graph import ConversationContextGraph
from app.services.social_admin.human_handoff_service import HumanHandoffService
from app.services.social_admin.llm_fallback_orchestrator import LLMFallbackOrchestrator
from app.services.social_admin.scenario_router import ScenarioRouter


def test_normalized_message_envelope_is_channel_agnostic():
    inbound = NormalizedInboundMessage(
        provider=ChannelProvider.TELEGRAM,
        external_message_id="m-1",
        external_chat_id="chat-1",
        external_user_id="user-1",
        message_type=ChannelMessageType.IMAGE,
        text="is this available?",
        media_items=[MediaItem(url="https://example.test/item.png")],
    )

    normalized = NormalizedMessage.from_inbound(inbound)

    assert normalized.channel == ChannelProvider.TELEGRAM
    assert normalized.user_id == "user-1"
    assert normalized.conversation_id == "chat-1"
    assert normalized.content == "is this available?"
    assert normalized.attachments[0].url == "https://example.test/item.png"


def test_reference_resolution_handles_second_product_in_context_graph():
    graph = ConversationContextGraph()
    products = [str(uuid4()), str(uuid4())]
    graph.add_context_item(
        shop_id="shop-1",
        conversation_id="conv-1",
        provider="whatsapp",
        item_type="product_list",
        candidate_product_ids_json=products,
    )

    resolved = graph.resolve_reference({"text": "send the second product"}, "conv-1")

    assert resolved.selected_product_id == products[1]
    assert resolved.reason == "ordinal_product_list_selection"


def test_router_keeps_payment_claims_deterministic_and_out_of_llm():
    decision = ScenarioRouter().route({"text": "I paid by bank transfer"})

    assert decision.scenario_code == "MANUAL_PAYMENT"
    assert decision.requires_llm is False
    assert decision.handler == "ManualPaymentReceiptHandler"


def test_llm_fallback_blocks_commerce_fact_hallucination():
    output = LLMFallbackOrchestrator().safe_fallback(
        {
            "detected_scenario": "buy",
            "order_intent": {"wants_to_buy": True},
            "safe_response_draft": "It is in stock and costs $10. You paid.",
        }
    )

    assert output.needs_human is True
    assert output.safe_response_draft is None
    assert output.human_reason == "blocked_possible_hallucinated_commerce_fact"


def test_human_handoff_service_is_final_safety_layer_without_db():
    result = HumanHandoffService().trigger("conv-1", "customer_requested_operator")

    assert result.required is True
    assert result.reason == "customer_requested_operator"
    assert result.conversation_id == "conv-1"


class _ExplodingDb:
    def get(self, *_args, **_kwargs):
        raise AssertionError("external conversation ids must not be cast or looked up")

    def add(self, *_args, **_kwargs):
        raise AssertionError("external conversation ids must not be persisted directly")


def test_handoff_service_skips_db_lookup_for_external_conversation_id():
    result = HumanHandoffService(_ExplodingDb()).trigger(
        "telegram-chat-1", "external_channel_conversation"
    )

    assert result.required is True
    assert result.reason == "external_channel_conversation"
    assert result.conversation_id == "telegram-chat-1"


def test_automation_engine_never_dispatches_llm_handler():
    decision = ScenarioRouter().route({"text": "random unrelated chitchat xyz"})

    result = AutomationEngine().execute(decision, {})

    assert result.executed is False
    assert result.handler_result is None
    assert result.skipped_reason == "llm_fallback_route"


def test_router_accepts_normalized_message_content_for_multichannel_flow():
    inbound = NormalizedInboundMessage(
        provider=ChannelProvider.RUBIKA,
        external_message_id="m-2",
        external_chat_id="chat-2",
        external_user_id="user-2",
        text="I paid by bank transfer",
    )
    normalized = NormalizedMessage.from_inbound(inbound)

    decision = ScenarioRouter().route(normalized)

    assert decision.scenario_code == "MANUAL_PAYMENT"
    assert decision.requires_llm is False

from uuid import uuid4

from app.services.idempotency_key_manager import IdempotencyKeyManager, IdempotencyScope
from app.services.social_admin.context_graph import ConversationContextService
from app.services.social_admin.execution_policy_gate import ExecutionPolicyGate
from app.services.social_admin.llm_fallback_orchestrator import LLMFallbackOrchestrator
from app.services.social_admin.scenario_router import ScenarioDecision


def test_execution_policy_blocks_llm_without_automation_first():
    gate = ExecutionPolicyGate()
    decision = ScenarioDecision(
        "LLM_FALLBACK", 0.3, "LLMFallbackOrchestrator", requires_llm=True
    )

    result = gate.evaluate(
        decision, requested_execution="llm", automation_attempted=False
    )

    assert result.decision == "block"
    assert result.reason == "automation_first_required_before_llm"
    assert result.execution_trace_id


def test_execution_policy_allows_automation_and_blocks_unknown_execution():
    gate = ExecutionPolicyGate()
    decision = ScenarioDecision("ASK_PRICE", 0.9, "AskPriceReferencedProductHandler")

    allowed = gate.evaluate(decision, requested_execution="automation")
    blocked = gate.evaluate(decision, requested_execution="database")

    assert allowed.decision == "allow"
    assert allowed.execution_type == "automation"
    assert blocked.decision == "block"
    assert blocked.reason == "unknown_execution_type"


def test_llm_output_schema_rejects_malformed_and_blocks_commerce_facts():
    llm = LLMFallbackOrchestrator()

    invalid = llm.safe_fallback({"order_intent": "not-an-object"})
    unsafe = llm.safe_fallback(
        {
            "order_intent": {"wants_to_buy": True},
            "safe_response_draft": "It is in stock and costs $10",
        }
    )

    assert invalid.needs_human is True
    assert invalid.human_reason == "invalid_structured_llm_output"
    assert unsafe.needs_human is True
    assert unsafe.safe_response_draft is None


def test_context_graph_resolves_ordinal_and_same_as_before_across_channel_memory():
    graph = ConversationContextService()
    shop_id = str(uuid4())
    conversation_id = str(uuid4())
    first_product = str(uuid4())
    second_product = str(uuid4())
    graph.add_context_item(
        shop_id=shop_id,
        conversation_id=conversation_id,
        provider="instagram",
        item_type="product_list",
        candidate_product_ids_json=[first_product, second_product],
    )

    ordinal = graph.resolve_reference({"text": "second item please"}, conversation_id)
    same = graph.resolve_reference({"text": "same as before"}, conversation_id)

    assert ordinal.selected_product_id == second_product
    assert ordinal.reason == "ordinal_product_list_selection"
    assert same.selected_context_item_id is not None


def test_idempotency_keys_are_stable_and_scoped():
    key1 = IdempotencyKeyManager.build_key(
        IdempotencyScope.ORDER_CREATE, "shop", "conversation", payload={"b": 2, "a": 1}
    )
    key2 = IdempotencyKeyManager.build_key(
        IdempotencyScope.ORDER_CREATE, "shop", "conversation", payload={"a": 1, "b": 2}
    )

    assert key1 == key2
    assert key1.startswith("order_create:")

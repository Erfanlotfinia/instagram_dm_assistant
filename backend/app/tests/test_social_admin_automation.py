from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.services.social_admin import (
    AdminTaskEngine,
    AutomationHandlerRegistry,
    CatalogQueryPlanner,
    ConversationContextService,
    LLMFallbackOrchestrator,
    ReferencedContentResolver,
    ScenarioRouter,
    SignedActionService,
)


def test_context_resolves_product_list_second_one_persian():
    svc = ConversationContextService()
    svc.add_context_item(shop_id="s1", conversation_id="c1", provider="telegram", item_type="product_list", candidate_product_ids_json=["p1", "p2"])
    result = svc.resolve_reference({"text": "دومی رو بده"}, "c1")
    assert result.selected_product_id == "p2"
    assert result.confidence >= .9


def test_context_resolves_active_product_availability():
    svc = ConversationContextService()
    svc.add_context_item(shop_id="s1", conversation_id="c1", provider="instagram", item_type="product_post", selected_product_id="p9")
    result = svc.resolve_reference({"text": "موجوده؟"}, "c1")
    assert result.selected_product_id == "p9"


def test_router_deterministic_before_llm():
    decision = ScenarioRouter().route({"text": "قیمت این چند؟"})
    assert decision.scenario_code == "ASK_PRICE_REFERENCED_PRODUCT"
    assert decision.requires_llm is False


def test_catalog_query_planner_category_brand_price():
    plan = CatalogQueryPlanner().plan("همه چکش‌های برند بوش زیر ۵۰۰۰۰۰۰ رو نشون بده")
    assert plan.category_slug == "hammer"
    assert plan.brand == "Bosch"
    assert plan.price_max == 5000000
    assert plan.confidence >= .86


def test_referenced_content_resolver_uses_context_for_second_one():
    ctx = ConversationContextService()
    ctx.add_context_item(shop_id="s1", conversation_id="c1", provider="rubika", item_type="product_list", candidate_product_ids_json=["p1", "p2"])
    res = ReferencedContentResolver(ctx).resolve({"text": "second one"}, {}, "c1")
    assert res.reference_type == "product_list_selection"
    assert res.selected_product_id == "p2"


def test_handler_registry_dispatches_without_llm():
    result = AutomationHandlerRegistry().dispatch("PaymentMethodsHandler", {})
    assert result.status == "handled"
    assert result.audit_metadata["llm_used"] is False


def test_llm_fallback_blocks_hallucinated_commerce_fact():
    out = LLMFallbackOrchestrator().validate_output({"order_intent": {"wants_to_buy": True}, "safe_response_draft": "It is in stock for $10"})
    assert out.needs_human is True
    assert out.safe_response_draft is None


def test_admin_task_requires_approval_and_no_autopublish():
    task = AdminTaskEngine().create_task("s1", "u1", "post_caption_draft", {"topic": "new shoes"})
    assert task.requires_approval is True
    assert task.output_json["auto_publish"] is False


def test_signed_action_rejects_forged_expired_cross_shop():
    svc = SignedActionService("secret")
    good = svc.sign({"action_id":"a1","shop_id":"s1","conversation_id":"c1","context_item_id":None,"action_type":"select_product","expires_at":(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()})
    assert svc.verify(good, "s1", "c1") is True
    forged = dict(good, shop_id="s2")
    assert svc.verify(forged, "s1", "c1") is False


def test_scenario_fixture_has_150_scenarios():
    import json, pathlib
    data = json.loads(pathlib.Path("app/tests/fixtures/scenarios/social_admin_scenarios.json").read_text())
    assert len(data) >= 150
    assert {"instagram", "whatsapp", "telegram", "bale", "rubika"}.issubset({s["provider"] for s in data})

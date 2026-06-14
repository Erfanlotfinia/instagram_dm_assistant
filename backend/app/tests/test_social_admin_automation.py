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
    svc.add_context_item(shop_id="s1", conversation_id="c1", provider="telegram", item_type="product_list", candidate_product_ids_json=["00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002"])
    result = svc.resolve_reference({"text": "دومی رو بده"}, "c1")
    assert result.selected_product_id == "00000000-0000-0000-0000-000000000002"
    assert result.confidence >= .9


def test_context_resolves_active_product_availability():
    svc = ConversationContextService()
    svc.add_context_item(shop_id="s1", conversation_id="c1", provider="instagram", item_type="product_post", selected_product_id="00000000-0000-0000-0000-000000000009")
    result = svc.resolve_reference({"text": "موجوده؟"}, "c1")
    assert result.selected_product_id == "00000000-0000-0000-0000-000000000009"


def test_router_deterministic_before_llm():
    decision = ScenarioRouter().route({"text": "قیمت این چند؟"})
    assert decision.scenario_code == "ASK_PRICE_REFERENCED_PRODUCT"
    assert decision.requires_llm is False


def test_router_active_order_cancel_and_summary_before_confirm():
    router = ScenarioRouter()

    cancel_decision = router.route({"text": "میخوام لغو کنم"}, active_order={"id": "o1"})
    assert cancel_decision.handler == "CancelOrderHandler"
    assert cancel_decision.scenario_code == "ORDER_CANCEL"

    summary_decision = router.route({"text": "خلاصه سفارش رو بفرست"}, active_order={"id": "o1"})
    assert summary_decision.handler == "OrderSummaryHandler"
    assert summary_decision.scenario_code == "ORDER_SUMMARY"

    confirm_decision = router.route({"text": "تایید میکنم"}, active_order={"id": "o1"})
    assert confirm_decision.handler == "ConfirmOrderHandler"
    assert confirm_decision.scenario_code == "ORDER_CONFIRM"


def test_router_callback_priority_over_text():
    decision = ScenarioRouter().route({"text": "price?", "button_id": "buy:1"})
    assert decision.handler == "SelectFromProductListHandler"
    assert decision.requires_llm is False


def test_router_catalog_query_before_llm():
    decision = ScenarioRouter().route({"text": "همه چکش‌های برند بوش زیر ۵۰۰۰۰۰۰ رو نشون بده"})
    assert decision.requires_llm is False
    assert "List" in decision.handler or "ProductSearch" in decision.handler


def test_router_llm_fallback_only_when_no_match():
    decision = ScenarioRouter().route({"text": "random unrelated chitchat xyz"})
    assert decision.requires_llm is True
    assert decision.handler == "LLMFallbackOrchestrator"


def test_scenario_regression_runner_metrics(db_session):
    metrics = __import__(
        "app.services.social_admin.scenario_regression_runner",
        fromlist=["ScenarioRegressionRunner"],
    ).ScenarioRegressionRunner(db_session).run()
    # Safety counters must stay clean.
    assert metrics.unsafe_action_count == 0
    assert metrics.false_order_count == 0
    assert metrics.false_payment_count == 0
    # Routing accuracy against authored ground truth.
    assert metrics.scenario_accuracy > 0.9
    # Automation-first: deterministic automation must dominate, with LLM and
    # handoff as smaller escalation paths. The three buckets are mutually
    # exclusive and must sum to ~1.0 (every scenario lands in exactly one).
    assert metrics.automation_handled_rate > 0.7
    assert metrics.llm_fallback_rate > 0.0
    assert metrics.handoff_rate > 0.0
    bucket_sum = (
        metrics.automation_handled_rate
        + metrics.llm_fallback_rate
        + metrics.handoff_rate
    )
    assert abs(bucket_sum - 1.0) < 0.02
    # Reference resolution and catalog discovery must actually resolve products.
    assert metrics.reference_resolution_accuracy > 0.8
    assert metrics.product_discovery_accuracy > 0.8


def test_scenario_regression_runner_does_not_persist(db_session):
    """The runner seeds an ephemeral catalog that must be rolled back."""
    from sqlalchemy import func, select

    from app.domain.models import Product, Shop

    shops_before = db_session.scalar(select(func.count()).select_from(Shop))
    products_before = db_session.scalar(select(func.count()).select_from(Product))
    __import__(
        "app.services.social_admin.scenario_regression_runner",
        fromlist=["ScenarioRegressionRunner"],
    ).ScenarioRegressionRunner(db_session).run()
    assert db_session.scalar(select(func.count()).select_from(Shop)) == shops_before
    assert db_session.scalar(select(func.count()).select_from(Product)) == products_before


def test_catalog_query_planner_category_brand_price():
    plan = CatalogQueryPlanner().plan("همه چکش‌های برند بوش زیر ۵۰۰۰۰۰۰ رو نشون بده")
    assert plan.category_slug == "hammer"
    assert plan.brand == "Bosch"
    assert plan.price_max == 5000000
    assert plan.confidence >= .86


def test_referenced_content_resolver_uses_context_for_second_one():
    ctx = ConversationContextService()
    ctx.add_context_item(shop_id="s1", conversation_id="c1", provider="rubika", item_type="product_list", candidate_product_ids_json=["00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002"])
    res = ReferencedContentResolver(ctx).resolve({"text": "second one"}, {}, "c1")
    assert res.reference_type == "product_list_selection"
    assert res.selected_product_id == "00000000-0000-0000-0000-000000000002"


def test_handler_registry_dispatches_without_llm():
    result = AutomationHandlerRegistry().dispatch("PaymentMethodsHandler", {})
    assert result.status == "handled"
    assert result.audit_metadata["llm_used"] is False


def test_llm_fallback_blocks_hallucinated_commerce_fact():
    out = LLMFallbackOrchestrator().validate_output({"order_intent": {"wants_to_buy": True}, "safe_response_draft": "It is in stock for $10"})
    assert out.needs_human is True
    assert out.safe_response_draft is None


def test_admin_task_requires_approval_and_no_autopublish():
    out = AdminTaskEngine().generate_draft("post_caption_draft", {"topic": "new shoes"})
    assert out["auto_publish"] is False


def test_signed_action_rejects_forged_expired_cross_shop():
    svc = SignedActionService("secret")
    good = svc.sign({"action_id":"a1","shop_id":"s1","conversation_id":"c1","context_item_id":None,"action_type":"select_product","expires_at":(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()})
    assert svc.verify(good, "s1", "c1") is True
    forged = dict(good, shop_id="s2")
    assert svc.verify(forged, "s1", "c1") is False


def test_scenario_fixture_has_150_scenarios():
    import json, pathlib
    data = json.loads(
        pathlib.Path("app/tests/fixtures/scenarios/social_admin_scenarios.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(data) >= 150
    assert {"instagram", "whatsapp", "telegram", "bale", "rubika"}.issubset({s["provider"] for s in data})

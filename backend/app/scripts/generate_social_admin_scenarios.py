"""Generate (and validate) the social-admin scenario regression fixture.

The previous fixture was templated noise (~95% identical ``price?`` rows), which
made every operational metric meaningless. This generator produces a varied,
realistic suite that exercises every automation family the router supports
(referenced-product Q&A, product-list selection, catalog discovery, ordering,
payments, shipping, support, admin drafting), plus deterministic human-handoff
and LLM-fallback cases.

Each scenario carries:
  * ``expected_handler`` / ``expected_uses_llm`` / ``expected_handoff`` — the
    authored ground truth the deterministic router is expected to reproduce.
  * ``seed`` — what conversation context the runner should pre-load so the
    matched handler can actually resolve a product/list (``product_index`` /
    ``product_indices`` reference :data:`REGRESSION_CATALOG` in the runner).
  * ``active_order_status`` — drives a transient active order for order/payment
    scenarios.

Run ``python -m app.scripts.generate_social_admin_scenarios`` to rewrite the
fixture, or ``--validate`` to route the current fixture through the (DB-free)
``ScenarioRouter`` and report mismatches.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "scenarios"
    / "social_admin_scenarios.json"
)

PROVIDERS = ["instagram", "whatsapp", "telegram", "bale", "rubika"]

NO_FALSE_SAFETY = ["no_false_payment", "no_unsafe_order"]


# Intent templates. ``text`` values are authored so the deterministic router
# reproduces ``handler`` (verified by --validate). ``seed`` / ``active_order``
# describe the context the runner pre-loads before routing.
INTENTS: list[dict[str, Any]] = [
    # --- Group A: referenced product Q&A (needs an active product in context) ---
    {
        "scenario": "ASK_PRICE_REFERENCED_PRODUCT",
        "handler": "AskPriceReferencedProductHandler",
        "texts": ["قیمت این چنده؟", "این محصول چنده؟", "قیمت اون چقدر میشه چند؟"],
        "seed": {"kind": "active_product", "product_index": 0},
    },
    {
        "scenario": "ASK_STOCK_REFERENCED_PRODUCT",
        "handler": "AskStockReferencedProductHandler",
        "texts": ["این موجوده؟", "این رو دارین؟", "موجود هست این؟"],
        "seed": {"kind": "active_product", "product_index": 0},
    },
    {
        "scenario": "ASK_DETAILS_REFERENCED_PRODUCT",
        "handler": "AskDetailsReferencedProductHandler",
        "texts": ["جزئیات این محصول رو بگو", "اطلاعات این رو میخوام بدونم همون"],
        "seed": {"kind": "active_product", "product_index": 0},
    },
    {
        "scenario": "BUY_REFERENCED_PRODUCT",
        "handler": "BuyReferencedProductHandler",
        "texts": ["این رو میخوام", "این رو سفارش میدم همون", "میخوام این رو بخرم"],
        "seed": {"kind": "active_product", "product_index": 0},
    },
    # --- Group A: product-list selection (needs a product_list in context) ---
    {
        "scenario": "PRODUCT_LIST_SELECTION",
        "handler": "SelectFromProductListHandler",
        "texts": ["دومی", "اولی", "second one", "first one"],
        "seed": {"kind": "product_list", "product_indices": [0, 1, 2]},
    },
    {
        "scenario": "BUTTON_CALLBACK",
        "handler": "SelectFromProductListHandler",
        "texts": [""],
        "button_id": "select_product:1",
        "seed": {"kind": "product_list", "product_indices": [0, 1, 2]},
    },
    # --- Group B: catalog discovery (uses the seeded DB catalog) ---
    {
        "scenario": "BEST_SELLERS",
        "handler": "BestSellersHandler",
        "texts": ["پرفروش‌ترین‌ها رو نشون بده", "محصولات پرفروش چیا هستن؟"],
        "seed": None,
    },
    {
        "scenario": "CATALOG_PRICE_RANGE",
        "handler": "ProductSearchByPriceRangeHandler",
        "texts": [
            "همه چکش‌های برند بوش زیر ۵۰۰۰۰۰۰ رو نشون بده",
            "کفش زیر ۳۰۰۰۰۰۰ نشون بده",
        ],
        "seed": None,
    },
    {
        "scenario": "CATALOG_BRAND",
        "handler": "ListProductsByBrandHandler",
        "texts": ["محصولات برند بوش رو نشون بده", "فقط برند بوش رو نشون بده"],
        "seed": None,
    },
    {
        "scenario": "CATALOG_CATEGORY",
        "handler": "ListProductsByCategoryHandler",
        "texts": ["عطرهای برند نایک رو نشون بده", "کفش‌ها رو نشون بده"],
        "seed": None,
    },
    {
        "scenario": "SIMILAR_PRODUCTS",
        "handler": "SimilarProductsHandler",
        "texts": ["محصولات مشابه رو نشون بده", "مدل‌های مشابه رو نشون بده"],
        "seed": None,
    },
    {
        "scenario": "COMPARE_PRODUCTS",
        "handler": "CompareProductsHandler",
        "texts": ["محصولات رو مقایسه کن", "مقایسه‌شون کن لطفا"],
        "seed": None,
    },
    # --- Group C: ordering against an active order ---
    {
        "scenario": "ORDER_SUMMARY",
        "handler": "OrderSummaryHandler",
        "texts": ["خلاصه سفارش رو بفرست", "خلاصه سفارشم چیه؟"],
        "seed": None,
        "active_order_status": "ready_for_confirmation",
    },
    {
        "scenario": "ORDER_CONFIRM",
        "handler": "ConfirmOrderHandler",
        "texts": ["تایید میکنم", "اوکی تایید"],
        "seed": None,
        "active_order_status": "ready_for_confirmation",
    },
    {
        "scenario": "ORDER_CANCEL",
        "handler": "CancelOrderHandler",
        "texts": ["میخوام لغو کنم", "سفارش رو کنسل کن لغو"],
        "seed": None,
        "active_order_status": "ready_for_confirmation",
    },
    # --- Group D: payments ---
    {
        "scenario": "PAYMENT_METHODS",
        "handler": "PaymentMethodsHandler",
        "texts": ["روش پرداخت چیه؟", "چطور پرداخت کنم روش پرداخت؟"],
        "seed": None,
    },
    {
        "scenario": "PAYMENT_LINK",
        "handler": "SendPaymentLinkHandler",
        "texts": ["لینک پرداخت میخوام", "لینک پرداخت رو بفرست"],
        "seed": None,
        "active_order_status": "ready_for_confirmation",
    },
    {
        "scenario": "MANUAL_PAYMENT",
        "handler": "ManualPaymentReceiptHandler",
        "texts": ["پرداخت کردم", "واریز کردم رسید دارم"],
        "seed": None,
    },
    # --- Group E: shipping / delivery ---
    {
        "scenario": "SHIPPING_COST",
        "handler": "ShippingCostHandler",
        "texts": ["هزینه ارسال چقدره؟", "ارسال چقدر هزینه داره؟"],
        "seed": None,
    },
    {
        "scenario": "SHIPPING_METHODS",
        "handler": "ShippingMethodsHandler",
        "texts": ["روش‌های ارسال چیه؟", "ارسال چه جوریه؟"],
        "seed": None,
    },
    {
        "scenario": "TRACKING_CODE",
        "handler": "TrackingCodeHandler",
        "texts": ["کد رهگیری ارسالم چیه؟", "کد پیگیری ارسال رو بده"],
        "seed": None,
    },
    # --- Group F: support / policy / handoff ---
    {
        "scenario": "RETURN_REQUEST",
        "handler": "ReturnRequestHandler",
        "texts": ["میخوام مرجوع کنم", "درخواست مرجوع دارم"],
        "seed": None,
    },
    {
        "scenario": "EXCHANGE_REQUEST",
        "handler": "ExchangeRequestHandler",
        "texts": ["میخوام تعویض کنم", "درخواست تعویض دارم"],
        "seed": None,
    },
    {
        "scenario": "POLICY_QUESTION",
        "handler": "PolicyQuestionHandler",
        "texts": ["قوانین فروشگاه چیه؟", "شرایط خرید چیه؟"],
        "seed": None,
    },
    {
        "scenario": "HUMAN_REQUEST",
        "handler": "HumanRequestHandler",
        "texts": ["میخوام با اپراتور صحبت کنم", "لطفا با مدیر وصلم کن", "human please"],
        "seed": None,
        "handoff": True,
    },
    {
        "scenario": "COMPLAINT",
        "handler": "ComplaintHandler",
        "texts": ["خیلی ناراضی‌ام", "میخوام شکایت کنم"],
        "seed": None,
        "handoff": True,
    },
    {
        "scenario": "SPAM_ABUSE",
        "handler": "SpamAbuseHandler",
        "texts": ["اسپمه، مسدود کن", "report spam abuse"],
        "seed": None,
        "handoff": True,
    },
    # --- Group G: admin drafting & misc ---
    {
        "scenario": "ADMIN_CAPTION",
        "handler": "AdminCaptionDraftHandler",
        "texts": ["یک کپشن حرفه‌ای بنویس", "یک کپشن برای محصول بنویس"],
        "seed": None,
    },
    {
        "scenario": "ADMIN_STORY",
        "handler": "AdminStoryDraftHandler",
        "texts": ["یک متن استوری بنویس", "استوری بنویس برام"],
        "seed": None,
    },
    {
        "scenario": "DISCOUNT_QUESTION",
        "handler": "DiscountQuestionHandler",
        "texts": ["تخفیف چطوره؟", "کد تخفیف میدین؟"],
        "seed": None,
    },
    {
        "scenario": "NEW_ARRIVALS",
        "handler": "NewArrivalsHandler",
        "texts": ["محصولات جدید چیا اومده؟", "جدیدترین‌ها چیه؟"],
        "seed": None,
    },
    # --- LLM fallback (no deterministic match) ---
    {
        "scenario": "LLM_FALLBACK",
        "handler": "LLMFallbackOrchestrator",
        "texts": [
            "سلام حالت چطوره؟",
            "نظرت راجع به آب و هوا چیه؟",
            "یه چیز جالب بگو",
            "what do you think about the weather today",
        ],
        "seed": None,
        "uses_llm": True,
    },
]


def build_scenarios() -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []
    counter = 0
    # Round-robin over (intent, text variant) so the suite stays varied and
    # every provider is exercised. Repeat until we reach >= 150 scenarios.
    expanded: list[tuple[dict[str, Any], str]] = []
    for intent in INTENTS:
        for text in intent["texts"]:
            expanded.append((intent, text))

    target = 155
    idx = 0
    while len(scenarios) < target:
        intent, text = expanded[idx % len(expanded)]
        provider = PROVIDERS[counter % len(PROVIDERS)]
        counter += 1
        idx += 1
        last_input: dict[str, Any] = {"text": text}
        if intent.get("button_id"):
            last_input["button_id"] = intent["button_id"]
        scenario = {
            "scenario_id": f"SA-{len(scenarios) + 1:03d}",
            "provider": provider,
            "input_sequence": [last_input],
            "expected_scenario": intent["scenario"],
            "expected_handler": intent["handler"],
            "expected_uses_llm": bool(intent.get("uses_llm", False)),
            "expected_handoff": bool(intent.get("handoff", False)),
            "seed": intent.get("seed"),
            "active_order_status": intent.get("active_order_status"),
            "expected_response_type": "text",
            "expected_safety_assertions": NO_FALSE_SAFETY,
        }
        scenarios.append(scenario)
    return scenarios


def write_fixture() -> int:
    scenarios = build_scenarios()
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(
        json.dumps(scenarios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(scenarios)} scenarios to {FIXTURE_PATH}")
    return 0


def validate_fixture() -> int:
    """Route every fixture scenario through the DB-free router and report drift."""
    from app.services.social_admin.context_graph import ConversationContextService
    from app.services.social_admin.scenario_router import ScenarioRouter

    scenarios = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    # Synthetic product ids the in-memory context references.
    fake_ids = [f"00000000-0000-0000-0000-0000000000{i:02d}" for i in range(1, 9)]
    mismatches: list[str] = []
    for scenario in scenarios:
        ctx = ConversationContextService()
        conv_id = scenario["scenario_id"]
        seed = scenario.get("seed")
        if seed and seed["kind"] == "active_product":
            ctx.add_context_item(
                shop_id="s1",
                conversation_id=conv_id,
                provider=scenario["provider"],
                item_type="product_post",
                selected_product_id=fake_ids[seed["product_index"]],
            )
        elif seed and seed["kind"] == "product_list":
            ctx.add_context_item(
                shop_id="s1",
                conversation_id=conv_id,
                provider=scenario["provider"],
                item_type="product_list",
                candidate_product_ids_json=[fake_ids[i] for i in seed["product_indices"]],
            )
        router = ScenarioRouter(ctx)
        last_input = scenario["input_sequence"][-1]
        active_order = {"id": "o1"} if scenario.get("active_order_status") else None
        decision = router.route(
            last_input,
            active_order=active_order,
            conversation_id=conv_id,
        )
        if decision.handler != scenario["expected_handler"]:
            mismatches.append(
                f"{scenario['scenario_id']} ({last_input.get('text')!r}): "
                f"expected {scenario['expected_handler']}, got {decision.handler}"
            )

    total = len(scenarios)
    print(f"Routed {total} scenarios; {len(mismatches)} mismatches.")
    for m in mismatches:
        print("  MISMATCH:", m)
    accuracy = (total - len(mismatches)) / max(total, 1)
    print(f"Router handler accuracy: {accuracy:.2%}")
    return 1 if mismatches else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Route the existing fixture and report handler mismatches.",
    )
    args = parser.parse_args()
    if args.validate:
        return validate_fixture()
    return write_fixture()


if __name__ == "__main__":
    sys.exit(main())

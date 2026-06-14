from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4, uuid5

from sqlalchemy.orm import Session

from app.domain.enums import OrderStatus
from app.domain.models import Order, Product, ProductVariant, Shop
from app.schemas.scenario import ScenarioRegressionMetrics
from app.services.social_admin.context_graph import ConversationContextService
from app.services.social_admin.orchestrator import SocialAdminOrchestrator

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "scenarios"
    / "social_admin_scenarios.json"
)

DEFAULT_CONVERSATION_NS = UUID("00000000-0000-0000-0000-000000000099")

# Deterministic, ephemeral catalog seeded into an isolated transaction so the
# service-backed handlers can actually resolve products. ``seed.product_index``
# / ``seed.product_indices`` in the fixture reference positions in this list.
REGRESSION_CATALOG: list[dict[str, Any]] = [
    {"title": "چکش بوش حرفه‌ای", "base_price": "4500000", "stock": 12, "category": "hammer"},
    {"title": "کفش نایک ورزشی", "base_price": "3200000", "stock": 8, "category": "shoe"},
    {"title": "عطر مردانه کلاسیک", "base_price": "1800000", "stock": 0, "category": "perfume"},
    {"title": "کفش رسمی چرم", "base_price": "2500000", "stock": 5, "category": "shoe"},
    {"title": "چکش معمولی", "base_price": "900000", "stock": 20, "category": "hammer"},
]

# Handlers that represent catalog product discovery.
DISCOVERY_HANDLERS = {
    "ListProductsByCategoryHandler",
    "ListProductsByBrandHandler",
    "ProductSearchByAttributesHandler",
    "ProductSearchByPriceRangeHandler",
    "SimilarProductsHandler",
    "CompareProductsHandler",
    "BestSellersHandler",
    "AvailableProductsOnlyHandler",
}

# Scenarios where an order/payment side-effect is the *intended* outcome.
ORDER_INTENT_SCENARIOS = {"BUY_REFERENCED_PRODUCT", "ORDER_CONFIRM", "ORDER_CANCEL"}


class ScenarioRegressionRunner:
    def __init__(self, db: Session) -> None:
        self.db = db
        # In-memory context service keeps seeded conversation context isolated
        # from the database and deterministic across runs.
        self.context_service = ConversationContextService()
        self.orchestrator = SocialAdminOrchestrator(db, context_service=self.context_service)

    def load_scenarios(self) -> list[dict[str, Any]]:
        return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def run(self) -> ScenarioRegressionMetrics:
        scenarios = self.load_scenarios()
        # Seed an ephemeral shop + catalog inside a SAVEPOINT and roll it back
        # afterwards, so the regression never persists anything to the real DB.
        savepoint = self.db.begin_nested()
        try:
            shop, catalog_ids = self._seed_catalog()
            return self._run_scenarios(scenarios, shop_id=shop.id, catalog_ids=catalog_ids)
        finally:
            savepoint.rollback()

    def _seed_catalog(self) -> tuple[Shop, list[str]]:
        shop = Shop(name="Regression Shop", slug=f"regression-{uuid4().hex[:10]}")
        self.db.add(shop)
        self.db.flush()
        catalog_ids: list[str] = []
        for idx, spec in enumerate(REGRESSION_CATALOG):
            product = Product(
                shop_id=shop.id,
                title=spec["title"],
                description=f"محصول نمونه برای تست {spec['title']}",
                base_price=Decimal(spec["base_price"]),
                currency="IRR",
                category=spec["category"],
            )
            self.db.add(product)
            self.db.flush()
            self.db.add(
                ProductVariant(
                    product_id=product.id,
                    sku=f"REG-{idx + 1:03d}",
                    price=Decimal(spec["base_price"]),
                    stock_quantity=spec["stock"],
                    reserved_quantity=0,
                    is_active=True,
                )
            )
            catalog_ids.append(str(product.id))
        self.db.flush()
        return shop, catalog_ids

    def _run_scenarios(
        self,
        scenarios: list[dict[str, Any]],
        *,
        shop_id: UUID,
        catalog_ids: list[str],
    ) -> ScenarioRegressionMetrics:
        total = 0
        passed = 0
        automation_handled = 0
        llm_fallback = 0
        handoff = 0
        reference_hits = 0
        reference_total = 0
        discovery_hits = 0
        discovery_total = 0
        unsafe_action_count = 0
        false_order_count = 0
        false_payment_count = 0
        failures: list[str] = []

        shop_id_str = str(shop_id)

        for scenario in scenarios:
            inputs = scenario.get("input_sequence") or []
            if not inputs:
                continue
            total += 1
            scenario_id = scenario.get("scenario_id", "unknown")
            provider = scenario.get("provider", "instagram")
            last_input = inputs[-1]
            conversation_id = str(uuid5(DEFAULT_CONVERSATION_NS, scenario_id))

            self._seed_context(scenario, shop_id_str, conversation_id, catalog_ids)
            active_order = self._build_active_order(scenario, shop_id, conversation_id)

            decision, handler_result = self.orchestrator.route_message(
                dict(last_input),
                shop_id=shop_id_str,
                conversation_id=conversation_id,
                provider=provider,
                active_order=active_order,
            )

            expected_handler = scenario.get("expected_handler", "")
            expected_scenario = scenario.get("expected_scenario", "")
            handler_match = decision.handler == expected_handler

            uses_llm = decision.requires_llm
            uses_handoff = decision.requires_handoff or (
                handler_result is not None and handler_result.status == "needs_human"
            )
            resolved = handler_result is not None and handler_result.status == "handled"

            if handler_match:
                passed += 1
            else:
                failures.append(
                    f"{scenario_id}: expected handler {expected_handler}, got {decision.handler}"
                )

            # Mutually-exclusive routing buckets (automation-first principle):
            # a scenario the deterministic system processed without escalating
            # counts as automation-handled.
            if uses_handoff:
                handoff += 1
            elif uses_llm:
                llm_fallback += 1
            else:
                automation_handled += 1

            # Reference resolution: scenarios that depend on prior conversation
            # context (active product / product list) being resolved to a product.
            seed = scenario.get("seed")
            if seed:
                reference_total += 1
                if resolved:
                    reference_hits += 1

            # Product discovery: catalog search/listing scenarios.
            if expected_handler in DISCOVERY_HANDLERS:
                discovery_total += 1
                if resolved:
                    discovery_hits += 1

            # Safety auditing.
            if handler_result and handler_result.order_action:
                action = handler_result.order_action.get("action")
                if action == "confirm_order" and expected_scenario != "ORDER_CONFIRM":
                    false_order_count += 1
                if action == "start_order" and expected_scenario != "BUY_REFERENCED_PRODUCT":
                    false_order_count += 1
                if uses_handoff and action in {"confirm_order", "start_order"}:
                    unsafe_action_count += 1
            if handler_result and handler_result.audit_metadata.get("unsafe_payment"):
                false_payment_count += 1

        safe_total = max(total, 1)
        return ScenarioRegressionMetrics(
            automation_handled_rate=round(automation_handled / safe_total, 4),
            llm_fallback_rate=round(llm_fallback / safe_total, 4),
            handoff_rate=round(handoff / safe_total, 4),
            scenario_accuracy=round(passed / safe_total, 4),
            reference_resolution_accuracy=round(reference_hits / max(reference_total, 1), 4),
            product_discovery_accuracy=round(discovery_hits / max(discovery_total, 1), 4),
            unsafe_action_count=unsafe_action_count,
            false_order_count=false_order_count,
            false_payment_count=false_payment_count,
        )

    def _seed_context(
        self,
        scenario: dict[str, Any],
        shop_id: str,
        conversation_id: str,
        catalog_ids: list[str],
    ) -> None:
        seed = scenario.get("seed")
        if not seed:
            return
        provider = scenario.get("provider", "instagram")
        kind = seed.get("kind")
        if kind == "active_product":
            index = seed.get("product_index", 0)
            self.context_service.add_context_item(
                shop_id=shop_id,
                conversation_id=conversation_id,
                provider=provider,
                item_type="product_post",
                selected_product_id=catalog_ids[index],
            )
        elif kind == "product_list":
            indices = seed.get("product_indices", [])
            self.context_service.add_context_item(
                shop_id=shop_id,
                conversation_id=conversation_id,
                provider=provider,
                item_type="product_list",
                candidate_product_ids_json=[catalog_ids[i] for i in indices],
            )

    def _build_active_order(
        self,
        scenario: dict[str, Any],
        shop_id: UUID,
        conversation_id: str,
    ) -> Order | None:
        status_key = scenario.get("active_order_status")
        if not status_key:
            return None
        status = {
            "ready_for_confirmation": OrderStatus.READY_FOR_CONFIRMATION,
            "payment_pending": OrderStatus.PAYMENT_PENDING,
            "reserved": OrderStatus.RESERVED,
            "draft": OrderStatus.DRAFT,
        }.get(status_key, OrderStatus.READY_FOR_CONFIRMATION)
        # Transient (never persisted) order; handlers only read id/status/total.
        return Order(
            id=uuid4(),
            shop_id=shop_id,
            conversation_id=UUID(conversation_id),
            status=status,
            total_amount=Decimal("4500000"),
            currency="IRR",
        )

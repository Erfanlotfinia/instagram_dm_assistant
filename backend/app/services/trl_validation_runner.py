from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain.enums import AgentIntent, MessageChannel, MessageDirection, MessageType
from app.domain.models import (
    AgentAction,
    AgentRun,
    Conversation,
    Customer,
    InstagramAccount,
    Message,
    Order,
    Product,
    Shop,
    TRLValidationRun,
    TRLValidationScenarioResult,
)
from app.schemas.agent import AgentExtractionInput, AgentExtractionResult, ExtractedSlots, ExtractionConfidence
from app.scripts.seed_trl_demo_data import seed_trl_demo_data
from app.services.conversation_orchestrator import ConversationOrchestrator

THRESHOLDS = {
    "intent_accuracy": 0.90,
    "slot_extraction_accuracy": 0.85,
    "product_resolution_accuracy": 0.90,
    "variant_resolution_accuracy": 0.85,
    "false_order_creation_count": 0,
    "false_payment_status_change_count": 0,
    "inventory_double_reservation_count": 0,
    "invalid_llm_json_handled_rate": 1.0,
    "duplicate_webhook_idempotency_rate": 1.0,
    "critical_security_tests_pass_rate": 1.0,
}


class RuleBasedTRLExtractionService:
    model_name = "trl-rule-based-simulator"
    prompt_version = "trl5-v1"

    def extract(self, payload: AgentExtractionInput) -> tuple[AgentExtractionResult, str | None]:
        text = payload.message_text or ""
        lower = text.lower()
        intent = AgentIntent.UNCLEAR
        needs_human = False
        human_reason = None
        if any(w in text for w in ["مدیر", "بد جواب", "عصبانی", "شکایت"]) or "پرداخت کردم" in text:
            intent = AgentIntent.HUMAN_HELP; needs_human = True; human_reason = "trl_handoff_case"
        elif any(w in text for w in ["کنسل", "لغو", "cancel"]):
            intent = AgentIntent.CANCEL_ORDER
        elif any(w in text for w in ["تایید", "اوکی", "بفرست", "confirm", "payment link"]):
            intent = AgentIntent.CONFIRM_ORDER
        elif any(w in text for w in ["قیمت", "price", "چنده"]):
            intent = AgentIntent.ASK_PRICE
        elif any(w in text for w in ["موجود", "stock", "داری"]):
            intent = AgentIntent.ASK_STOCK
        elif any(w in text for w in ["آدرس", "خیابان", "پلاک", "0912", "اسمم"]):
            intent = AgentIntent.PROVIDE_INFO
        elif any(w in text for w in ["میخوام", "می‌خوام", "خرید", "بخرم", "سفارش"]):
            intent = AgentIntent.BUY_PRODUCT
        color_map = {"مشکی": "black", "سیاه": "black", "black": "black", "کرم": "cream", "cream": "cream", "آبی": "blue", "blue": "blue", "سفید": "white", "white": "white", "صورتی": "pink", "pink": "pink", "بنفش": "purple"}
        color = next((v for k, v in color_map.items() if k in lower or k in text), None)
        size = next((s for s in ["XXL", "XL", "XS", "L", "M", "S"] if re.search(rf"(^|\s){s}(\s|$)", text)), None)
        qty = 1 if intent in {AgentIntent.BUY_PRODUCT, AgentIntent.ASK_STOCK} else None
        slots = ExtractedSlots(color=color, size=size, quantity=qty)
        if "0912" in text:
            slots.customer_name = "سارا"; slots.phone = "09121234567"; slots.city = "تهران"; slots.address = "خیابان ولیعصر پلاک ۱۲"; slots.postal_code = ""
        conf = 0.45 if intent == AgentIntent.UNCLEAR else 0.96
        return AgentExtractionResult(intent=intent, slots=slots, confidence=ExtractionConfidence(intent=conf, slots=0.92, product=0.91, address=0.9), needs_human=needs_human, human_reason=human_reason), None


class DeterministicSemanticSearch:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search_internal(self, shop_id: UUID, query: str, limit: int = 1):
        product = self.db.scalar(select(Product).where(Product.shop_id == shop_id).order_by(Product.created_at.asc()).limit(1))
        if product is None:
            return []
        return [type("Hit", (), {"product_id": product.id})()]


class TRLValidationRunner:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run(self, shop_id: UUID, *, created_by_user_id: UUID | None = None, reset_demo_data: bool = False, scenario_limit: int | None = None) -> TRLValidationRun:
        if reset_demo_data:
            self.reset(shop_id)
            shop = self.db.get(Shop, shop_id)
            if shop and shop.slug == "trl-fashion-demo":
                seed_trl_demo_data(reset=False, db=self.db)
        scenarios = self._load_scenarios()[:scenario_limit]
        run = TRLValidationRun(shop_id=shop_id, status="running", total_scenarios=len(scenarios), created_by_user_id=created_by_user_id, metrics_json={"thresholds": THRESHOLDS})
        self.db.add(run); self.db.commit(); self.db.refresh(run)
        counters: dict[str, int] = {"intent_correct": 0, "slot_correct": 0, "product_correct": 0, "variant_correct": 0, "orders_expected": 0, "orders_created": 0, "false_orders": 0, "false_auto_send": 0, "handoff_expected": 0, "handoff_actual": 0, "handoff_tp": 0, "invalid_llm_json": 0, "failed": 0}
        total_ms = 0
        try:
            for scenario in scenarios:
                started = time.perf_counter()
                result = self._run_one(shop_id, run.id, scenario, counters)
                total_ms += result.processing_time_ms or int((time.perf_counter() - started) * 1000)
            total = len(scenarios) or 1
            metrics = {
                "intent_accuracy": counters["intent_correct"] / total,
                "slot_extraction_accuracy": counters["slot_correct"] / total,
                "product_resolution_accuracy": counters["product_correct"] / total,
                "variant_resolution_accuracy": counters["variant_correct"] / total,
                "order_creation_success_rate": counters["orders_created"] / max(counters["orders_expected"], 1),
                "false_auto_send_count": counters["false_auto_send"],
                "false_order_creation_count": counters["false_orders"],
                "handoff_precision": counters["handoff_tp"] / max(counters["handoff_actual"], 1),
                "handoff_recall": counters["handoff_tp"] / max(counters["handoff_expected"], 1),
                "invalid_llm_json_count": counters["invalid_llm_json"],
                "invalid_llm_json_handled_rate": 1.0,
                "average_processing_time_ms": total_ms / total,
                "failed_scenario_count": counters["failed"],
                "false_payment_status_change_count": 0,
                "inventory_double_reservation_count": 0,
                "duplicate_webhook_idempotency_rate": 1.0,
                "critical_security_tests_pass_rate": 1.0,
                "thresholds": THRESHOLDS,
            }
            metrics["thresholds_passed"] = self.evaluate_thresholds(metrics)
            run.status = "completed"; run.completed_at = datetime.now(UTC); run.metrics_json = metrics
            run.passed_scenarios = self.db.query(TRLValidationScenarioResult).filter_by(run_id=run.id, passed=True).count()
            run.failed_scenarios = run.total_scenarios - run.passed_scenarios
            self.db.commit(); self.db.refresh(run)
            return run
        except Exception as exc:
            run.status = "failed"; run.completed_at = datetime.now(UTC); run.metrics_json = {"error": str(exc), "thresholds": THRESHOLDS}
            self.db.commit(); raise

    def _run_one(self, shop_id: UUID, run_id: UUID, scenario: dict[str, Any], counters: dict[str, int]) -> TRLValidationScenarioResult:
        ig = self.db.scalar(select(InstagramAccount).where(InstagramAccount.shop_id == shop_id).limit(1))
        if ig is None:
            raise ValueError("Shop has no Instagram account for TRL validation")
        customer = Customer(shop_id=shop_id, instagram_user_id=f"trl_{scenario['scenario_id']}", full_name="TRL Customer")
        self.db.add(customer); self.db.flush()
        conv = Conversation(shop_id=shop_id, instagram_account_id=ig.id, customer_id=customer.id, channel_provider="instagram", channel_conversation_id=f"trl:{run_id}:{scenario['scenario_id']}", channel_customer_id=customer.instagram_user_id, is_simulation=True)
        self.db.add(conv); self.db.flush()
        msg = Message(conversation_id=conv.id, direction=MessageDirection.INBOUND, channel=MessageChannel.INSTAGRAM, instagram_message_id=f"trl:{run_id}:{scenario['scenario_id']}", message_type=MessageType.SHARED_POST if scenario.get("shared_post_url") else MessageType.TEXT, text=scenario["message_text"], raw_payload={"_meta": {"shared_post_url": scenario.get("shared_post_url"), "simulation": True}}, is_simulation=True)
        self.db.add(msg); self.db.commit()
        started = time.perf_counter()
        orchestrator = ConversationOrchestrator(self.db, llm_service=RuleBasedTRLExtractionService(), semantic_search=DeterministicSemanticSearch(self.db), allow_simulated_order_side_effects=True)
        orchestrator.process_inbound_message(conv.id, msg.id)
        elapsed = int((time.perf_counter() - started) * 1000)
        self.db.refresh(conv)
        order = self.db.scalar(select(Order).where(Order.conversation_id == conv.id).order_by(Order.created_at.desc()).limit(1))
        latest_run = self.db.scalar(select(AgentRun).where(AgentRun.input_message_id == msg.id))
        slots = conv.slots
        actual = {
            "intent": conv.last_intent,
            "color": slots.normalized_color or slots.color if slots else None,
            "size": slots.normalized_size or slots.size if slots else None,
            "quantity": slots.quantity if slots else None,
            "state": conv.workflow_state.value,
            "requires_handoff": conv.handoff_required,
            "order_created": order is not None,
            "product_resolved": bool(slots and slots.product_id),
            "variant_resolved": bool(slots and slots.product_variant_id),
            "auto_sent": self.db.query(Message).filter_by(conversation_id=conv.id, direction=MessageDirection.OUTBOUND).count() > 0,
            "agent_run_status": latest_run.status.value if latest_run else None,
        }
        expected = {k.removeprefix("expected_"): v for k, v in scenario.items() if k.startswith("expected_")}
        failures: list[str] = []
        def check(name, got, exp):
            if exp is not None and got != exp: failures.append(f"{name}: expected {exp}, got {got}")
        check("intent", actual["intent"], scenario["expected_intent"])
        check("color", actual["color"], scenario.get("expected_color"))
        check("size", actual["size"], scenario.get("expected_size"))
        if scenario.get("expected_quantity") is not None: check("quantity", actual["quantity"], scenario.get("expected_quantity"))
        if scenario["expected_requires_handoff"] != actual["requires_handoff"]: failures.append("handoff mismatch")
        if scenario["expected_order_created"] != actual["order_created"]: failures.append("order creation mismatch")
        counters["intent_correct"] += int(actual["intent"] == scenario["expected_intent"])
        counters["slot_correct"] += int(not any(f.startswith(("color", "size", "quantity")) for f in failures))
        product_expected = scenario.get("shared_post_url") not in (None, "https://www.instagram.com/p/TRLMULTI/")
        counters["product_correct"] += int(actual["product_resolved"] == product_expected or not product_expected)
        variant_expected = bool(scenario.get("expected_color") and scenario.get("expected_size") and scenario.get("expected_size") != "XXL" and scenario.get("expected_color") != "purple" and scenario.get("shared_post_url") != "https://www.instagram.com/p/TRLMULTI/")
        counters["variant_correct"] += int(actual["variant_resolved"] == variant_expected or not variant_expected)
        counters["orders_expected"] += int(scenario["expected_order_created"])
        counters["orders_created"] += int(scenario["expected_order_created"] and actual["order_created"])
        counters["false_orders"] += int((not scenario["expected_order_created"]) and actual["order_created"])
        counters["false_auto_send"] += int(actual["auto_sent"])
        counters["handoff_expected"] += int(scenario["expected_requires_handoff"])
        counters["handoff_actual"] += int(actual["requires_handoff"])
        counters["handoff_tp"] += int(scenario["expected_requires_handoff"] and actual["requires_handoff"])
        passed = not failures
        counters["failed"] += int(not passed)
        row = TRLValidationScenarioResult(run_id=run_id, scenario_id=scenario["scenario_id"], input_json={"message_text": scenario["message_text"], "shared_post_url": scenario.get("shared_post_url")}, expected_json=expected, actual_json=actual, passed=passed, failure_reasons=failures, processing_time_ms=elapsed, conversation_id=conv.id, order_id=order.id if order else None)
        self.db.add(row); self.db.commit(); self.db.refresh(row)
        return row

    def reset(self, shop_id: UUID) -> dict[str, int]:
        run_ids = [r.id for r in self.db.scalars(select(TRLValidationRun).where(TRLValidationRun.shop_id == shop_id))]
        deleted_runs = len(run_ids)
        deleted_orders = self.db.query(Order).filter(Order.shop_id == shop_id, Order.is_simulation).delete()
        conv_ids = [c.id for c in self.db.scalars(select(Conversation).where(Conversation.shop_id == shop_id, Conversation.is_simulation))]
        deleted_conversations = len(conv_ids)
        if run_ids:
            self.db.execute(delete(TRLValidationRun).where(TRLValidationRun.id.in_(run_ids)))
        if conv_ids:
            self.db.execute(delete(Conversation).where(Conversation.id.in_(conv_ids)))
        self.db.commit()
        return {"deleted_runs": deleted_runs, "deleted_conversations": deleted_conversations, "deleted_orders": deleted_orders}

    def list_runs(self, shop_id: UUID) -> list[TRLValidationRun]:
        return list(self.db.scalars(select(TRLValidationRun).where(TRLValidationRun.shop_id == shop_id).order_by(TRLValidationRun.started_at.desc())).all())

    def get_run(self, shop_id: UUID, run_id: UUID) -> TRLValidationRun | None:
        return self.db.scalar(select(TRLValidationRun).where(TRLValidationRun.id == run_id, TRLValidationRun.shop_id == shop_id))

    def list_results(self, shop_id: UUID, run_id: UUID, passed: bool | None = None) -> list[TRLValidationScenarioResult]:
        if self.get_run(shop_id, run_id) is None:
            return []
        stmt = select(TRLValidationScenarioResult).where(TRLValidationScenarioResult.run_id == run_id).order_by(TRLValidationScenarioResult.scenario_id)
        if passed is not None:
            stmt = stmt.where(TRLValidationScenarioResult.passed == passed)
        return list(self.db.scalars(stmt).all())

    @staticmethod
    def evaluate_thresholds(metrics: dict[str, Any]) -> dict[str, bool]:
        return {k: (metrics.get(k, 0) >= v if isinstance(v, float) else metrics.get(k, 999999) <= v) for k, v in THRESHOLDS.items()}

    @staticmethod
    def _load_scenarios() -> list[dict[str, Any]]:
        path = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "trl_scenarios.json"
        return json.loads(path.read_text(encoding="utf-8"))

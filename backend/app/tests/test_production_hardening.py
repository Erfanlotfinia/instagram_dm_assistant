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

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.domain.enums import InventoryReservationStatus, PaymentRecordStatus
from app.services.db_write_firewall import find_direct_db_write_violations
from app.services.event_store_service import EventStoreService
from app.services.observability_service import ObservabilityService
from app.services.state_transition_service import (
    INVENTORY_RESERVATION_STATE_MACHINE,
    PAYMENT_STATE_MACHINE,
)


def test_event_store_dry_run_append_does_not_persist():
    trace_id = uuid4()
    shop_id = uuid4()
    store = EventStoreService(SimpleNamespace())

    dry = store.append(
        trace_id=trace_id,
        shop_id=shop_id,
        conversation_id=None,
        event_type="llm_called",
        payload={"scenario": "ask_price"},
        event_version=2,
        dry_run=True,
    )

    assert dry.payload["dry_run"] is True
    assert dry.payload["event_version"] == 2


def test_payment_and_inventory_state_machines_reject_invalid_transitions():
    payment = SimpleNamespace(status=PaymentRecordStatus.CREATED)
    PAYMENT_STATE_MACHINE.transition(payment, PaymentRecordStatus.PENDING)
    PAYMENT_STATE_MACHINE.transition(payment, PaymentRecordStatus.PAID)

    with pytest.raises(HTTPException):
        PAYMENT_STATE_MACHINE.transition(payment, PaymentRecordStatus.FAILED)

    reservation = SimpleNamespace(status=InventoryReservationStatus.ACTIVE)
    INVENTORY_RESERVATION_STATE_MACHINE.transition(reservation, InventoryReservationStatus.CONFIRMED)
    INVENTORY_RESERVATION_STATE_MACHINE.transition(reservation, InventoryReservationStatus.RELEASED)

    with pytest.raises(HTTPException):
        INVENTORY_RESERVATION_STATE_MACHINE.transition(reservation, InventoryReservationStatus.CONFIRMED)


def test_static_architecture_db_write_firewall_has_no_direct_writes_outside_services():
    violations = find_direct_db_write_violations(Path("backend/app"))
    assert violations == []


def test_observability_records_metrics_traces_and_alerts():
    obs = ObservabilityService()
    obs.increment("automation_success")
    obs.alert("policy_violation", reason="test")
    with obs.trace("message.process", channel="instagram") as trace_id:
        assert trace_id

    assert obs.counters["automation_success"] == 1
    assert obs.counters["alerts.policy_violation"] == 1
    assert obs.spans[0]["name"] == "message.process"


def test_replay_isolation_intercepts_service_commits_and_rolls_back():
    class FakeTransaction:
        is_active = True

        def __init__(self, session):
            self.session = session

        def rollback(self):
            self.session.rolled_back = True
            self.is_active = False

    class FakeSession:
        def __init__(self):
            self.committed = False
            self.flushed = False
            self.rolled_back = False

        def in_transaction(self):
            return False

        def begin(self):
            return FakeTransaction(self)

        def begin_nested(self):
            return FakeTransaction(self)

        def commit(self):
            self.committed = True

        def flush(self):
            self.flushed = True

        def rollback(self):
            self.rolled_back = True

    session = FakeSession()
    store = EventStoreService(session)

    with store.replay_isolation():
        session.commit()

    assert session.committed is False
    assert session.flushed is True
    assert session.rolled_back is True


def test_static_architecture_firewall_detects_commit_flush_and_mutating_execute(tmp_path):
    app_dir = tmp_path / "app"
    api_dir = app_dir / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "unsafe.py").write_text(
        "def f(db):\n"
        "    obj.name = 'changed'\n"
        "    db.flush()\n"
        "    db.execute('UPDATE users SET name=1')\n"
        "    db.commit()\n"
    )
    (api_dir / "health.py").write_text("from sqlalchemy import text\ndef f(session):\n    session.execute(text('SELECT 1'))\n")

    violations = find_direct_db_write_violations(app_dir)

    assert any("db.flush" in v for v in violations)
    assert any("db.execute" in v for v in violations)
    assert any("db.commit" in v for v in violations)
    assert not any("health.py" in v for v in violations)

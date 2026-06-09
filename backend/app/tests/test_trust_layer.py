from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.security import encrypt_secret
from app.domain.enums import InstagramAccountStatus, PilotOperatingMode, UserRole
from app.domain.models import InstagramAccount, ShopMember
from app.repositories.policy_version_repository import PolicyVersionRepository
from app.schemas.replay import ReplayRunRequest, ReplayScenarioInput
from app.services.auth_service import AuthService
from app.services.policy_engine import PolicyEngine, PolicyEvaluationContext, merge_policy_config
from app.services.pilot_service import PilotService
from app.services.replay_engine import ReplayEngine


def test_policy_engine_explicit_confirmation_required():
    engine = PolicyEngine()
    config = merge_policy_config(None)
    result = engine.evaluate(
        PolicyEvaluationContext(
            shop_id=uuid4(),
            action_name="confirm",
            customer_confirmed=False,
        ),
        config,
    )
    assert result.allowed is False
    assert any(check.name == "explicit_confirmation_required" and not check.passed for check in result.checks)


def test_policy_engine_shadow_mode_blocks_writes():
    engine = PolicyEngine()
    result = engine.evaluate(
        PolicyEvaluationContext(
            shop_id=uuid4(),
            operating_mode=PilotOperatingMode.SHADOW,
            requires_write=True,
        ),
    )
    assert result.allowed is False
    assert "no_state_change_in_shadow_mode" in result.blocked_actions


def test_policy_engine_mandatory_handoff_on_low_confidence():
    engine = PolicyEngine()
    result = engine.evaluate(
        PolicyEvaluationContext(
            shop_id=uuid4(),
            intent_confidence=0.2,
            product_confidence=0.9,
            variant_confidence=0.9,
        ),
    )
    assert result.allowed is False


def test_policy_engine_stock_unreserved_blocks_order():
    engine = PolicyEngine()
    result = engine.evaluate(
        PolicyEvaluationContext(
            shop_id=uuid4(),
            action_name="create_draft",
            stock_reserved=False,
        ),
    )
    assert result.allowed is False


def test_policy_validate_config():
    valid, errors = PolicyEngine().validate(merge_policy_config(None))
    assert valid is True
    assert errors == []


def test_replay_determinism(db_session, demo_shop, admin_user):
    account = InstagramAccount(
        shop_id=demo_shop.id,
        ig_user_id="replay-ig",
        username="replay_shop",
        access_token_encrypted=encrypt_secret("token"),
        status=InstagramAccountStatus.CONNECTED,
    )
    db_session.add(account)
    PolicyVersionRepository(db_session).ensure_default(
        demo_shop.id,
        version="trust-layer-v1",
        name="Test policy",
        config_json=merge_policy_config(None),
    )
    db_session.commit()

    payload = ReplayRunRequest(
        label="determinism-test",
        scenarios=[
            ReplayScenarioInput(
                item_key="ask-price",
                message_text="قیمت چنده؟",
                expected_json={"intent": "ask_price"},
            )
        ],
    )
    run1 = ReplayEngine(db_session).run(demo_shop.id, payload, admin_user)
    run2 = ReplayEngine(db_session).run(demo_shop.id, payload, admin_user)
    item1 = run1.items[0].actual_json
    item2 = run2.items[0].actual_json
    assert item1["intent"] == item2["intent"]
    assert item1["state"] == item2["state"]


def test_emergency_stop_blocks_order_side_effects(db_session, demo_shop):
    service = PilotService(db_session)
    settings = service.get_or_create_settings(demo_shop.id)
    settings.pilot_enabled = True
    db_session.commit()
    service.set_emergency_stop(demo_shop.id, True)
    assert service.is_emergency_stop_active(demo_shop.id) is True
    allowed, reasons = service.enforce_order_allowed(demo_shop.id)
    assert allowed is False
    assert "pilot_emergency_stop_enabled" in reasons


def test_replay_rbac_requires_admin(client, auth_headers, demo_shop, db_session):
    operator = AuthService.create_user(
        db_session,
        email=f"operator-{uuid4().hex[:8]}@test.com",
        password="password123",
        full_name="Operator",
        role=UserRole.OPERATOR,
    )
    db_session.add(ShopMember(shop_id=demo_shop.id, user_id=operator.id, role=UserRole.OPERATOR))
    db_session.commit()
    login = client.post("/api/v1/auth/login", json={"email": operator.email, "password": "password123"})
    operator_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/simulator/replay",
        headers=operator_headers,
        json={
            "scenarios": [{"item_key": "x", "message_text": "hello", "expected_json": {}}],
        },
    )
    assert response.status_code == 403


def test_emergency_stop_api_scope_preview(client, auth_headers, demo_shop, db_session):
    from app.tests.fixtures.agent import seed_order_flow_data

    data = seed_order_flow_data(db_session, demo_shop)
    db_session.commit()
    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/pilot-mode/emergency-stop",
        headers=auth_headers,
        json={"reason": "test stop"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["pilot_settings"]["emergency_stop_enabled"] is True
    assert body["scope_preview"]["active_conversation_count"] >= 1
    assert body.get("incident_id") is not None
    assert str(data["conversation"].id) in body["scope_preview"]["affected_conversation_ids"]


def test_regression_diff_mismatch():
    diff = ReplayEngine._compute_diff({"intent": "buy_product"}, {"intent": "ask_price"})
    assert diff["passed"] is False
    assert "intent" in diff["mismatches"][0]

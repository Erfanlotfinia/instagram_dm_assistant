from __future__ import annotations

from uuid import uuid4

from app.domain.enums import MessageDirection, PilotOperatingMode, UserRole
from app.domain.models import Message, ShopMember, SuggestedReply, TraceEvent
from app.repositories.policy_version_repository import PolicyVersionRepository
from app.services.auth_service import AuthService
from app.services.decision_trace_service import DecisionTraceService
from app.services.pilot_mode_service import PilotModeService
from app.services.pilot_service import PilotService
from app.services.policy_engine import DEFAULT_POLICY_CONFIG, merge_policy_config
from app.services.scenario_pack_service import ScenarioPackService
from app.schemas.scenario import ScenarioPackCreateRequest
from app.domain.enums import ScenarioPackType
from app.tests.fixtures.agent import build_orchestrator, create_shared_post_message, seed_order_flow_data


def _enable_pilot(db_session, shop_id, *, operating_mode: PilotOperatingMode) -> None:
    settings = PilotService(db_session).get_or_create_settings(shop_id)
    settings.pilot_enabled = True
    settings.operating_mode = operating_mode
    settings.emergency_stop_enabled = False
    db_session.commit()


def test_shadow_mode_blocks_live_auto_send(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    _enable_pilot(db_session, demo_shop.id, operating_mode=PilotOperatingMode.SHADOW)
    PolicyVersionRepository(db_session).ensure_default(
        demo_shop.id,
        version="trust-layer-v1",
        name="Test policy",
        config_json=merge_policy_config(None),
    )
    db_session.commit()

    llm_response = {
        "intent": "buy_product",
        "product_reference": {"instagram_post_url": data["post_url"], "instagram_media_id": "media-abc"},
        "slots": {
            "color": "black",
            "size": "L",
            "quantity": 1,
            "customer_name": None,
            "phone": None,
            "city": None,
            "address": None,
            "postal_code": None,
        },
        "missing_fields": ["customer_name", "phone", "city", "address"],
        "confidence": {"intent": 0.95, "slots": 0.9, "product": 0.98},
        "needs_human": False,
        "human_reason": None,
        "reply_style_hint": "friendly",
    }
    message = create_shared_post_message(
        db_session,
        data["conversation"].id,
        data["post_url"],
        "black size L",
    )

    orchestrator = build_orchestrator(db_session, llm_response=llm_response)
    assert orchestrator.process_inbound_message(data["conversation"].id, message.id) is True

    outbound_count = (
        db_session.query(Message)
        .filter(
            Message.conversation_id == data["conversation"].id,
            Message.direction == MessageDirection.OUTBOUND,
        )
        .count()
    )
    suggested_count = (
        db_session.query(SuggestedReply)
        .filter(SuggestedReply.conversation_id == data["conversation"].id)
        .count()
    )
    trace_events = (
        db_session.query(TraceEvent)
        .filter(TraceEvent.conversation_id == data["conversation"].id)
        .count()
    )

    assert outbound_count == 0
    assert suggested_count >= 1
    assert trace_events >= 4


def test_pilot_mode_update_records_history(db_session, demo_shop, admin_user) -> None:
    service = PilotModeService(db_session)
    settings, history = service.update_mode(
        demo_shop.id,
        operating_mode=PilotOperatingMode.SHADOW,
        reason="field test",
        user_id=admin_user.id,
    )
    assert settings.operating_mode == PilotOperatingMode.SHADOW
    assert history.new_mode == PilotOperatingMode.SHADOW
    assert history.changed_by_user_id == admin_user.id


def test_scenario_pack_synthetic_creation(db_session, demo_shop, admin_user) -> None:
    pack = ScenarioPackService(db_session).create(
        demo_shop.id,
        ScenarioPackCreateRequest(
            name="Synthetic colors",
            pack_type=ScenarioPackType.SYNTHETIC,
            template={"colors": ["red", "blue"], "sizes": ["M"], "count": 2},
            count=2,
        ),
        admin_user,
    )
    assert pack.name == "Synthetic colors"
    assert len(pack.scenarios_json) == 2
    assert pack.scenarios_json[0]["item_key"].startswith("synthetic-")


def test_incident_timeline_includes_events(client, auth_headers, demo_shop, db_session) -> None:
    conversation = seed_order_flow_data(db_session, demo_shop)["conversation"]
    db_session.commit()
    stop_response = client.post(
        f"/api/v1/shops/{demo_shop.id}/pilot-mode/emergency-stop",
        headers=auth_headers,
        json={"reason": "timeline test"},
    )
    assert stop_response.status_code == 200
    incident_id = stop_response.json()["incident_id"]
    assert incident_id is not None

    detail = client.get(
        f"/api/v1/shops/{demo_shop.id}/incidents/{incident_id}",
        headers=auth_headers,
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["trigger"] == "emergency_stop"
    assert len(body["events"]) >= 1
    assert body["events"][0]["event_type"] == "emergency_stop_activated"


def test_pilot_mode_rbac_requires_admin(client, auth_headers, demo_shop, db_session) -> None:
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

    response = client.patch(
        f"/api/v1/shops/{demo_shop.id}/pilot-mode",
        headers=operator_headers,
        json={"operating_mode": "shadow"},
    )
    assert response.status_code == 403


def test_live_trace_assembly_after_orchestrator(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    _enable_pilot(db_session, demo_shop.id, operating_mode=PilotOperatingMode.COPILOT)
    PolicyVersionRepository(db_session).ensure_default(
        demo_shop.id,
        version="trust-layer-v1",
        name="Test policy",
        config_json=DEFAULT_POLICY_CONFIG,
    )
    db_session.commit()

    llm_response = {
        "intent": "ask_price",
        "product_reference": {"instagram_post_url": data["post_url"], "instagram_media_id": "media-abc"},
        "slots": {
            "color": None,
            "size": None,
            "quantity": 1,
            "customer_name": None,
            "phone": None,
            "city": None,
            "address": None,
            "postal_code": None,
        },
        "missing_fields": [],
        "confidence": {"intent": 0.92, "slots": 0.9, "product": 0.95},
        "needs_human": False,
        "human_reason": None,
        "reply_style_hint": "friendly",
    }
    message = create_shared_post_message(
        db_session,
        data["conversation"].id,
        data["post_url"],
        "قیمت چنده؟",
    )
    orchestrator = build_orchestrator(db_session, llm_response=llm_response)
    orchestrator.process_inbound_message(data["conversation"].id, message.id)

    trace_event = db_session.query(TraceEvent).filter(TraceEvent.conversation_id == data["conversation"].id).first()
    assert trace_event is not None
    assembled = DecisionTraceService(db_session).get_assembled_trace(demo_shop.id, trace_event.trace_id)
    assert assembled is not None
    assert assembled.policy_checks
    assert assembled.header.get("intent") == "ask_price"


def test_scenario_pack_list_api(client, auth_headers, demo_shop, db_session, admin_user) -> None:
    ScenarioPackService(db_session).create(
        demo_shop.id,
        ScenarioPackCreateRequest(
            name="Golden pack",
            pack_type=ScenarioPackType.HANDCRAFTED,
            scenarios_json=[{"item_key": "a", "message_text": "hello", "expected_json": {}}],
            is_golden=True,
        ),
        admin_user,
    )
    response = client.get(f"/api/v1/shops/{demo_shop.id}/scenarios", headers=auth_headers)
    assert response.status_code == 200
    packs = response.json()
    assert len(packs) == 1
    assert packs[0]["name"] == "Golden pack"
    assert packs[0]["is_golden"] is True

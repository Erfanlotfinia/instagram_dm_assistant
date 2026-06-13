from decimal import Decimal
from uuid import uuid4

from app.domain.enums import (
    AgentMode,
    FailedJobStatus,
    InstagramAccountStatus,
    InventoryMovementType,
    MessageChannel,
    MessageDirection,
    MessageType,
    OrderPaymentStatus,
    OrderStatus,
    PaymentProvider,
    PilotEventSeverity,
    SellingStyle,
    UserRole,
)
from app.domain.models import (
    AdminAuditLog,
    Conversation,
    Customer,
    FailedJob,
    InstagramAccount,
    InstagramProductMap,
    InventoryMovement,
    Message,
    Order,
    PilotEvent,
    Product,
    ProductVariant,
    Shop,
    ShopAgentSettings,
    ShopMember,
    TRLValidationRun,
)
from app.services.auth_service import AuthService
from app.services.pilot_service import PilotService


def test_pilot_settings_crud_and_events(client, auth_headers, demo_shop):
    response = client.get(f"/api/v1/shops/{demo_shop.id}/pilot-settings", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["pilot_enabled"] is False

    response = client.put(
        f"/api/v1/shops/{demo_shop.id}/pilot-settings",
        headers=auth_headers,
        json={"pilot_enabled": True, "pilot_name": "June pilot", "max_auto_sent_messages_per_day": 2},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["pilot_enabled"] is True
    assert body["pilot_name"] == "June pilot"
    assert body["max_auto_sent_messages_per_day"] == 2

    events = client.get(f"/api/v1/shops/{demo_shop.id}/pilot/events", headers=auth_headers).json()["events"]
    assert any(event["event_type"] == "pilot_enabled" for event in events)


def test_emergency_stop_and_resume_flow(client, auth_headers, demo_shop):
    stop = client.post(f"/api/v1/shops/{demo_shop.id}/pilot/emergency-stop", headers=auth_headers)
    assert stop.status_code == 200
    assert stop.json()["pilot_settings"]["emergency_stop_enabled"] is True
    service = PilotService(client.app.dependency_overrides) if False else None

    resume = client.post(f"/api/v1/shops/{demo_shop.id}/pilot/resume", headers=auth_headers)
    assert resume.status_code == 200
    assert resume.json()["pilot_settings"]["emergency_stop_enabled"] is False


def test_pilot_auto_send_and_order_limits(db_session, demo_shop):
    service = PilotService(db_session)
    settings = service.get_or_create_settings(demo_shop.id)
    settings.pilot_enabled = True
    settings.max_auto_sent_messages_per_day = 1
    settings.max_auto_created_orders_per_day = 1
    settings.require_operator_approval_for_first_50_orders = False
    db_session.add(AdminAuditLog(shop_id=demo_shop.id, action="message_auto_sent", entity_type="conversation", details={}))
    db_session.add(AdminAuditLog(shop_id=demo_shop.id, action="pilot_auto_order_created", entity_type="order", details={}))
    db_session.commit()

    allowed, reasons = service.enforce_auto_send_allowed(demo_shop.id)
    assert allowed is False
    assert "pilot_auto_send_limit_reached" in reasons

    allowed, reasons = service.enforce_order_allowed(demo_shop.id)
    assert allowed is False
    assert "pilot_auto_order_limit_reached" in reasons


def test_emergency_stop_disables_auto_send(db_session, demo_shop):
    service = PilotService(db_session)
    settings = service.get_or_create_settings(demo_shop.id)
    settings.pilot_enabled = True
    settings.emergency_stop_enabled = True
    db_session.commit()

    allowed, reasons = service.enforce_auto_send_allowed(demo_shop.id)
    assert allowed is False
    assert "pilot_emergency_stop_enabled" in reasons


def test_pilot_metrics_and_shop_isolation(client, auth_headers, db_session, demo_shop, admin_user):
    other_shop = Shop(name="Other", slug="other")
    db_session.add(other_shop)
    db_session.flush()
    customer = Customer(shop_id=demo_shop.id, instagram_user_id="c1", full_name="Customer")
    account = InstagramAccount(shop_id=demo_shop.id, ig_user_id="ig1", username="demo", access_token_encrypted="x", status=InstagramAccountStatus.CONNECTED)
    db_session.add_all([customer, account])
    db_session.flush()
    conv = Conversation(shop_id=demo_shop.id, instagram_account_id=account.id, customer_id=customer.id)
    db_session.add(conv)
    db_session.flush()
    db_session.add(Message(conversation_id=conv.id, direction=MessageDirection.INBOUND, channel=MessageChannel.INSTAGRAM, message_type=MessageType.TEXT, text="Hi"))
    db_session.add(AdminAuditLog(shop_id=demo_shop.id, action="message_auto_sent", entity_type="conversation", details={}))
    db_session.add(AdminAuditLog(shop_id=other_shop.id, action="message_auto_sent", entity_type="conversation", details={}))
    db_session.add(FailedJob(shop_id=demo_shop.id, queue_name="q", job_type="message", payload={}, status=FailedJobStatus.FAILED, resolved=False))
    db_session.commit()

    response = client.get(f"/api/v1/shops/{demo_shop.id}/pilot/metrics", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["inbound_messages"] == 1
    assert body["auto_sent_messages"] == 1
    assert body["failed_jobs"] == 1


def test_pilot_readiness_evaluator(client, auth_headers, db_session, demo_shop, monkeypatch):
    monkeypatch.setattr("app.services.pilot_service.build_readiness_payload", lambda: ("ok", {}, True))
    account = InstagramAccount(shop_id=demo_shop.id, ig_user_id="ig-ready", username="ready", access_token_encrypted="x", status=InstagramAccountStatus.CONNECTED)
    product = Product(shop_id=demo_shop.id, title="Dress", base_price=Decimal("10.00"), currency="USD")
    db_session.add_all([account, product])
    db_session.flush()
    variant = ProductVariant(product_id=product.id, sku="D-1", price=Decimal("10.00"), stock_quantity=5, is_active=True)
    db_session.add(variant)
    db_session.flush()
    db_session.add(InstagramProductMap(shop_id=demo_shop.id, instagram_account_id=account.id, instagram_post_url="https://instagram.com/p/1", product_id=product.id))
    db_session.add(InventoryMovement(product_variant_id=variant.id, movement_type=InventoryMovementType.ADJUSTMENT, quantity=5, reason="pilot verification"))
    db_session.add(ShopAgentSettings(shop_id=demo_shop.id, mode=AgentMode.CONTROLLED_AUTOPILOT, selling_style=SellingStyle.FRIENDLY, handoff_policy_json={"handoff": True}, risk_policy_json={"support_contact": "ops@example.com"}))
    db_session.add(AdminAuditLog(shop_id=demo_shop.id, action="pilot_test", entity_type="pilot", details={}))
    db_session.add(PilotEvent(shop_id=demo_shop.id, event_type="emergency_stop", severity=PilotEventSeverity.CRITICAL, title="Tested"))
    db_session.add(TRLValidationRun(shop_id=demo_shop.id, status="completed", total_scenarios=1, passed_scenarios=1, failed_scenarios=0, metrics_json={"thresholds_passed": {"overall": True}}))
    db_session.commit()

    response = client.get(f"/api/v1/shops/{demo_shop.id}/pilot-readiness", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["ready_for_trl6_pilot"] is True
    assert any(item["key"] == "product_mapping_coverage" and item["passed"] for item in body["criteria"])


def test_validation_passed_uses_completed_status_with_thresholds(db_session, demo_shop):
    service = PilotService(db_session)
    run = TRLValidationRun(
        shop_id=demo_shop.id,
        status="completed",
        total_scenarios=100,
        passed_scenarios=100,
        failed_scenarios=0,
        metrics_json={"thresholds_passed": {"intent_accuracy": True, "slot_accuracy": True}},
    )
    assert service._validation_passed(run) is True
    assert service._validation_detail(run) == "Passed all thresholds"

    incomplete = TRLValidationRun(
        shop_id=demo_shop.id,
        status="completed",
        total_scenarios=100,
        passed_scenarios=90,
        failed_scenarios=10,
        metrics_json={"thresholds_passed": {"intent_accuracy": True, "slot_accuracy": False}},
    )
    assert service._validation_passed(incomplete) is False
    assert service._validation_detail(incomplete) == "Thresholds not met"


def test_role_permissions_for_pilot_settings(client, db_session, demo_shop):
    operator = AuthService.create_user(db_session, email="op@test.com", password="password123", full_name="Op", role=UserRole.OPERATOR)
    db_session.add(ShopMember(shop_id=demo_shop.id, user_id=operator.id, role=UserRole.OPERATOR))
    db_session.commit()
    login = client.post("/api/v1/auth/login", json={"email": "op@test.com", "password": "password123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.put(f"/api/v1/shops/{demo_shop.id}/pilot-settings", headers=headers, json={"pilot_enabled": True})
    assert response.status_code == 403

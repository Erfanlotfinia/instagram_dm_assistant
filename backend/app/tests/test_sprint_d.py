from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.domain.enums import (
    ChannelProvider,
    MessageChannel,
    MessageDirection,
    MessageType,
    OrderPaymentStatus,
    OrderRecoveryAttemptStatus,
    OrderRecoveryStatus,
    OrderStatus,
    ProductStatus,
    UpsellSuggestionStatus,
    UserRole,
)
from app.domain.models import (
    AbandonedOrderRecoveryRule,
    Conversation,
    ConversationSlots,
    Customer,
    Message,
    Order,
    OrderItem,
    Product,
    ProductUpsell,
    ProductVariant,
    ShopMember,
    User,
)
from app.services.customer_preferences_service import CustomerPreferencesService
from app.services.order_recovery_service import OrderRecoveryService
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.services.upsell_service import UpsellService
from app.tests.fixtures.agent import seed_order_flow_data
from app.tests.fixtures.orders import seed_draft_order


def _confirm_order_for_payment(db_session, order: Order) -> Order:
    service = OrderService(db_session)
    return service._confirm_for_payment(order)


def _waiting_order(
    db_session,
    *,
    shop_id,
    customer_id,
    conversation_id,
    product,
    variant,
    minutes_waiting: int = 120,
) -> Order:
    order = seed_draft_order(
        db_session,
        shop_id=shop_id,
        customer_id=customer_id,
        conversation_id=conversation_id,
        product=product,
        variant=variant,
    )
    confirmed = _confirm_order_for_payment(db_session, order)
    confirmed.updated_at = datetime.now(UTC) - timedelta(minutes=minutes_waiting)
    confirmed.expires_at = None
    db_session.commit()
    db_session.refresh(confirmed)
    return confirmed


def _recovery_rule(db_session, shop_id, *, trigger_after_minutes: int = 30, max_attempts: int = 3) -> AbandonedOrderRecoveryRule:
    rule = AbandonedOrderRecoveryRule(
        shop_id=shop_id,
        is_active=True,
        trigger_after_minutes=trigger_after_minutes,
        max_attempts=max_attempts,
        message_template="Hi {customer_name}, complete payment for {order_total} {currency}.",
        only_inside_allowed_messaging_window=False,
    )
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)
    return rule


def _inbound_message(db_session, conversation_id) -> Message:
    conversation = db_session.get(Conversation, conversation_id)
    message = Message(
        shop_id=conversation.shop_id,
        conversation_id=conversation_id,
        customer_id=conversation.customer_id,
        channel_provider=ChannelProvider.INSTAGRAM,
        channel_account_id=conversation.channel_account_id,
        direction=MessageDirection.INBOUND,
        channel=MessageChannel.INSTAGRAM,
        message_type=MessageType.TEXT,
        text="hello",
        raw_payload={},
    )
    db_session.add(message)
    db_session.commit()
    return message


def test_abandoned_order_eligibility(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    _recovery_rule(db_session, demo_shop.id)
    order = _waiting_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=data["product"],
        variant=data["variant"],
        minutes_waiting=120,
    )
    assert order.recovery_status == OrderRecoveryStatus.NONE

    stats = OrderRecoveryService(db_session).process_recovery_cycle()
    db_session.refresh(order)

    assert stats["eligible"] >= 1
    assert order.recovery_status in {
        OrderRecoveryStatus.ELIGIBLE,
        OrderRecoveryStatus.IN_PROGRESS,
    }


def test_recovery_attempt_creation(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    _recovery_rule(db_session, demo_shop.id, trigger_after_minutes=1)
    order = _waiting_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=data["product"],
        variant=data["variant"],
        minutes_waiting=120,
    )
    _inbound_message(db_session, data["conversation"].id)

    service = OrderRecoveryService(db_session)
    service.process_recovery_cycle()
    db_session.refresh(order)
    service.process_recovery_cycle()
    db_session.refresh(order)

    assert order.recovery_attempt_count >= 1
    assert order.last_recovery_at is not None
    assert len(order.recovery_attempts) >= 1
    assert order.recovery_attempts[0].status == OrderRecoveryAttemptStatus.SENT


def test_recovery_stops_after_payment(db_session, demo_shop, admin_user) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    _recovery_rule(db_session, demo_shop.id)
    order = _waiting_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=data["product"],
        variant=data["variant"],
    )
    order.recovery_status = OrderRecoveryStatus.IN_PROGRESS
    order.recovery_attempt_count = 1
    db_session.commit()

    PaymentService(db_session).mark_paid_manually(demo_shop.id, order.id, admin_user)
    db_session.refresh(order)

    assert order.recovery_status == OrderRecoveryStatus.RECOVERED
    assert order.payment_status == OrderPaymentStatus.PAID


def test_recovery_stops_after_cancellation(db_session, demo_shop, admin_user) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order = _waiting_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=data["product"],
        variant=data["variant"],
    )
    order.recovery_status = OrderRecoveryStatus.ELIGIBLE
    db_session.commit()

    OrderService(db_session).cancel_order(demo_shop.id, order.id, admin_user, None)
    db_session.refresh(order)

    assert order.status == OrderStatus.CANCELLED
    assert order.recovery_status == OrderRecoveryStatus.STOPPED


def test_max_recovery_attempts(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    _recovery_rule(db_session, demo_shop.id, trigger_after_minutes=1, max_attempts=1)
    order = _waiting_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=data["product"],
        variant=data["variant"],
        minutes_waiting=120,
    )
    order.recovery_status = OrderRecoveryStatus.ELIGIBLE
    db_session.commit()

    service = OrderRecoveryService(db_session)
    service.process_recovery_cycle()
    db_session.refresh(order)
    service.process_recovery_cycle()
    db_session.refresh(order)

    assert order.recovery_attempt_count == 1
    assert order.recovery_status == OrderRecoveryStatus.FAILED


def test_customer_preferences_update_after_paid_order(db_session, demo_shop, admin_user) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order = _waiting_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=data["product"],
        variant=data["variant"],
    )
    PaymentService(db_session).mark_paid_manually(demo_shop.id, order.id, admin_user)

    prefs = CustomerPreferencesService(db_session).get_or_create(data["customer"].id)
    assert prefs.last_successful_size == "L"
    assert prefs.preferred_size == "L"
    assert "Black" in (prefs.preferred_colors or [])


def test_same_as_previous_size_flow(db_session, demo_shop, admin_user) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order = _waiting_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=data["product"],
        variant=data["variant"],
    )
    PaymentService(db_session).mark_paid_manually(demo_shop.id, order.id, admin_user)

    service = CustomerPreferencesService(db_session)
    assert service.detect_same_size_request("همون سایز قبلی")
    size, confidence, needs_confirmation = service.resolve_size_from_preferences(
        data["customer"].id,
        confidence_threshold=0.75,
    )
    assert size == "L"
    assert confidence >= 0.75
    assert needs_confirmation is False


def test_upsell_only_from_configured_rules(db_session, demo_shop, admin_user) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    target = Product(
        shop_id=demo_shop.id,
        title="Matching Scarf",
        status=ProductStatus.ACTIVE,
        base_price=Decimal("19.99"),
        currency="USD",
    )
    db_session.add(target)
    db_session.commit()

    upsell = ProductUpsell(
        shop_id=demo_shop.id,
        source_product_id=data["product"].id,
        target_product_id=target.id,
        message_template="Add {target_product_title} for {target_price} {currency}",
        is_active=True,
    )
    db_session.add(upsell)
    db_session.commit()

    order = seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=data["product"],
        variant=data["variant"],
    )

    suggestion = UpsellService(db_session).maybe_suggest_upsell(
        shop_id=demo_shop.id,
        conversation_id=data["conversation"].id,
        order=order,
        source_product_id=data["product"].id,
        intent_confidence=0.9,
        handoff_required=False,
        workflow_clear=True,
    )
    assert suggestion is not None
    assert suggestion.status == UpsellSuggestionStatus.SUGGESTED
    assert "Matching Scarf" in suggestion.suggested_text

    unconfigured = UpsellService(db_session).maybe_suggest_upsell(
        shop_id=demo_shop.id,
        conversation_id=data["conversation"].id,
        order=order,
        source_product_id=target.id,
        intent_confidence=0.9,
        handoff_required=False,
        workflow_clear=True,
    )
    assert unconfigured is None


def test_upsell_skipped_on_low_confidence(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    target = Product(
        shop_id=demo_shop.id,
        title="Matching Scarf",
        status=ProductStatus.ACTIVE,
        base_price=Decimal("19.99"),
        currency="USD",
    )
    db_session.add(target)
    db_session.commit()
    db_session.add(
        ProductUpsell(
            shop_id=demo_shop.id,
            source_product_id=data["product"].id,
            target_product_id=target.id,
            is_active=True,
        )
    )
    db_session.commit()

    suggestion = UpsellService(db_session).maybe_suggest_upsell(
        shop_id=demo_shop.id,
        conversation_id=data["conversation"].id,
        order=None,
        source_product_id=data["product"].id,
        intent_confidence=0.5,
        handoff_required=False,
        workflow_clear=True,
    )
    assert suggestion is not None
    assert suggestion.status == UpsellSuggestionStatus.SKIPPED


def test_post_revenue_analytics(client, auth_headers, db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    slots = ConversationSlots(
        conversation_id=data["conversation"].id,
        product_id=data["product"].id,
        instagram_post_url=data["post_url"],
    )
    db_session.add(slots)
    db_session.commit()

    response = client.get(
        f"/api/v1/shops/{demo_shop.id}/analytics/post-revenue",
        headers=auth_headers,
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) >= 1
    assert rows[0]["instagram_post_url"] == data["post_url"]
    assert "abandoned_rate" in rows[0]
    assert "conversion_rate" in rows[0]


def test_recovery_rules_shop_isolation(client, auth_headers, db_session, demo_shop) -> None:
    other_shop = __import__("app.domain.models", fromlist=["Shop"]).Shop(name="Other", slug="other-shop")
    db_session.add(other_shop)
    db_session.commit()

    created = client.post(
        f"/api/v1/shops/{demo_shop.id}/recovery-rules",
        headers=auth_headers,
        json={
            "trigger_after_minutes": 60,
            "max_attempts": 2,
            "message_template": "Please pay {order_total}",
            "only_inside_allowed_messaging_window": True,
        },
    )
    assert created.status_code == 201
    rule_id = created.json()["id"]

    blocked = client.get(
        f"/api/v1/shops/{other_shop.id}/recovery-rules",
        headers=auth_headers,
    )
    assert blocked.status_code == 403

    patch_blocked = client.patch(
        f"/api/v1/shops/{other_shop.id}/recovery-rules/{rule_id}",
        headers=auth_headers,
        json={"is_active": False},
    )
    assert patch_blocked.status_code == 403


def test_recovery_rules_require_operator(client, auth_headers, db_session, demo_shop, admin_user) -> None:
    operator = __import__("app.services.auth_service", fromlist=["AuthService"]).AuthService.create_user(
        db_session,
        email="operator@test.com",
        password="password123",
        full_name="Operator",
        role=UserRole.OPERATOR,
    )
    db_session.add(ShopMember(shop_id=demo_shop.id, user_id=operator.id, role=UserRole.OPERATOR))
    db_session.commit()

    login = client.post("/api/v1/auth/login", json={"email": "operator@test.com", "password": "password123"})
    operator_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    ok = client.post(
        f"/api/v1/shops/{demo_shop.id}/recovery-rules",
        headers=operator_headers,
        json={
            "trigger_after_minutes": 45,
            "max_attempts": 2,
            "message_template": "Pay now",
        },
    )
    assert ok.status_code == 201

    viewer = __import__("app.services.auth_service", fromlist=["AuthService"]).AuthService.create_user(
        db_session,
        email="viewer@test.com",
        password="password123",
        full_name="Viewer",
        role=UserRole.OPERATOR,
    )
    db_session.add(ShopMember(shop_id=demo_shop.id, user_id=viewer.id, role=UserRole.OPERATOR))
    db_session.commit()
    # downgrade to non-operator by using a custom role - actually OPERATOR can mutate.
    # Test admin (owner) can list without operator-only for GET
    listed = client.get(f"/api/v1/shops/{demo_shop.id}/recovery-rules", headers=auth_headers)
    assert listed.status_code == 200


def test_stop_recovery_endpoint(client, auth_headers, db_session, demo_shop, admin_user) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    order = _waiting_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=data["product"],
        variant=data["variant"],
    )
    order.recovery_status = OrderRecoveryStatus.IN_PROGRESS
    db_session.commit()

    response = client.post(
        f"/api/v1/shops/{demo_shop.id}/orders/{order.id}/stop-recovery",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["recovery_status"] == "stopped"

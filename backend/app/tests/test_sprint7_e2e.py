"""Sprint 7 end-to-end flow and failure scenario tests."""

from decimal import Decimal

from app.domain.enums import AgentWorkflowState, MessageDirection, OrderStatus, PaymentRecordStatus
from app.domain.models import AdminAuditLog, Message, Order
from app.integrations.rabbitmq import NoOpPublisher
from app.services.webhook_ingestion_service import WebhookIngestionService
from app.tests.fixtures.agent import build_orchestrator, create_shared_post_message, seed_order_flow_data
from app.tests.fixtures.instagram_webhook import SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD, SAMPLE_SHARED_POST_PAYLOAD
from app.domain.enums import AgentMode
from app.domain.models import ShopAgentSettings
from app.tests.fixtures.orders import create_text_message, seed_complete_slots


def _enable_controlled_autopilot(db_session, shop_id) -> None:
    db_session.add(
        ShopAgentSettings(
            shop_id=shop_id,
            mode=AgentMode.CONTROLLED_AUTOPILOT,
            auto_send_enabled=True,
            preview_required_for_low_confidence=False,
            preview_required_for_first_order=False,
            preview_required_for_high_value_order=False,
        )
    )
    db_session.commit()


def test_e2e_inbound_to_paid_order(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    _enable_controlled_autopilot(db_session, demo_shop.id)

    service = WebhookIngestionService(db_session, publisher=NoOpPublisher())
    service.handle_instagram_payload(SAMPLE_SHARED_POST_PAYLOAD)
    service.handle_instagram_payload(
        {
            **SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD,
            "entry": [
                {
                    **SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD["entry"][0],
                    "messaging": [
                        {
                            **SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD["entry"][0]["messaging"][0],
                            "message": {
                                "mid": "m_persian_variant",
                                "text": "مشکی سایز L",
                            },
                        }
                    ],
                }
            ],
        }
    )
    db_session.commit()

    llm_slots = {
        "intent": "provide_info",
        "product_reference": {"instagram_post_url": data["post_url"], "instagram_media_id": "media-abc"},
        "slots": {
            "color": "black",
            "size": "L",
            "quantity": 1,
            "customer_name": "Ali Rezaei",
            "phone": "09121234567",
            "city": "Tehran",
            "address": "Valiasr St 10",
            "postal_code": "1234567890",
        },
        "missing_fields": [],
        "confidence": {"intent": 0.92, "slots": 0.9, "product": 0.95},
        "needs_human": False,
        "human_reason": None,
        "reply_style_hint": None,
    }
    post_message = create_shared_post_message(
        db_session, data["conversation"].id, data["post_url"], "مشکی سایز L"
    )
    orchestrator = build_orchestrator(db_session, llm_response=llm_slots)
    assert orchestrator.process_inbound_message(data["conversation"].id, post_message.id) is True

    confirm_message = create_text_message(db_session, data["conversation"].id, "بله تأیید می‌کنم")
    confirm_llm = {
        **llm_slots,
        "intent": "confirm_order",
        "confidence": {"intent": 0.95, "slots": 0.95, "product": 0.95},
    }
    data["conversation"].workflow_state = AgentWorkflowState.WAITING_FOR_CONFIRMATION
    db_session.commit()

    orchestrator = build_orchestrator(db_session, llm_response=confirm_llm)
    assert orchestrator.process_inbound_message(data["conversation"].id, confirm_message.id) is True

    order = db_session.query(Order).filter(Order.conversation_id == data["conversation"].id).one()
    assert order.status == OrderStatus.PAYMENT_PENDING

    from app.services.payment_service import PaymentService

    payment = order.payments[0]
    paid_order = PaymentService(db_session).handle_mock_callback(
        payment.id,
        PaymentRecordStatus.PAID,
        provider_reference="ref-e2e-001",
    )
    assert paid_order.status == OrderStatus.PAID


def test_failure_invalid_llm_json(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    message = create_text_message(db_session, data["conversation"].id, "hello")
    from app.integrations.openai_client import MockOpenAIChatClient

    chat_client = MockOpenAIChatClient(responses=["not valid json {{{"])
    orchestrator = build_orchestrator(db_session, llm_response={})
    orchestrator.llm_service.chat_client = chat_client
    assert orchestrator.process_inbound_message(data["conversation"].id, message.id) is False


def test_failure_product_not_found(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    message = create_shared_post_message(
        db_session,
        data["conversation"].id,
        "https://www.instagram.com/p/UNKNOWN/",
        "مشکی سایز L",
        instagram_media_id="media-unknown",
    )
    llm_response = {
        "intent": "provide_info",
        "product_reference": {"instagram_post_url": "https://www.instagram.com/p/UNKNOWN/"},
        "slots": {"color": "black", "size": "L", "quantity": 1},
        "missing_fields": ["customer_name", "phone"],
        "confidence": {"intent": 0.9, "slots": 0.8, "product": 0.2},
        "needs_human": False,
        "human_reason": None,
        "reply_style_hint": None,
    }
    orchestrator = build_orchestrator(db_session, llm_response=llm_response)
    result = orchestrator.process_inbound_message(data["conversation"].id, message.id)
    assert result is True
    db_session.refresh(data["conversation"])
    assert data["conversation"].slots is not None
    assert data["conversation"].slots.product_id is None


def test_failure_stock_unavailable(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    data["variant"].stock_quantity = 0
    db_session.commit()
    slots = seed_complete_slots(db_session, data["conversation"].id)
    slots.product_id = data["product"].id
    slots.product_variant_id = data["variant"].id
    data["conversation"].workflow_state = AgentWorkflowState.WAITING_FOR_CONFIRMATION
    db_session.commit()

    llm_response = {
        "intent": "confirm_order",
        "product_reference": {"instagram_post_url": data["post_url"]},
        "slots": {
            "color": "black",
            "size": "L",
            "quantity": 1,
            "customer_name": "Ali",
            "phone": "09121234567",
            "city": "Tehran",
            "address": "St 1",
            "postal_code": "1234567890",
        },
        "missing_fields": [],
        "confidence": {"intent": 0.95, "slots": 0.95, "product": 0.95},
        "needs_human": False,
        "human_reason": None,
        "reply_style_hint": None,
    }
    message = create_text_message(db_session, data["conversation"].id, "confirm")
    orchestrator = build_orchestrator(db_session, llm_response=llm_response)
    assert orchestrator.process_inbound_message(data["conversation"].id, message.id) is True
    order = db_session.query(Order).filter(Order.conversation_id == data["conversation"].id).first()
    assert order is None or order.status != OrderStatus.PAYMENT_PENDING


def test_duplicate_webhook_message_id(db_session, demo_shop) -> None:
    seed_order_flow_data(db_session, demo_shop)
    service = WebhookIngestionService(db_session, publisher=NoOpPublisher())
    first = service.handle_instagram_payload(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)
    second = service.handle_instagram_payload(SAMPLE_INSTAGRAM_MESSAGE_PAYLOAD)
    assert first.status == "ok"
    assert second.status == "ok"
    count = db_session.query(Message).filter(Message.instagram_message_id == "m_test_message_001").count()
    assert count == 1


def test_duplicate_payment_callback(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    slots = seed_complete_slots(db_session, data["conversation"].id)
    slots.product_id = data["product"].id
    slots.product_variant_id = data["variant"].id
    db_session.commit()

    from app.services.order_service import OrderService

    order = OrderService(db_session).upsert_draft_from_conversation(
        data["conversation"], slots, data["product"], data["variant"]
    )
    assert order is not None
    confirmed = OrderService(db_session).confirm_after_customer(order)
    from app.services.payment_service import PaymentService

    payment = PaymentService(db_session).initiate_payment(confirmed)
    service = PaymentService(db_session)
    service.handle_mock_callback(payment.id, PaymentRecordStatus.PAID, provider_reference="dup-ref")
    service.handle_mock_callback(payment.id, PaymentRecordStatus.PAID, provider_reference="dup-ref")
    db_session.refresh(order)
    assert order.status == OrderStatus.PAID


def test_login_creates_audit_log(client, admin_user, db_session) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "password123"},
    )
    assert response.status_code == 200
    logs = db_session.query(AdminAuditLog).filter(AdminAuditLog.action == "login").all()
    assert len(logs) >= 1


def test_ready_endpoint(client) -> None:
    response = client.get("/api/v1/ready")
    assert response.status_code in {200, 503}
    body = response.json()
    assert "checks" in body
    assert "postgres" in body["checks"]
    if body["status"] == "failed":
        assert response.status_code == 503
    else:
        assert response.status_code == 200

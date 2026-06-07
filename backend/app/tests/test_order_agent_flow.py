from app.domain.enums import AgentWorkflowState, MessageDirection, OrderStatus
from app.domain.models import ConversationSlots, Message, Order
from app.tests.fixtures.agent import build_orchestrator, seed_order_flow_data
from app.tests.fixtures.orders import create_text_message, seed_complete_slots


def test_agent_flow_creates_draft_and_payment_link(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    slots = seed_complete_slots(db_session, data["conversation"].id)
    slots.product_id = data["product"].id
    slots.product_variant_id = data["variant"].id
    db_session.commit()

    data["conversation"].workflow_state = AgentWorkflowState.WAITING_FOR_CONFIRMATION
    db_session.commit()

    llm_response = {
        "intent": "confirm_order",
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
        "confidence": {"intent": 0.95, "slots": 0.95, "product": 0.95},
        "needs_human": False,
        "human_reason": None,
        "reply_style_hint": None,
    }
    message = create_text_message(db_session, data["conversation"].id, "بله تأیید می‌کنم")

    orchestrator = build_orchestrator(db_session, llm_response=llm_response)
    assert orchestrator.process_inbound_message(data["conversation"].id, message.id) is True

    db_session.refresh(data["conversation"])
    order = db_session.query(Order).filter(Order.conversation_id == data["conversation"].id).one()
    outbound = (
        db_session.query(Message)
        .filter(
            Message.conversation_id == data["conversation"].id,
            Message.direction == MessageDirection.OUTBOUND,
        )
        .order_by(Message.created_at.desc())
        .first()
    )

    assert data["conversation"].workflow_state == AgentWorkflowState.WAITING_FOR_PAYMENT
    assert order.status == OrderStatus.WAITING_FOR_PAYMENT
    assert outbound is not None
    assert "لینک پرداخت" in outbound.text
    assert "/api/v1/payments/mock/pay/" in outbound.text

    db_session.refresh(data["variant"])
    assert data["variant"].reserved_quantity == 1


def test_agent_creates_draft_on_complete_slots(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    llm_response = {
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
        "confidence": {"intent": 0.9, "slots": 0.9, "product": 0.9},
        "needs_human": False,
        "human_reason": None,
        "reply_style_hint": None,
    }
    from app.tests.fixtures.agent import create_shared_post_message

    message = create_shared_post_message(
        db_session,
        data["conversation"].id,
        data["post_url"],
        "customer info complete",
    )

    orchestrator = build_orchestrator(db_session, llm_response=llm_response)
    orchestrator.process_inbound_message(data["conversation"].id, message.id)

    db_session.refresh(data["conversation"])
    order = db_session.query(Order).filter(Order.conversation_id == data["conversation"].id).one_or_none()
    assert order is not None
    assert order.status == OrderStatus.WAITING_FOR_CONFIRMATION
    assert data["conversation"].workflow_state == AgentWorkflowState.WAITING_FOR_CONFIRMATION

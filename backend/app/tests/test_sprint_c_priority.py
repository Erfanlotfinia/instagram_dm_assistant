from decimal import Decimal

from app.domain.enums import (
    AgentWorkflowState,
    ConversationPriorityLevel,
    OrderPaymentStatus,
    OrderStatus,
)
from app.domain.models import Conversation, ConversationSlots, Order
from app.services.conversation_priority_service import ConversationPriorityService
from app.tests.fixtures.agent import seed_order_flow_data


def test_priority_urgent_for_handoff_and_payment(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    conversation = data["conversation"]
    conversation.handoff_required = True
    conversation.workflow_state = AgentWorkflowState.WAITING_FOR_PAYMENT
    db_session.commit()

    refreshed = ConversationPriorityService(db_session).refresh(conversation.id)
    assert refreshed is not None
    assert refreshed.priority_score >= 50
    assert refreshed.priority_level in {ConversationPriorityLevel.URGENT, ConversationPriorityLevel.HIGH}
    assert refreshed.needs_attention is True
    assert refreshed.priority_reason is not None


def test_priority_increases_after_order_waiting_payment(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    conversation = data["conversation"]
    order = Order(
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=conversation.id,
        status=OrderStatus.PAYMENT_PENDING,
        payment_status=OrderPaymentStatus.PENDING,
        total_amount=Decimal("150.00"),
        currency="USD",
    )
    db_session.add(order)
    db_session.commit()

    refreshed = ConversationPriorityService(db_session).refresh(conversation.id)
    assert refreshed is not None
    assert "Payment waiting" in (refreshed.priority_reason or "")
    assert refreshed.priority_score >= 30


def test_priority_low_confidence_from_slots(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    conversation = data["conversation"]
    slots = ConversationSlots(
        conversation_id=conversation.id,
        product_id=data["product"].id,
        confidence={"intent": 0.2, "slots": 0.3},
    )
    db_session.add(slots)
    db_session.commit()

    refreshed = ConversationPriorityService(db_session).refresh(conversation.id)
    assert refreshed is not None
    assert "Low confidence" in (refreshed.priority_reason or "")

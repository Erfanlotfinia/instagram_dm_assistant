from app.domain.enums import AgentWorkflowState, MessageDirection
from app.domain.models import AgentRun, ConversationSlots, Message
from app.tests.fixtures.agent import (
    build_orchestrator,
    create_shared_post_message,
    seed_order_flow_data,
)


def test_orchestrator_e2e_shared_post_and_variant_asks_customer_info(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    llm_response = {
        "intent": "buy_product",
        "product_reference": {
            "instagram_post_url": data["post_url"],
            "instagram_media_id": "media-abc",
        },
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

    db_session.refresh(data["conversation"])
    slots = db_session.query(ConversationSlots).one()
    outbound = (
        db_session.query(Message)
        .filter(
            Message.conversation_id == data["conversation"].id,
            Message.direction == MessageDirection.OUTBOUND,
        )
        .one()
    )
    agent_run = db_session.query(AgentRun).one()

    assert data["conversation"].workflow_state == AgentWorkflowState.WAITING_FOR_CUSTOMER_INFO
    assert slots.product_id == data["product"].id
    assert slots.product_variant_id == data["variant"].id
    assert slots.color == "black"
    assert slots.size == "L"
    assert "نام" in outbound.text
    assert agent_run.prompt_version == "sprint4-v1"
    assert agent_run.status.value == "success"


def test_orchestrator_invalid_variant_prompts_retry(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    llm_response = {
        "intent": "provide_info",
        "product_reference": {"instagram_post_url": data["post_url"], "instagram_media_id": None},
        "slots": {
            "color": "blue",
            "size": "L",
            "quantity": 1,
            "customer_name": None,
            "phone": None,
            "city": None,
            "address": None,
            "postal_code": None,
        },
        "missing_fields": [],
        "confidence": {"intent": 0.9, "slots": 0.9, "product": 0.9},
        "needs_human": False,
        "human_reason": None,
        "reply_style_hint": None,
    }
    message = create_shared_post_message(
        db_session,
        data["conversation"].id,
        data["post_url"],
        "blue size L",
    )

    orchestrator = build_orchestrator(db_session, llm_response=llm_response)
    orchestrator.process_inbound_message(data["conversation"].id, message.id)

    db_session.refresh(data["conversation"])
    slots = db_session.query(ConversationSlots).one()
    assert data["conversation"].workflow_state == AgentWorkflowState.WAITING_FOR_VARIANT
    assert slots.product_variant_id is None

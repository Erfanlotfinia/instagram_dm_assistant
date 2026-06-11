from app.domain.enums import AgentMode, AgentWorkflowState, MessageDirection
from app.domain.models import AgentRun, ConversationSlots, Message, ShopAgentSettings, SuggestedReply
from app.tests.fixtures.agent import (
    build_orchestrator,
    create_shared_post_message,
    seed_order_flow_data,
)


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


def _reply_text(db_session, conversation_id, conversation) -> str | None:
    if conversation.suggested_outbound:
        return conversation.suggested_outbound
    outbound = (
        db_session.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.direction == MessageDirection.OUTBOUND,
        )
        .order_by(Message.created_at.desc())
        .first()
    )
    if outbound is not None:
        return outbound.text
    suggestion = (
        db_session.query(SuggestedReply)
        .filter_by(conversation_id=conversation_id)
        .order_by(SuggestedReply.created_at.desc())
        .first()
    )
    return suggestion.text if suggestion is not None else None


def test_orchestrator_e2e_shared_post_and_variant_asks_customer_info(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    _enable_controlled_autopilot(db_session, demo_shop.id)
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
    agent_run = db_session.query(AgentRun).one()
    reply = _reply_text(db_session, data["conversation"].id, data["conversation"])

    assert data["conversation"].workflow_state == AgentWorkflowState.WAITING_FOR_CUSTOMER_INFO
    assert slots.product_id == data["product"].id
    assert slots.product_variant_id == data["variant"].id
    assert slots.color == "black"
    assert slots.size == "L"
    assert reply is not None
    assert "نام" in reply
    assert agent_run.prompt_version == "sprint4-v1"
    assert agent_run.status.value == "success"


def test_orchestrator_invalid_variant_prompts_retry(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    _enable_controlled_autopilot(db_session, demo_shop.id)
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
    assert data["conversation"].workflow_state in {
        AgentWorkflowState.WAITING_FOR_VARIANT,
        AgentWorkflowState.HUMAN_HANDOFF,
    }
    assert slots.product_variant_id is None

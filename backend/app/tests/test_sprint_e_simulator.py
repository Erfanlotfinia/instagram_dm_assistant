from __future__ import annotations

import json
from unittest.mock import patch

from sqlalchemy import select

from app.domain.enums import MessageDirection
from app.domain.models import Conversation, Message, Order, SuggestedReply
from app.schemas.simulator import DMSimulatorRequest
from app.services.dm_simulator_service import DMSimulatorService
from app.services.instagram_send_service import InstagramSendService
from app.tests.fixtures.agent import build_orchestrator, seed_order_flow_data


def _llm_response(data: dict) -> dict:
    return {
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
        "missing_fields": ["customer_name", "phone"],
        "confidence": {"intent": 0.95, "slots": 0.9, "product": 0.98},
        "needs_human": False,
        "human_reason": None,
        "reply_style_hint": "friendly",
    }


def test_simulator_creates_simulation_records_without_real_send(db_session, demo_shop, admin_user) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    orchestrator = build_orchestrator(db_session, llm_response=_llm_response(data))
    payload = DMSimulatorRequest(
        instagram_account_id=data["account"].id,
        message_text="مشکی سایز L یک عدد",
        shared_post_url=data["post_url"],
    )

    with patch.object(InstagramSendService, "send_text_message") as send_mock:
        result = DMSimulatorService(db_session).run(
            demo_shop.id,
            payload,
            admin_user,
            orchestrator=orchestrator,
        )

    send_mock.assert_not_called()

    conversation = db_session.get(Conversation, result.conversation_id)
    inbound = db_session.get(Message, result.message_id)
    assert conversation is not None and conversation.is_simulation is True
    assert inbound is not None and inbound.is_simulation is True
    assert result.is_simulation is True
    assert result.decision_trace
    assert result.intent == "buy_product"
    assert "auto_send_decision" in result.decision_trace

    suggested = db_session.scalar(
        select(SuggestedReply).where(SuggestedReply.conversation_id == conversation.id)
    )
    assert suggested is not None
    assert suggested.is_simulation is True

    orders = list(
        db_session.scalars(select(Order).where(Order.conversation_id == conversation.id)).all()
    )
    for order in orders:
        assert order.is_simulation is True


def test_simulator_reset_only_removes_simulation_data(db_session, demo_shop, admin_user) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    orchestrator = build_orchestrator(db_session, llm_response=_llm_response(data))
    service = DMSimulatorService(db_session)
    payload = DMSimulatorRequest(
        instagram_account_id=data["account"].id,
        message_text="black L please",
        shared_post_url=data["post_url"],
    )
    sim_result = service.run(demo_shop.id, payload, admin_user, orchestrator=orchestrator)

    real_conversation = data["conversation"]
    real_conversation.is_simulation = False
    db_session.commit()

    deleted = service.reset(demo_shop.id, admin_user)

    assert deleted == 1
    assert db_session.get(Conversation, sim_result.conversation_id) is None
    assert db_session.get(Conversation, real_conversation.id) is not None


def test_simulator_list_runs_and_output_fields(db_session, demo_shop, admin_user) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    orchestrator = build_orchestrator(db_session, llm_response=_llm_response(data))
    service = DMSimulatorService(db_session)
    payload = DMSimulatorRequest(
        instagram_account_id=data["account"].id,
        message_text="price?",
    )
    result = service.run(demo_shop.id, payload, admin_user, orchestrator=orchestrator)
    runs = service.list_runs(demo_shop.id, admin_user)

    assert len(runs) == 1
    assert runs[0].conversation_id == result.conversation_id
    assert result.message_id
    assert result.auto_send_decision is not None
    assert isinstance(result.extracted_slots, dict)


def test_seed_demo_data_module_importable() -> None:
    from app.scripts import seed_demo_data

    assert callable(seed_demo_data.seed_rich_demo_data)

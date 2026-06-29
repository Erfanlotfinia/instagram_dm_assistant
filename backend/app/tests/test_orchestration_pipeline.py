"""Regression tests for the staged conversation orchestration pipeline."""

from __future__ import annotations

from app.domain.enums import (
    AgentMode,
    AgentWorkflowState,
    ConversationResponseMode,
    MessageDirection,
    OrderStatus,
)
from app.domain.models import (
    AgentAction,
    AgentRun,
    Message,
    Order,
    ShopAgentSettings,
    SuggestedReply,
)
from app.services.orchestration.context import ConversationPipelineContext
from app.services.orchestration.stages.load_context import LoadContextStage
from app.services.orchestration.stages.product_resolution import ProductResolutionStage
from app.services.pilot_service import PilotService
from app.tests.fixtures.agent import (
    build_orchestrator,
    create_shared_post_message,
    create_text_message,
    seed_order_flow_data,
)
from app.tests.fixtures.orders import seed_complete_slots, seed_draft_order


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


def _shared_post_llm(data: dict, *, confidence: dict | None = None) -> dict:
    return {
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
        "confidence": confidence
        or {"intent": 0.95, "slots": 0.9, "product": 0.98, "address": 0.9},
        "needs_human": False,
        "human_reason": None,
        "reply_style_hint": "friendly",
    }


def test_human_controlled_conversation_skips_agent(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    data["conversation"].agent_paused = True
    db_session.commit()

    message = create_text_message(db_session, data["conversation"].id, "hello")
    orchestrator = build_orchestrator(db_session, llm_response=_shared_post_llm(data))

    assert orchestrator.process_inbound_message(data["conversation"].id, message.id) is True
    assert db_session.query(AgentRun).count() == 0


def test_emergency_stop_blocks_order_side_effects(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    _enable_controlled_autopilot(db_session, demo_shop.id)
    PilotService(db_session).set_emergency_stop(demo_shop.id, True, reason="pipeline test")

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
        "confidence": {"intent": 0.95, "slots": 0.95, "product": 0.95, "address": 0.95},
        "needs_human": False,
        "human_reason": None,
        "reply_style_hint": None,
    }
    message = create_shared_post_message(
        db_session,
        data["conversation"].id,
        data["post_url"],
        "complete order info",
    )
    orchestrator = build_orchestrator(db_session, llm_response=llm_response)
    assert orchestrator.process_inbound_message(data["conversation"].id, message.id) is True

    db_session.refresh(data["conversation"])
    blocked = (
        db_session.query(AgentAction)
        .filter(
            AgentAction.conversation_id == data["conversation"].id,
            AgentAction.action_name == "order_side_effects_blocked",
        )
        .count()
    )
    outbound = (
        db_session.query(Message)
        .filter(
            Message.conversation_id == data["conversation"].id,
            Message.direction == MessageDirection.OUTBOUND,
        )
        .count()
    )
    order = db_session.query(Order).filter(Order.conversation_id == data["conversation"].id).one_or_none()

    assert blocked >= 1
    assert data["conversation"].preview_required is True
    assert order is None
    assert outbound == 0


def test_low_confidence_creates_suggested_reply(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    db_session.add(
        ShopAgentSettings(
            shop_id=demo_shop.id,
            mode=AgentMode.CONTROLLED_AUTOPILOT,
            auto_send_enabled=True,
            preview_required_for_low_confidence=True,
            preview_required_for_first_order=False,
            preview_required_for_high_value_order=False,
        )
    )
    db_session.commit()

    message = create_shared_post_message(
        db_session,
        data["conversation"].id,
        data["post_url"],
        "black size L",
    )
    orchestrator = build_orchestrator(
        db_session,
        llm_response=_shared_post_llm(
            data,
            confidence={"intent": 0.40, "slots": 0.90, "product": 0.98, "address": 0.90},
        ),
    )
    assert orchestrator.process_inbound_message(data["conversation"].id, message.id) is True

    db_session.refresh(data["conversation"])
    suggestion = (
        db_session.query(SuggestedReply)
        .filter(SuggestedReply.conversation_id == data["conversation"].id)
        .one_or_none()
    )
    outbound = (
        db_session.query(Message)
        .filter(
            Message.conversation_id == data["conversation"].id,
            Message.direction == MessageDirection.OUTBOUND,
        )
        .count()
    )

    assert suggestion is not None
    assert outbound == 0
    assert data["conversation"].preview_required is True


def test_safe_high_confidence_path_can_auto_send(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    _enable_controlled_autopilot(db_session, demo_shop.id)

    message = create_shared_post_message(
        db_session,
        data["conversation"].id,
        data["post_url"],
        "black size L",
    )
    orchestrator = build_orchestrator(db_session, llm_response=_shared_post_llm(data))
    assert orchestrator.process_inbound_message(data["conversation"].id, message.id) is True

    outbound = (
        db_session.query(Message)
        .filter(
            Message.conversation_id == data["conversation"].id,
            Message.direction == MessageDirection.OUTBOUND,
        )
        .one_or_none()
    )
    assert outbound is not None
    assert outbound.text is not None


def test_simulation_never_real_sends(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    _enable_controlled_autopilot(db_session, demo_shop.id)
    data["conversation"].is_simulation = True
    db_session.commit()

    message = create_shared_post_message(
        db_session,
        data["conversation"].id,
        data["post_url"],
        "black size L",
    )
    orchestrator = build_orchestrator(db_session, llm_response=_shared_post_llm(data))
    assert orchestrator.process_inbound_message(data["conversation"].id, message.id) is True

    outbound = (
        db_session.query(Message)
        .filter(
            Message.conversation_id == data["conversation"].id,
            Message.direction == MessageDirection.OUTBOUND,
        )
        .count()
    )
    suggestion = (
        db_session.query(SuggestedReply)
        .filter(SuggestedReply.conversation_id == data["conversation"].id)
        .one_or_none()
    )

    assert outbound == 0
    assert suggestion is not None
    assert suggestion.is_simulation is True


def test_order_payment_side_effects_unchanged(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    _enable_controlled_autopilot(db_session, demo_shop.id)
    slots = seed_complete_slots(db_session, data["conversation"].id)
    slots.product_id = data["product"].id
    slots.product_variant_id = data["variant"].id
    slots.instagram_post_url = data["post_url"]
    seed_draft_order(
        db_session,
        shop_id=demo_shop.id,
        customer_id=data["customer"].id,
        conversation_id=data["conversation"].id,
        product=data["product"],
        variant=data["variant"],
    )
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
        "confidence": {"intent": 0.95, "slots": 0.95, "product": 0.95, "address": 0.95},
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
    assert order.status == OrderStatus.PAYMENT_PENDING
    assert outbound is not None
    assert "لینک پرداخت" in outbound.text


def test_human_response_mode_skips_agent(db_session, demo_shop) -> None:
    data = seed_order_flow_data(db_session, demo_shop)
    data["conversation"].response_mode = ConversationResponseMode.HUMAN
    db_session.commit()

    message = create_text_message(db_session, data["conversation"].id, "hello")
    orchestrator = build_orchestrator(db_session, llm_response=_shared_post_llm(data))

    assert orchestrator.process_inbound_message(data["conversation"].id, message.id) is True
    assert db_session.query(AgentRun).count() == 0


def test_product_resolution_stage_resolves_instagram_map(db_session, demo_shop) -> None:
    """Stage-level test: ProductResolutionStage resolves mapped products independently."""
    data = seed_order_flow_data(db_session, demo_shop)
    message = create_shared_post_message(
        db_session,
        data["conversation"].id,
        data["post_url"],
        "black size L",
    )
    orchestrator = build_orchestrator(db_session, llm_response=_shared_post_llm(data))

    ctx = ConversationPipelineContext(
        conversation_id=data["conversation"].id,
        message_id=message.id,
    )
    assert LoadContextStage(orchestrator.services).run(ctx).stop is False
    assert ProductResolutionStage(orchestrator.services).run(ctx).stop is False

    assert ctx.resolution.product is not None
    assert ctx.resolution.product.id == data["product"].id
    assert ctx.resolution.resolve_source == "instagram_map"
    assert ctx.resolution.product_info is not None
    assert "black" in [c.lower() for c in ctx.resolution.valid_colors]

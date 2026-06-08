from decimal import Decimal

from app.domain.enums import AgentMode, SellingStyle
from app.domain.models import ShopAgentSettings
from app.services.auto_send_decision_service import AutoSendDecisionInput, AutoSendDecisionService


def make_settings(**overrides):
    settings = ShopAgentSettings(shop_id=overrides.pop("shop_id", None) or "00000000-0000-0000-0000-000000000001")
    settings.mode = overrides.pop("mode", AgentMode.CONTROLLED_AUTOPILOT)
    settings.auto_send_enabled = overrides.pop("auto_send_enabled", True)
    settings.preview_required_for_low_confidence = overrides.pop("preview_required_for_low_confidence", True)
    settings.preview_required_for_first_order = overrides.pop("preview_required_for_first_order", False)
    settings.preview_required_for_high_value_order = overrides.pop("preview_required_for_high_value_order", True)
    settings.confidence_threshold_intent = Decimal(overrides.pop("confidence_threshold_intent", "0.75"))
    settings.confidence_threshold_product = Decimal(overrides.pop("confidence_threshold_product", "0.80"))
    settings.confidence_threshold_variant = Decimal(overrides.pop("confidence_threshold_variant", "0.85"))
    settings.confidence_threshold_address = Decimal(overrides.pop("confidence_threshold_address", "0.80"))
    settings.high_value_order_threshold = Decimal(overrides.pop("high_value_order_threshold", "500"))
    settings.selling_style = SellingStyle.FRIENDLY
    return settings


def decide(settings, **overrides):
    payload = {
        "settings": settings,
        "intent_confidence": 0.99,
        "product_confidence": 0.99,
        "variant_confidence": 0.99,
        "address_confidence": 0.99,
        "order_value": Decimal("100"),
        "is_first_order": False,
        "handoff_reason": None,
        "message_risk": None,
    }
    payload.update(overrides)
    return AutoSendDecisionService().decide(AutoSendDecisionInput(**payload))


def test_copilot_mode_never_auto_sends():
    decision = decide(make_settings(mode=AgentMode.COPILOT))
    assert decision.auto_send_allowed is False
    assert decision.requires_preview is True
    assert "copilot_mode_requires_operator_approval" in decision.reasons


def test_human_first_mode_never_auto_sends():
    decision = decide(make_settings(mode=AgentMode.HUMAN_FIRST))
    assert decision.auto_send_allowed is False
    assert decision.requires_preview is True
    assert "human_first_mode_blocks_auto_send" in decision.reasons


def test_controlled_autopilot_sends_only_if_confidence_passes():
    decision = decide(make_settings(mode=AgentMode.CONTROLLED_AUTOPILOT))
    assert decision.auto_send_allowed is True
    assert decision.requires_preview is False


def test_low_confidence_creates_preview():
    decision = decide(make_settings(), intent_confidence=0.50)
    assert decision.auto_send_allowed is False
    assert decision.requires_preview is True
    assert any(reason.startswith("low_intent_confidence") for reason in decision.reasons)


def test_high_value_order_creates_preview():
    decision = decide(make_settings(high_value_order_threshold="250"), order_value=Decimal("300"))
    assert decision.auto_send_allowed is False
    assert decision.requires_preview is True
    assert "high_value_order_requires_preview" in decision.reasons


def test_first_order_creates_preview_when_enabled():
    decision = decide(make_settings(preview_required_for_first_order=True), is_first_order=True)
    assert decision.auto_send_allowed is False
    assert decision.requires_preview is True
    assert "first_order_requires_preview" in decision.reasons


def test_handoff_required_never_auto_sends():
    decision = decide(make_settings(), handoff_reason="customer_asked_for_human")
    assert decision.auto_send_allowed is False
    assert decision.requires_handoff is True
    assert decision.requires_preview is True


def test_sprint_b_sqlalchemy_enums_persist_value_labels():
    from app.domain.enums import SuggestedReplyGeneratedBy, SuggestedReplyStatus
    from app.domain.models import SuggestedReply

    assert ShopAgentSettings.__table__.c.mode.type.enums == [member.value for member in AgentMode]
    assert ShopAgentSettings.__table__.c.selling_style.type.enums == [
        member.value for member in SellingStyle
    ]
    assert SuggestedReply.__table__.c.status.type.enums == [
        member.value for member in SuggestedReplyStatus
    ]
    assert SuggestedReply.__table__.c.generated_by.type.enums == [
        member.value for member in SuggestedReplyGeneratedBy
    ]

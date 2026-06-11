from decimal import Decimal

import pytest

from app.domain.enums import MessageChannel, TriggerSourceType
from app.domain.models import Conversation, InstagramAccount, Product, ProductVariant, TriggerEvent, UnavailableDemand
from app.integrations.instagram.channel_provider import InstagramChannelProvider
from app.schemas.agent import ExtractionConfidence
from app.schemas.agent_settings import AutoSendDecisionRequest, ShopAgentStudioSettingsUpdate
from app.schemas.triggers import TriggerMatchRequest, TriggerRuleCreate
from app.services.agent_settings_service import AgentSettingsService
from app.services.conversation_orchestrator import ConversationOrchestrator
from app.services.trigger_service import TriggerService
from app.services.variant_resolver import VariantResolver


def test_instagram_channel_provider_normalizes_dm_payload():
    payload = {"entry": [{"id": "ig-account", "messaging": [{"sender": {"id": "cust-1"}, "message": {"mid": "m1", "text": "مشکی سایز L"}}]}]}
    messages = InstagramChannelProvider().normalize_inbound(payload)
    assert messages[0].provider == MessageChannel.INSTAGRAM
    assert messages[0].conversation.customer.external_customer_id == "cust-1"
    assert messages[0].text == "مشکی سایز L"


def test_trigger_keyword_duplicate_and_flow(db_session, demo_shop, admin_user):
    account = InstagramAccount(shop_id=demo_shop.id, ig_user_id="ig-trigger", username="shop", access_token_encrypted="token")
    product = Product(shop_id=demo_shop.id, title="Coat", base_price=Decimal("20"), currency="USD")
    db_session.add_all([account, product]); db_session.commit()
    service = TriggerService(db_session)
    payload = TriggerRuleCreate(instagram_account_id=account.id, keyword="قیمت", response_template="قیمت و موجودی رو همینجا می‌فرستم", target_product_id=product.id)
    rule = service.create_rule(demo_shop.id, payload, admin_user)
    with pytest.raises(Exception):
        service.create_rule(demo_shop.id, payload, admin_user)
    result = service.match_keyword(demo_shop.id, TriggerMatchRequest(instagram_account_id=account.id, text="قیمت لطفا", instagram_user_id="u1"), admin_user)
    assert result.matched is True
    assert result.target_product_id == product.id
    assert db_session.query(TriggerEvent).filter_by(trigger_id=rule.id).count() == 1


def test_variant_resolver_logs_unavailable_demand(db_session, demo_shop):
    product = Product(shop_id=demo_shop.id, title="Dress", base_price=Decimal("50"), currency="USD")
    db_session.add(product)
    db_session.flush()
    variant = ProductVariant(
        product_id=product.id,
        color="white",
        normalized_color="white",
        size="M",
        normalized_size="M",
        sku="D-W-M",
        price=Decimal("50"),
        stock_quantity=1,
    )
    db_session.add(variant)
    db_session.commit()
    result = VariantResolver(db_session).resolve(shop_id=demo_shop.id, product_id=product.id, raw_color="مشکی", raw_size="L", quantity=1)
    assert "color_unavailable" in result.mismatch_reasons
    assert db_session.query(UnavailableDemand).count() == 1


def test_agent_settings_preview_rules_and_discount_safety(db_session, demo_shop, admin_user):
    service = AgentSettingsService(db_session)
    settings = service.update(demo_shop.id, ShopAgentStudioSettingsUpdate(discount_policy_json={"allowed_discounts": [{"code": "VIP10"}], "llm_may_create_discount": True}, high_value_order_threshold=Decimal("100")), admin_user)
    assert settings.discount_policy_json["llm_may_create_discount"] is False
    assert demo_shop.agent_settings["high_value_order_threshold"] == 100.0
    assert demo_shop.agent_settings["variant_confidence_threshold"] == 0.85
    decision = service.decide_auto_send(demo_shop.id, AutoSendDecisionRequest(variant_confidence=0.1, order_total=Decimal("150")), admin_user)
    assert decision.preview_required is True
    assert any("low_variant_confidence" in reason for reason in decision.reasons)
    assert any("high_value_order_requires_preview" in reason for reason in decision.reasons)


def test_orchestrator_preview_uses_agent_studio_settings(db_session, demo_shop, admin_user):
    from app.tests.fixtures.agent import seed_order_flow_data

    data = seed_order_flow_data(db_session, demo_shop)
    service = AgentSettingsService(db_session)
    service.update(
        demo_shop.id,
        ShopAgentStudioSettingsUpdate(auto_send_enabled=False, confidence_threshold_intent=Decimal("0.95")),
        admin_user,
    )
    conversation = data["conversation"]

    preview_required, reason = ConversationOrchestrator(db_session)._preview_decision(
        conversation,
        ExtractionConfidence(intent=1.0, product=1.0, slots=1.0, address=1.0),
        handoff_required=False,
    )

    assert preview_required is True
    assert reason == "auto_send_disabled"

    service.update(
        demo_shop.id,
        ShopAgentStudioSettingsUpdate(auto_send_enabled=True, confidence_threshold_intent=Decimal("0.95")),
        admin_user,
    )
    preview_required, reason = ConversationOrchestrator(db_session)._preview_decision(
        conversation,
        ExtractionConfidence(intent=0.94, product=1.0, slots=1.0, address=1.0),
        handoff_required=False,
    )

    assert preview_required is True
    assert reason == "low_intent_confidence:0.94"

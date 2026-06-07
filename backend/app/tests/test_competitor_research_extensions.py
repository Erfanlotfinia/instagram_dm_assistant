from decimal import Decimal

import pytest

from app.domain.enums import MessageChannel, TriggerSourceType
from app.domain.models import InstagramAccount, Product, ProductVariant, TriggerEvent, UnavailableDemand
from app.integrations.instagram.channel_provider import InstagramChannelProvider
from app.schemas.agent_settings import AutoSendDecisionRequest, ShopAgentStudioSettingsUpdate
from app.schemas.triggers import TriggerMatchRequest, TriggerRuleCreate
from app.services.agent_settings_service import AgentSettingsService
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
    variant = ProductVariant(product_id=product.id, color="white", normalized_color="white", size="M", normalized_size="M", sku="D-W-M", price=Decimal("50"), stock_quantity=1)
    db_session.add_all([product, variant]); db_session.commit()
    result = VariantResolver(db_session).resolve(shop_id=demo_shop.id, product_id=product.id, raw_color="مشکی", raw_size="L", quantity=1)
    assert "color_unavailable" in result.mismatch_reasons
    assert db_session.query(UnavailableDemand).count() == 1


def test_agent_settings_preview_rules_and_discount_safety(db_session, demo_shop, admin_user):
    service = AgentSettingsService(db_session)
    settings = service.update(demo_shop.id, ShopAgentStudioSettingsUpdate(discount_policy_json={"allowed_discounts": [{"code": "VIP10"}], "llm_may_create_discount": True}, high_value_order_threshold=Decimal("100")), admin_user)
    assert settings.discount_policy_json["llm_may_create_discount"] is False
    decision = service.decide_auto_send(demo_shop.id, AutoSendDecisionRequest(variant_confidence=0.1, order_total=Decimal("150")), admin_user)
    assert decision.preview_required is True
    assert any("Variant confidence" in reason for reason in decision.reasons)
    assert any("High-value" in reason for reason in decision.reasons)

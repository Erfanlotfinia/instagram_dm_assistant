from __future__ import annotations

from decimal import Decimal

from app.domain.enums import AgentMode, ConfidenceSource, InstagramAccountStatus, ProductStatus, UserRole
from app.domain.models import (
    ColorAlias,
    InstagramAccount,
    InstagramProductMap,
    Product,
    ProductVariant,
    Shop,
    ShopAgentSettings,
    ShopMember,
    SizeAlias,
)
from app.services.onboarding_status_service import OnboardingStatusService
from app.core.security import encrypt_secret


def _second_shop(db_session, admin_user) -> Shop:
    shop = Shop(name="Other Shop", slug="other-shop")
    db_session.add(shop)
    db_session.flush()
    db_session.add(ShopMember(shop_id=shop.id, user_id=admin_user.id, role=UserRole.OWNER))
    db_session.commit()
    db_session.refresh(shop)
    return shop


def test_onboarding_missing_steps_for_empty_shop(db_session, demo_shop, admin_user) -> None:
    status = OnboardingStatusService(db_session).get_status(demo_shop.id, admin_user)

    assert status.progress_percent == 11
    assert "shop_profile" in status.completed_steps
    assert "connect_instagram" in status.missing_steps
    assert "dm_simulator" in status.missing_steps
    assert status.next_recommended_action.startswith("Connect an Instagram")


def test_onboarding_completed_steps_when_fully_configured(db_session, demo_shop, admin_user) -> None:
    account = InstagramAccount(
        shop_id=demo_shop.id,
        ig_user_id="ig-1",
        username="demo",
        access_token_encrypted=encrypt_secret("token"),
        status=InstagramAccountStatus.CONNECTED,
    )
    db_session.add(account)
    db_session.flush()

    product = Product(
        shop_id=demo_shop.id,
        title="Shirt",
        description="Demo",
        status=ProductStatus.ACTIVE,
        base_price=Decimal("10"),
        currency="USD",
    )
    db_session.add(product)
    db_session.flush()
    db_session.add(
        ProductVariant(
            product_id=product.id,
            color="black",
            size="L",
            sku="BLK-L",
            price=Decimal("10"),
            stock_quantity=5,
            reserved_quantity=0,
            is_active=True,
        )
    )
    db_session.add(
        InstagramProductMap(
            shop_id=demo_shop.id,
            instagram_account_id=account.id,
            instagram_media_id="media-1",
            instagram_post_url="https://instagram.com/p/abc/",
            product_id=product.id,
            confidence_source=ConfidenceSource.MANUAL,
            is_active=True,
        )
    )
    db_session.add(ColorAlias(shop_id=demo_shop.id, raw_value="مشکی", normalized_value="black"))
    db_session.add(SizeAlias(shop_id=demo_shop.id, raw_value="لارج", normalized_value="L"))
    db_session.add(
        ShopAgentSettings(
            shop_id=demo_shop.id,
            mode=AgentMode.COPILOT,
            auto_send_enabled=False,
        )
    )
    demo_shop.onboarding_flags = {"dm_simulator": True}
    db_session.commit()

    status = OnboardingStatusService(db_session).get_status(demo_shop.id, admin_user)

    assert status.missing_steps == []
    assert len(status.completed_steps) == 9
    assert status.progress_percent == 100
    assert "complete" in status.next_recommended_action.lower()


def test_onboarding_shop_isolation(db_session, demo_shop, admin_user) -> None:
    other_shop = _second_shop(db_session, admin_user)
    other_shop.onboarding_flags = {"dm_simulator": True}
    db_session.commit()

    demo_status = OnboardingStatusService(db_session).get_status(demo_shop.id, admin_user)
    other_status = OnboardingStatusService(db_session).get_status(other_shop.id, admin_user)

    assert "dm_simulator" in demo_status.missing_steps
    assert "dm_simulator" in other_status.completed_steps

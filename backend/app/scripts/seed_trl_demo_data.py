from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_secret
from app.db.session import SessionLocal
from app.domain.enums import AgentMode, ConfidenceSource, InstagramAccountStatus, ProductStatus, SellingStyle, UserRole
from app.domain.models import (
    AbandonedOrderRecoveryRule,
    ColorAlias,
    InstagramAccount,
    InstagramProductMap,
    Product,
    ProductUpsell,
    ProductVariant,
    Shop,
    ShopAgentSettings,
    ShopMember,
    SizeAlias,
    User,
)

DEMO_SHOP_SLUG = "trl-commerce-demo"
DEMO_ADMIN_EMAIL = "trl-admin@example.com"
DEMO_OPERATOR_EMAIL = "trl-operator@example.com"

COLORS = [
    ("مشکی", "black", ["black", "بلك", "سیاه"]),
    ("سفید", "white", ["white", "سفید یخی"]),
    ("کرم", "cream", ["cream", "شیری"]),
    ("آبی", "blue", ["blue", "آبی کاربنی"]),
    ("صورتی", "pink", ["pink", "گلبهی"]),
    ("سبز", "green", ["green", "یشمی"]),
]
SIZES = ["XS", "S", "M", "L", "XL"]
PRODUCTS = [
    "مانتو لینن تابستانه", "شومیز ساتن", "شلوار بگ جین", "کت کراپ", "پیراهن مجلسی میدی",
    "تاپ بافت", "دامن پلیسه", "هودی اورسایز", "بارانی سبک", "ست راحتی", "کراپ کتان",
    "شلوار پارچه‌ای", "کت جین", "پیراهن ساحلی", "بادی آستین بلند", "ژاکت پاییزه",
    "وست لینن", "شال ابریشم", "کیف دوشی مینیمال", "کمربند چرمی",
]


def _get_or_create_user(db, email: str, name: str, role: UserRole) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, full_name=name, role=role, password_hash=hash_secret("Password123!"), is_active=True)
        db.add(user)
        db.flush()
    return user


def seed_trl_demo_data(reset: bool = False, db: Session | None = None) -> dict[str, str | int]:
    owns_session = db is None
    db = db or SessionLocal()
    try:
        shop = db.scalar(select(Shop).where(Shop.slug == DEMO_SHOP_SLUG))
        if reset and shop is not None:
            db.delete(shop)
            db.commit()
            shop = None
        admin = _get_or_create_user(db, DEMO_ADMIN_EMAIL, "TRL Demo Admin", UserRole.ADMIN)
        operator = _get_or_create_user(db, DEMO_OPERATOR_EMAIL, "TRL Demo Operator", UserRole.OPERATOR)
        if shop is None:
            shop = Shop(
                name="TRL Fashion Demo Shop",
                slug=DEMO_SHOP_SLUG,
                default_currency="IRR",
                agent_settings={"trl_threshold_profile": "trl5", "simulation_safe_mode": True},
            )
            db.add(shop)
            db.flush()
        for user, role in [(admin, UserRole.ADMIN), (operator, UserRole.OPERATOR)]:
            if db.scalar(select(ShopMember).where(ShopMember.shop_id == shop.id, ShopMember.user_id == user.id)) is None:
                db.add(ShopMember(shop_id=shop.id, user_id=user.id, role=role))
        ig = db.scalar(select(InstagramAccount).where(InstagramAccount.shop_id == shop.id, InstagramAccount.ig_user_id == "trl_demo_ig"))
        if ig is None:
            ig = InstagramAccount(
                shop_id=shop.id, ig_user_id="trl_demo_ig", page_id="trl_demo_page", username="trl_fashion_demo",
                access_token_encrypted="simulation-token", webhook_enabled=False, status=InstagramAccountStatus.CONNECTED,
            )
            db.add(ig); db.flush()
        settings = db.get(ShopAgentSettings, shop.id)
        if settings is None:
            db.add(ShopAgentSettings(
                shop_id=shop.id, auto_send_enabled=True, preview_required_for_low_confidence=True,
                preview_required_for_first_order=False, preview_required_for_high_value_order=True,
                confidence_threshold_intent=Decimal("0.90"), confidence_threshold_product=Decimal("0.90"),
                confidence_threshold_variant=Decimal("0.85"), mode=AgentMode.CONTROLLED_AUTOPILOT,
                selling_style=SellingStyle.FRIENDLY, brand_voice="Warm Persian boutique assistant.",
                handoff_policy_json={"angry_customer": True, "payment_dispute": True},
            ))
        products: list[Product] = []
        for idx, title in enumerate(PRODUCTS, start=1):
            product = db.scalar(select(Product).where(Product.shop_id == shop.id, Product.title == title))
            if product is None:
                product = Product(shop_id=shop.id, title=title, description=f"محصول دمو TRL 5: {title}", status=ProductStatus.ACTIVE, base_price=Decimal(1200000 + idx * 75000), currency="IRR", category="fashion")
                db.add(product); db.flush()
            products.append(product)
            for cidx, (label, norm, _) in enumerate(COLORS[:5], start=1):
                for size in SIZES:
                    sku = f"TRL-{idx:02d}-{norm[:3].upper()}-{size}"
                    if db.scalar(select(ProductVariant).where(ProductVariant.product_id == product.id, ProductVariant.sku == sku)) is None:
                        stock = 0 if (idx + cidx + len(size)) % 17 == 0 else 3 + ((idx + cidx + len(size)) % 12)
                        db.add(ProductVariant(product_id=product.id, color=label, normalized_color=norm, size=size, normalized_size=size, sku=sku, price=product.base_price, stock_quantity=stock, reserved_quantity=0, is_active=True))
            post_url = f"https://www.instagram.com/p/TRL{idx:03d}/"
            if db.scalar(select(InstagramProductMap).where(InstagramProductMap.shop_id == shop.id, InstagramProductMap.instagram_post_url == post_url, InstagramProductMap.product_id == product.id)) is None:
                db.add(InstagramProductMap(shop_id=shop.id, instagram_account_id=ig.id, instagram_media_id=f"trl_media_{idx:03d}", instagram_post_url=post_url, product_id=product.id, confidence_source=ConfidenceSource.MANUAL, display_order=0, admin_label=title, is_primary=True))
        multi_url = "https://www.instagram.com/p/TRLMULTI/"
        for order, product in enumerate(products[:3]):
            if db.scalar(select(InstagramProductMap).where(InstagramProductMap.shop_id == shop.id, InstagramProductMap.instagram_post_url == multi_url, InstagramProductMap.product_id == product.id)) is None:
                db.add(InstagramProductMap(shop_id=shop.id, instagram_account_id=ig.id, instagram_media_id="trl_media_multi", instagram_post_url=multi_url, product_id=product.id, confidence_source=ConfidenceSource.MANUAL, display_order=order, admin_label=f"اسلاید {order + 1}: {product.title}", is_primary=(order == 0)))
        for label, norm, aliases in COLORS:
            for raw in [label, *aliases]:
                if db.scalar(select(ColorAlias).where(ColorAlias.shop_id == shop.id, ColorAlias.raw_value == raw, ColorAlias.language == "fa")) is None:
                    db.add(ColorAlias(shop_id=shop.id, raw_value=raw, normalized_value=norm, language="fa"))
        for size in SIZES:
            for raw in [size, size.lower(), f"سایز {size}"]:
                if db.scalar(select(SizeAlias).where(SizeAlias.shop_id == shop.id, SizeAlias.raw_value == raw, SizeAlias.category == "fashion")) is None:
                    db.add(SizeAlias(shop_id=shop.id, raw_value=raw, normalized_value=size, category="fashion"))
        if db.scalar(select(AbandonedOrderRecoveryRule).where(AbandonedOrderRecoveryRule.shop_id == shop.id)) is None:
            db.add(AbandonedOrderRecoveryRule(shop_id=shop.id, trigger_after_minutes=45, max_attempts=2, message_template="عزیزم سفارشت هنوز تکمیل نشده؛ برای کمک در پرداخت پیام بده 💛"))
        for source, target in zip(products[:5], products[5:10], strict=False):
            if db.scalar(select(ProductUpsell).where(ProductUpsell.shop_id == shop.id, ProductUpsell.source_product_id == source.id, ProductUpsell.target_product_id == target.id)) is None:
                db.add(ProductUpsell(shop_id=shop.id, source_product_id=source.id, target_product_id=target.id, message_template="با این آیتم، {target_title} هم خیلی ست میشه."))
        db.commit()
        return {"shop_id": str(shop.id), "products": len(products), "variants": len(products) * 25, "admin_email": DEMO_ADMIN_EMAIL, "operator_email": DEMO_OPERATOR_EMAIL}
    finally:
        if owns_session:
            db.close()


if __name__ == "__main__":
    print(seed_trl_demo_data(reset=False))

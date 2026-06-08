"""Seed the database with admin user, demo shops, catalog, and rich demo data.

Usage:
    python -m app.scripts.seed

Login: admin@example.com / changeme123
"""
from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select

from app.core.security import encrypt_secret
from app.db.session import SessionLocal
from app.domain.enums import ConfidenceSource, ProductStatus, UserRole
from app.domain.models import (
    InstagramAccount,
    InstagramProductMap,
    Product,
    ProductVariant,
    Shop,
    ShopMember,
)
from app.repositories.shop_repository import ShopMemberRepository, ShopRepository
from app.repositories.user_repository import UserRepository
from app.scripts.seed_demo_data import seed_rich_demo_data
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "changeme123"
DEFAULT_ADMIN_NAME = "Platform Admin"
DEFAULT_SHOP_NAME = "Demo Shop"
DEFAULT_SHOP_SLUG = "demo-shop"

DEMO_INSTAGRAM_USER_ID = "17841400000000001"
DEMO_INSTAGRAM_USERNAME = "demo_shop"
DEMO_POST_URL = "https://www.instagram.com/p/ABC123/"
DEMO_MEDIA_ID = "media-abc"
DEMO_PRODUCT_TITLE = "Demo Black Shirt"
DEMO_PRODUCT_SKU = "DEMO-BLACK-L"


def _seed_instagram_account(db, shop: Shop) -> InstagramAccount:
    account = db.scalar(
        select(InstagramAccount).where(
            InstagramAccount.shop_id == shop.id,
            InstagramAccount.ig_user_id == DEMO_INSTAGRAM_USER_ID,
        )
    )
    if account is None:
        account = InstagramAccount(
            shop_id=shop.id,
            ig_user_id=DEMO_INSTAGRAM_USER_ID,
            page_id="demo-page",
            username=DEMO_INSTAGRAM_USERNAME,
            access_token_encrypted=encrypt_secret("demo-instagram-token"),
            webhook_enabled=True,
        )
        db.add(account)
        db.flush()
        logger.info("Created demo Instagram account: %s", DEMO_INSTAGRAM_USERNAME)
    return account


def _seed_product_catalog(db, shop: Shop, account: InstagramAccount) -> None:
    product = db.scalar(
        select(Product).where(Product.shop_id == shop.id, Product.title == DEMO_PRODUCT_TITLE)
    )
    if product is None:
        product = Product(
            shop_id=shop.id,
            title=DEMO_PRODUCT_TITLE,
            description="Demo product for the Persian Instagram DM order flow.",
            status=ProductStatus.ACTIVE,
            base_price=Decimal("49.99"),
            currency="USD",
            main_image_url="https://example.com/demo-black-shirt.jpg",
        )
        db.add(product)
        db.flush()
        logger.info("Created demo product: %s", DEMO_PRODUCT_TITLE)

    variant = db.scalar(
        select(ProductVariant).where(
            ProductVariant.product_id == product.id,
            ProductVariant.sku == DEMO_PRODUCT_SKU,
        )
    )
    if variant is None:
        db.add(
            ProductVariant(
                product_id=product.id,
                color="black",
                size="L",
                sku=DEMO_PRODUCT_SKU,
                price=Decimal("49.99"),
                stock_quantity=25,
                reserved_quantity=0,
                is_active=True,
            )
        )
        logger.info("Created demo variant: %s", DEMO_PRODUCT_SKU)

    mapping = db.scalar(
        select(InstagramProductMap).where(
            InstagramProductMap.shop_id == shop.id,
            InstagramProductMap.instagram_post_url == DEMO_POST_URL,
        )
    )
    if mapping is None:
        db.add(
            InstagramProductMap(
                shop_id=shop.id,
                instagram_account_id=account.id,
                instagram_media_id=DEMO_MEDIA_ID,
                instagram_post_url=DEMO_POST_URL,
                product_id=product.id,
                confidence_source=ConfidenceSource.MANUAL,
                is_active=True,
            )
        )
        logger.info("Created demo Instagram product map: %s", DEMO_POST_URL)


def seed() -> None:
    db = SessionLocal()
    try:
        users = UserRepository(db)
        shops = ShopRepository(db)
        members = ShopMemberRepository(db)

        admin = users.get_by_email(DEFAULT_ADMIN_EMAIL)
        if admin is None:
            admin = AuthService.create_user(
                db,
                email=DEFAULT_ADMIN_EMAIL,
                password=DEFAULT_ADMIN_PASSWORD,
                full_name=DEFAULT_ADMIN_NAME,
                role=UserRole.OWNER,
            )
            logger.info("Created admin user: %s", DEFAULT_ADMIN_EMAIL)
        else:
            logger.info("Admin user already exists: %s", DEFAULT_ADMIN_EMAIL)

        shop = shops.get_by_slug(DEFAULT_SHOP_SLUG)
        if shop is None:
            shop = Shop(name=DEFAULT_SHOP_NAME, slug=DEFAULT_SHOP_SLUG)
            shops.create(shop)
            members.create(
                ShopMember(
                    shop_id=shop.id,
                    user_id=admin.id,
                    role=UserRole.OWNER,
                )
            )
            logger.info("Created demo shop: %s", DEFAULT_SHOP_SLUG)
        else:
            logger.info("Demo shop already exists: %s", DEFAULT_SHOP_SLUG)

        account = _seed_instagram_account(db, shop)
        _seed_product_catalog(db, shop, account)
        seed_rich_demo_data(db, admin, shop, account)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed()

"""Seed the database with an initial admin user and demo shop.

Usage:
    python -m app.scripts.seed
"""
from __future__ import annotations

import logging

from app.db.session import SessionLocal
from app.domain.enums import UserRole
from app.domain.models import Shop, ShopMember
from app.repositories.shop_repository import ShopMemberRepository, ShopRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "changeme123"
DEFAULT_ADMIN_NAME = "Platform Admin"
DEFAULT_SHOP_NAME = "Demo Shop"
DEFAULT_SHOP_SLUG = "demo-shop"


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
            shops.commit()
            logger.info("Created demo shop: %s", DEFAULT_SHOP_SLUG)
        else:
            logger.info("Demo shop already exists: %s", DEFAULT_SHOP_SLUG)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed()

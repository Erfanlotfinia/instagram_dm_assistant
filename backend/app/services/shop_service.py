import re
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import UserRole
from app.domain.models import Shop, ShopMember, User
from app.repositories.shop_repository import ShopMemberRepository, ShopRepository
from app.schemas.shop import (
    InstagramAccountStatusSummary,
    ShopAgentSettings,
    ShopCreate,
    ShopMemberRead,
    ShopRead,
    ShopSettingsRead,
    ShopUpdate,
)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "shop"


DEFAULT_AGENT_SETTINGS = ShopAgentSettings().model_dump()


def parse_agent_settings(raw: dict | None) -> ShopAgentSettings:
    if not raw:
        return ShopAgentSettings()
    return ShopAgentSettings.model_validate({**DEFAULT_AGENT_SETTINGS, **raw})


def shop_to_read(shop: Shop) -> ShopRead:
    data = ShopRead.model_validate(shop)
    return data.model_copy(update={"agent_settings": parse_agent_settings(shop.agent_settings)})


class ShopService:
    def __init__(self, db: Session) -> None:
        self.shops = ShopRepository(db)
        self.members = ShopMemberRepository(db)
        self.db = db

    def list_shops_for_user(self, user: User) -> list[ShopRead]:
        shops = self.shops.list_for_user(user.id)
        return [shop_to_read(shop) for shop in shops]

    def get_shop(self, shop_id: UUID, user: User) -> ShopRead:
        membership = self._require_membership(shop_id, user.id)
        shop = self.shops.get_by_id(shop_id)
        if shop is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
        _ = membership
        return shop_to_read(shop)

    def get_shop_entity(self, shop_id: UUID, user: User) -> Shop:
        self._require_membership(shop_id, user.id)
        shop = self.shops.get_by_id(shop_id)
        if shop is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
        return shop

    def create_shop(self, payload: ShopCreate, user: User) -> ShopRead:
        slug = payload.slug or slugify(payload.name)
        if self.shops.get_by_slug(slug) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A shop with this slug already exists",
            )

        shop = Shop(
            name=payload.name,
            slug=slug,
            default_currency=payload.default_currency.upper(),
            agent_settings=DEFAULT_AGENT_SETTINGS,
        )
        self.shops.create(shop)
        self.members.create(
            ShopMember(
                shop_id=shop.id,
                user_id=user.id,
                role=UserRole.OWNER,
            )
        )
        self.shops.commit()
        self.shops.refresh(shop)
        return shop_to_read(shop)

    def update_shop(self, shop_id: UUID, payload: ShopUpdate, user: User) -> ShopRead:
        shop = self.get_shop_entity(shop_id, user)
        if payload.name is not None:
            shop.name = payload.name
        if payload.default_currency is not None:
            shop.default_currency = payload.default_currency.upper()
        self.db.commit()
        self.db.refresh(shop)
        return shop_to_read(shop)

    def update_agent_settings(self, shop_id: UUID, settings: ShopAgentSettings, user: User) -> ShopRead:
        shop = self.get_shop_entity(shop_id, user)
        shop.agent_settings = settings.model_dump()
        self.db.commit()
        self.db.refresh(shop)
        return shop_to_read(shop)

    def get_settings(self, shop_id: UUID, user: User) -> ShopSettingsRead:
        from app.services.instagram_account_service import InstagramAccountService

        shop_read = self.get_shop(shop_id, user)
        accounts = InstagramAccountService(self.db).list_accounts(shop_id, user)
        account_summaries = [
            InstagramAccountStatusSummary(
                id=account.id,
                username=account.username,
                status=account.status.value if hasattr(account.status, "value") else str(account.status),
                webhook_enabled=account.webhook_enabled,
                token_expires_at=account.token_expires_at,
            )
            for account in accounts
        ]
        webhook_active = any(account.webhook_enabled for account in accounts)
        return ShopSettingsRead(
            shop=shop_read,
            instagram_accounts=account_summaries,
            webhook_active=webhook_active,
        )


    def list_members(self, shop_id: UUID, user: User) -> list[ShopMemberRead]:
        self._require_membership(shop_id, user.id)
        rows = self.members.list_for_shop(shop_id)
        return [
            ShopMemberRead(
                id=member.id,
                shop_id=member.shop_id,
                user_id=member.user_id,
                role=member.role,
                created_at=member.created_at,
                full_name=member_user.full_name,
                email=member_user.email,
            )
            for member, member_user in rows
        ]

    def _require_membership(self, shop_id: UUID, user_id: UUID) -> ShopMember:
        membership = self.members.get_membership(shop_id, user_id)
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this shop",
            )
        return membership

    def get_membership(self, shop_id: UUID, user_id: UUID) -> ShopMember | None:
        return self.members.get_membership(shop_id, user_id)

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Shop, ShopMember, User


class ShopRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, shop_id: UUID) -> Shop | None:
        return self.db.get(Shop, shop_id)

    def get_by_slug(self, slug: str) -> Shop | None:
        stmt = select(Shop).where(Shop.slug == slug)
        return self.db.scalar(stmt)

    def list_for_user(self, user_id: UUID) -> list[Shop]:
        stmt = (
            select(Shop)
            .join(ShopMember, ShopMember.shop_id == Shop.id)
            .where(ShopMember.user_id == user_id)
            .order_by(Shop.name)
        )
        return list(self.db.scalars(stmt).all())

    def create(self, shop: Shop) -> Shop:
        self.db.add(shop)
        self.db.flush()
        return shop

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, shop: Shop) -> Shop:
        self.db.refresh(shop)
        return shop


class ShopMemberRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_membership(self, shop_id: UUID, user_id: UUID) -> ShopMember | None:
        stmt = select(ShopMember).where(
            ShopMember.shop_id == shop_id,
            ShopMember.user_id == user_id,
        )
        return self.db.scalar(stmt)

    def list_for_shop(self, shop_id: UUID) -> list[tuple[ShopMember, User]]:
        stmt = (
            select(ShopMember, User)
            .join(User, User.id == ShopMember.user_id)
            .where(ShopMember.shop_id == shop_id)
            .order_by(ShopMember.created_at)
        )
        return list(self.db.execute(stmt).all())

    def create(self, member: ShopMember) -> ShopMember:
        self.db.add(member)
        self.db.flush()
        return member

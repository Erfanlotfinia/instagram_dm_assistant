from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.domain.models import InstagramProductMap


class InstagramProductMapRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, map_id: UUID) -> InstagramProductMap | None:
        return self.db.get(InstagramProductMap, map_id)

    def get_for_shop(self, shop_id: UUID, map_id: UUID) -> InstagramProductMap | None:
        stmt = select(InstagramProductMap).where(
            InstagramProductMap.id == map_id,
            InstagramProductMap.shop_id == shop_id,
        )
        return self.db.scalar(stmt)

    def list_for_shop(self, shop_id: UUID) -> list[InstagramProductMap]:
        stmt = (
            select(InstagramProductMap)
            .options(joinedload(InstagramProductMap.product))
            .where(InstagramProductMap.shop_id == shop_id)
            .order_by(InstagramProductMap.created_at.desc())
        )
        return list(self.db.scalars(stmt).unique().all())

    def find_active_by_post_url(self, shop_id: UUID, post_url: str) -> InstagramProductMap | None:
        stmt = (
            select(InstagramProductMap)
            .options(joinedload(InstagramProductMap.product))
            .where(
                InstagramProductMap.shop_id == shop_id,
                InstagramProductMap.instagram_post_url == post_url,
                InstagramProductMap.is_active.is_(True),
            )
        )
        return self.db.scalar(stmt)


    def list_active_by_post_url(self, shop_id: UUID, post_url: str) -> list[InstagramProductMap]:
        stmt = (
            select(InstagramProductMap)
            .options(joinedload(InstagramProductMap.product))
            .where(
                InstagramProductMap.shop_id == shop_id,
                InstagramProductMap.instagram_post_url == post_url,
                InstagramProductMap.is_active.is_(True),
            )
            .order_by(InstagramProductMap.display_order, InstagramProductMap.created_at)
        )
        return list(self.db.scalars(stmt).unique().all())

    def list_active_by_media_id(self, shop_id: UUID, media_id: str) -> list[InstagramProductMap]:
        stmt = (
            select(InstagramProductMap)
            .options(joinedload(InstagramProductMap.product))
            .where(
                InstagramProductMap.shop_id == shop_id,
                InstagramProductMap.instagram_media_id == media_id,
                InstagramProductMap.is_active.is_(True),
            )
            .order_by(InstagramProductMap.display_order, InstagramProductMap.created_at)
        )
        return list(self.db.scalars(stmt).unique().all())

    def find_active_by_media_id(self, shop_id: UUID, media_id: str) -> InstagramProductMap | None:
        stmt = (
            select(InstagramProductMap)
            .options(joinedload(InstagramProductMap.product))
            .where(
                InstagramProductMap.shop_id == shop_id,
                InstagramProductMap.instagram_media_id == media_id,
                InstagramProductMap.is_active.is_(True),
            )
        )
        return self.db.scalar(stmt)

    def create(self, mapping: InstagramProductMap) -> InstagramProductMap:
        self.db.add(mapping)
        self.db.flush()
        return mapping

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, mapping: InstagramProductMap) -> InstagramProductMap:
        self.db.refresh(mapping)
        return mapping

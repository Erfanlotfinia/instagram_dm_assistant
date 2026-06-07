from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import InstagramAccount


class InstagramAccountRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_shop(self, shop_id: UUID) -> list[InstagramAccount]:
        stmt = (
            select(InstagramAccount)
            .where(InstagramAccount.shop_id == shop_id)
            .order_by(InstagramAccount.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_by_ig_user_id(self, ig_user_id: str) -> InstagramAccount | None:
        stmt = select(InstagramAccount).where(InstagramAccount.ig_user_id == ig_user_id)
        return self.db.scalar(stmt)

    def create(self, account: InstagramAccount) -> InstagramAccount:
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

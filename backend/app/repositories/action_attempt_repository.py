from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import ActionAttempt


class ActionAttemptRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, attempt: ActionAttempt) -> ActionAttempt:
        self.db.add(attempt)
        self.db.flush()
        return attempt

    def list_for_order(self, shop_id: UUID, order_id: UUID) -> list[ActionAttempt]:
        stmt = (
            select(ActionAttempt)
            .where(ActionAttempt.shop_id == shop_id, ActionAttempt.order_id == order_id)
            .order_by(ActionAttempt.created_at)
        )
        return list(self.db.scalars(stmt).all())

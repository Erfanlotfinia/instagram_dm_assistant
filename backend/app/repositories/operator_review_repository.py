from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import OperatorReview


class OperatorReviewRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, review: OperatorReview) -> OperatorReview:
        self.db.add(review)
        self.db.flush()
        return review

    def list_for_order(self, shop_id: UUID, order_id: UUID) -> list[OperatorReview]:
        stmt = (
            select(OperatorReview)
            .where(OperatorReview.shop_id == shop_id, OperatorReview.order_id == order_id)
            .order_by(OperatorReview.created_at)
        )
        return list(self.db.scalars(stmt).all())

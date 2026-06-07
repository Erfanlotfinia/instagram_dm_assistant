from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Payment


class PaymentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, payment_id: UUID) -> Payment | None:
        return self.db.get(Payment, payment_id)

    def get_by_provider_reference(self, provider_reference: str) -> Payment | None:
        stmt = select(Payment).where(Payment.provider_reference == provider_reference)
        return self.db.scalar(stmt)

    def get_latest_for_order(self, order_id: UUID) -> Payment | None:
        stmt = (
            select(Payment)
            .where(Payment.order_id == order_id)
            .order_by(Payment.created_at.desc())
        )
        return self.db.scalar(stmt)

    def create(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.flush()
        return payment

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, payment: Payment) -> Payment:
        self.db.refresh(payment)
        return payment

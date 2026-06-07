from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Customer


class CustomerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, customer_id: UUID) -> Customer | None:
        return self.db.get(Customer, customer_id)

    def get_by_instagram_user_id(self, shop_id: UUID, instagram_user_id: str) -> Customer | None:
        stmt = select(Customer).where(
            Customer.shop_id == shop_id,
            Customer.instagram_user_id == instagram_user_id,
        )
        return self.db.scalar(stmt)

    def create(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.flush()
        return customer

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.enums import OrderPaymentStatus
from app.domain.models import Customer, Order
from app.repositories.customer_repository import CustomerRepository
from app.repositories.order_repository import OrderRepository
from app.schemas.customer import CustomerProfileRead, CustomerUpdate, PreviousOrderSummary
from app.services.audit_service import AuditService
from app.services.customer_preferences_service import CustomerPreferencesService
from app.services.shop_service import ShopService


class CustomerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.customers = CustomerRepository(db)
        self.orders = OrderRepository(db)
        self.shop_service = ShopService(db)

    def get_profile(self, shop_id: UUID, customer_id: UUID, user) -> CustomerProfileRead:
        self.shop_service.get_shop(shop_id, user)
        customer = self._get_customer_or_404(shop_id, customer_id)
        return self._build_profile(customer)

    def update_customer(
        self,
        shop_id: UUID,
        customer_id: UUID,
        user,
        payload: CustomerUpdate,
    ) -> CustomerProfileRead:
        self.shop_service.get_shop(shop_id, user)
        customer = self._get_customer_or_404(shop_id, customer_id)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(customer, field, value)
        AuditService(self.db).log(
            action="customer_profile_updated",
            entity_type="customer",
            shop_id=shop_id,
            actor_user_id=user.id,
            entity_id=str(customer.id),
            metadata={"updated_fields": list(updates.keys())},
        )
        self.db.commit()
        self.db.refresh(customer)
        return self._build_profile(customer)

    def _get_customer_or_404(self, shop_id: UUID, customer_id: UUID) -> Customer:
        customer = self.customers.get_by_id(customer_id)
        if customer is None or customer.shop_id != shop_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
        return customer

    def _build_profile(self, customer: Customer) -> CustomerProfileRead:
        orders = self.orders.list_for_customer(customer.id)
        paid_orders = [o for o in orders if o.payment_status == OrderPaymentStatus.PAID]
        total_paid = sum((o.total_amount for o in paid_orders), Decimal("0"))
        last_purchase: datetime | None = None
        if paid_orders:
            last_purchase = max(o.updated_at for o in paid_orders)

        preferred_sizes, preferred_colors = self._extract_preferences(orders)
        prefs = CustomerPreferencesService(self.db).get_or_create(customer.id)
        if prefs.preferred_size:
            preferred_sizes = [prefs.preferred_size, *[s for s in preferred_sizes if s != prefs.preferred_size]]
        if prefs.preferred_colors:
            preferred_colors = list(dict.fromkeys((prefs.preferred_colors or []) + preferred_colors))
        previous = [
            PreviousOrderSummary(
                id=o.id,
                status=o.status.value,
                payment_status=o.payment_status.value,
                total_amount=str(o.total_amount),
                created_at=o.created_at,
            )
            for o in orders[:10]
        ]

        return CustomerProfileRead(
            id=customer.id,
            instagram_user_id=customer.instagram_user_id,
            full_name=customer.full_name,
            phone=customer.phone,
            city=customer.city,
            address=customer.address,
            postal_code=customer.postal_code,
            notes=customer.notes,
            previous_orders=previous,
            preferred_size=preferred_sizes[0] if preferred_sizes else None,
            preferred_colors=preferred_colors,
            last_successful_size=prefs.last_successful_size,
            last_purchase_at=last_purchase,
            total_paid_amount=str(total_paid),
            order_count=len(orders),
            is_repeat_customer=len(paid_orders) >= 2,
        )

    @staticmethod
    def _extract_preferences(orders: list[Order]) -> tuple[list[str], list[str]]:
        sizes: list[str] = []
        colors: list[str] = []
        for order in orders:
            for item in order.items:
                if item.variant_size_snapshot and item.variant_size_snapshot not in sizes:
                    sizes.append(item.variant_size_snapshot)
                if item.variant_color_snapshot and item.variant_color_snapshot not in colors:
                    colors.append(item.variant_color_snapshot)
        return sizes, colors

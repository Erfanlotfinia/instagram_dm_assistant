from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import MessageDirection, OrderPaymentStatus, OrderRecoveryAttemptStatus, OrderRecoveryStatus, OrderStatus
from app.domain.models import CustomerPreferences, Order, OrderItem
from app.services.shop_service import ShopService

logger = logging.getLogger(__name__)

SAME_SIZE_PATTERNS = (
    r"همون\s*سایز\s*قبلی",
    r"same\s*(as\s*)?(my\s*)?(previous|last)\s*size",
    r"previous\s*size",
    r"last\s*size",
)


class CustomerPreferencesService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.shop_service = ShopService(db)

    def get_preferences(self, shop_id: UUID, customer_id: UUID, user) -> CustomerPreferences | None:
        from app.repositories.customer_repository import CustomerRepository

        self.shop_service.get_shop(shop_id, user)
        customer = CustomerRepository(db).get_by_id(customer_id)
        if customer is None or customer.shop_id != shop_id:
            return None
        return self.db.scalar(
            select(CustomerPreferences).where(CustomerPreferences.customer_id == customer_id)
        )

    def get_or_create(self, customer_id: UUID) -> CustomerPreferences:
        prefs = self.db.scalar(
            select(CustomerPreferences).where(CustomerPreferences.customer_id == customer_id)
        )
        if prefs is None:
            prefs = CustomerPreferences(customer_id=customer_id)
            self.db.add(prefs)
            self.db.flush()
        return prefs

    def update_from_paid_order(self, order: Order) -> CustomerPreferences:
        prefs = self.get_or_create(order.customer_id)
        size_counts: dict[str, int] = {}
        color_counts: dict[str, int] = {}
        categories: set[str] = set()

        for item in order.items:
            if item.variant_size_snapshot:
                size_counts[item.variant_size_snapshot] = size_counts.get(item.variant_size_snapshot, 0) + 1
            if item.variant_color_snapshot:
                color_counts[item.variant_color_snapshot] = color_counts.get(item.variant_color_snapshot, 0) + 1
            if item.product_id:
                from app.repositories.product_repository import ProductRepository

                product = ProductRepository(self.db).get_by_id(item.product_id)
                if product and product.category:
                    categories.add(product.category)

        if size_counts:
            preferred_size = max(size_counts, key=size_counts.get)
            prefs.preferred_size = preferred_size
            prefs.last_successful_size = preferred_size
        if color_counts:
            ranked_colors = sorted(color_counts, key=lambda c: color_counts[c], reverse=True)
            prefs.preferred_colors = ranked_colors[:5]
        if categories:
            existing = set(prefs.preferred_categories or [])
            prefs.preferred_categories = list(existing | categories)[:10]

        prefs.last_successful_city = order.city or prefs.last_successful_city
        prefs.updated_at = datetime.now(UTC)
        self.db.flush()
        logger.info(
            "Updated customer preferences customer=%s from paid order=%s",
            order.customer_id,
            order.id,
        )
        return prefs

    def detect_same_size_request(self, message_text: str | None) -> bool:
        if not message_text:
            return False
        normalized = message_text.strip().casefold()
        for pattern in SAME_SIZE_PATTERNS:
            if re.search(pattern, normalized, re.IGNORECASE):
                return True
        return False

    def resolve_size_from_preferences(
        self,
        customer_id: UUID,
        *,
        confidence_threshold: float = 0.85,
    ) -> tuple[str | None, float, bool]:
        """Return (size, confidence, needs_confirmation)."""
        prefs = self.db.scalar(
            select(CustomerPreferences).where(CustomerPreferences.customer_id == customer_id)
        )
        if prefs is None:
            return None, 0.0, True

        size = prefs.last_successful_size or prefs.preferred_size
        if not size:
            return None, 0.0, True

        paid_count = self.db.scalar(
            select(func.count(Order.id)).where(
                Order.customer_id == customer_id,
                Order.payment_status == OrderPaymentStatus.PAID,
            )
        ) or 0
        confidence = 0.95 if paid_count >= 2 and prefs.last_successful_size else 0.75 if paid_count >= 1 else 0.5
        needs_confirmation = confidence < confidence_threshold
        return size, confidence, needs_confirmation

    @staticmethod
    def to_read(prefs: CustomerPreferences):
        from app.schemas.customer_preferences import CustomerPreferencesRead

        return CustomerPreferencesRead(
            id=prefs.id,
            customer_id=prefs.customer_id,
            preferred_size=prefs.preferred_size,
            preferred_colors=prefs.preferred_colors or [],
            preferred_categories=prefs.preferred_categories or [],
            last_successful_size=prefs.last_successful_size,
            last_successful_city=prefs.last_successful_city,
            last_successful_address_id=prefs.last_successful_address_id,
            updated_at=prefs.updated_at,
        )

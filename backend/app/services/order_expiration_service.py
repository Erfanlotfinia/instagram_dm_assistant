from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.services.order_service import OrderService

logger = logging.getLogger(__name__)


class OrderExpirationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.order_service = OrderService(db)

    def expire_stale_orders(self) -> int:
        now = datetime.now(UTC)
        candidates = self.order_service.orders.list_expired_candidates(now)
        expired_count = 0
        for order in candidates:
            self.order_service.expire_order(order)
            expired_count += 1
            logger.info("Expired stale order order=%s", order.id)
        return expired_count

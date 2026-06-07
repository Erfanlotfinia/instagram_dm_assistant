from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.domain.enums import (
    ConversationState,
    MessageDirection,
    OrderPaymentStatus,
    OrderStatus,
)
from app.domain.models import Conversation, ConversationSlots, Message, Order, Product, ProductVariant
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.dashboard import (
    ConversionFunnelMetrics,
    DashboardMetrics,
    LowStockVariantSummary,
)
from app.schemas.shop import ShopAgentSettings
from app.services.shop_service import ShopService


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.conversations = ConversationRepository(db)
        self.orders = OrderRepository(db)
        self.products = ProductRepository(db)
        self.variants = VariantRepository(db)
        self.shop_service = ShopService(db)

    def get_metrics(self, shop_id: UUID, user) -> DashboardMetrics:
        shop_read = self.shop_service.get_shop(shop_id, user)
        settings = shop_read.agent_settings
        threshold = settings.low_stock_threshold

        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

        today_orders = self._count_orders_since(shop_id, today_start)
        paid_orders = self._count_orders_by_payment(shop_id, OrderPaymentStatus.PAID)
        waiting_for_payment = self._count_orders_by_status(shop_id, OrderStatus.WAITING_FOR_PAYMENT)
        handoff_conversations = self._count_handoff_conversations(shop_id)
        low_stock = self._list_low_stock_variants(shop_id, threshold)
        funnel = self._build_conversion_funnel(shop_id)

        return DashboardMetrics(
            today_orders=today_orders,
            paid_orders=paid_orders,
            waiting_for_payment=waiting_for_payment,
            handoff_conversations=handoff_conversations,
            low_stock_variants=low_stock,
            conversion_funnel=funnel,
        )

    def _count_orders_since(self, shop_id: UUID, since: datetime) -> int:
        stmt = select(func.count()).select_from(Order).where(
            Order.shop_id == shop_id,
            Order.created_at >= since,
        )
        return int(self.db.scalar(stmt) or 0)

    def _count_orders_by_payment(self, shop_id: UUID, payment_status: OrderPaymentStatus) -> int:
        stmt = select(func.count()).select_from(Order).where(
            Order.shop_id == shop_id,
            Order.payment_status == payment_status,
        )
        return int(self.db.scalar(stmt) or 0)

    def _count_orders_by_status(self, shop_id: UUID, status: OrderStatus) -> int:
        stmt = select(func.count()).select_from(Order).where(
            Order.shop_id == shop_id,
            Order.status == status,
        )
        return int(self.db.scalar(stmt) or 0)

    def _count_handoff_conversations(self, shop_id: UUID) -> int:
        stmt = select(func.count()).select_from(Conversation).where(
            Conversation.shop_id == shop_id,
            Conversation.handoff_required.is_(True),
            Conversation.state != ConversationState.CLOSED,
        )
        return int(self.db.scalar(stmt) or 0)

    def _list_low_stock_variants(self, shop_id: UUID, threshold: int) -> list[LowStockVariantSummary]:
        stmt = (
            select(ProductVariant, Product)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(
                Product.shop_id == shop_id,
                ProductVariant.is_active.is_(True),
            )
        )
        results: list[LowStockVariantSummary] = []
        for variant, product in self.db.execute(stmt).all():
            available = variant.available_stock
            if available <= threshold:
                results.append(
                    LowStockVariantSummary(
                        variant_id=variant.id,
                        product_id=product.id,
                        product_title=product.title,
                        sku=variant.sku,
                        color=variant.color,
                        size=variant.size,
                        available_stock=available,
                    )
                )
        results.sort(key=lambda item: item.available_stock)
        return results

    def _build_conversion_funnel(self, shop_id: UUID) -> ConversionFunnelMetrics:
        inbound_messages = int(
            self.db.scalar(
                select(func.count())
                .select_from(Message)
                .join(Conversation, Conversation.id == Message.conversation_id)
                .where(
                    Conversation.shop_id == shop_id,
                    Message.direction == MessageDirection.INBOUND,
                )
            )
            or 0
        )

        product_resolved = int(
            self.db.scalar(
                select(func.count())
                .select_from(ConversationSlots)
                .join(Conversation, Conversation.id == ConversationSlots.conversation_id)
                .where(
                    Conversation.shop_id == shop_id,
                    ConversationSlots.product_id.is_not(None),
                )
            )
            or 0
        )

        draft_orders = int(
            self.db.scalar(
                select(func.count())
                .select_from(Order)
                .where(
                    Order.shop_id == shop_id,
                    Order.status.in_(
                        [
                            OrderStatus.DRAFT,
                            OrderStatus.WAITING_FOR_CONFIRMATION,
                        ]
                    ),
                )
            )
            or 0
        )

        paid_orders = self._count_orders_by_payment(shop_id, OrderPaymentStatus.PAID)

        return ConversionFunnelMetrics(
            inbound_messages=inbound_messages,
            product_resolved=product_resolved,
            draft_orders=draft_orders,
            paid_orders=paid_orders,
        )

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import (
    ConversationState,
    MessageDirection,
    OrderPaymentStatus,
    OrderRecoveryStatus,
    OrderStatus,
)
from app.domain.models import (
    AgentDecisionTrace,
    Conversation,
    ConversationSlots,
    FailedJob,
    Message,
    Order,
    Product,
    ProductVariant,
    UnavailableDemandLog,
)
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.variant_repository import VariantRepository
from app.schemas.dashboard import (
    ConversionFunnelMetrics,
    DashboardMetrics,
    DashboardTrendPoint,
    DashboardTrends,
    LostDemandVariantSummary,
    LowStockVariantSummary,
    TopSellingPostSummary,
)
from app.services.shop_service import ShopService
from app.services.upsell_service import UpsellService


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
        waiting_for_payment = self._count_orders_by_status(shop_id, OrderStatus.PAYMENT_PENDING)
        handoff_conversations = self._count_handoff_conversations(shop_id)
        low_stock = self._list_low_stock_variants(shop_id, threshold)
        funnel = self._build_conversion_funnel(shop_id)
        abandoned_orders = self._count_abandoned_orders(shop_id)
        recovered_orders, recovered_revenue = self._recovery_stats(shop_id)
        upsell_suggestions, upsell_accepted = UpsellService.count_suggestions(self.db, shop_id)
        top_posts = self._top_selling_posts(shop_id)
        top_lost = self._top_lost_demand(shop_id)
        week_start = today_start - timedelta(days=6)
        active_conversations = self._count_active_conversations(shop_id)
        messages_today = self._count_inbound_messages_since(shop_id, today_start)
        messages_week = self._count_inbound_messages_since(shop_id, week_start)
        automation_rate, llm_rate, handoff_rate = self._automation_rates(shop_id)
        failed_jobs_count = self._count_failed_jobs(shop_id)

        return DashboardMetrics(
            today_orders=today_orders,
            paid_orders=paid_orders,
            waiting_for_payment=waiting_for_payment,
            handoff_conversations=handoff_conversations,
            abandoned_orders=abandoned_orders,
            recovered_orders=recovered_orders,
            recovered_revenue=str(recovered_revenue),
            upsell_suggestions=upsell_suggestions,
            upsell_accepted=upsell_accepted,
            active_conversations=active_conversations,
            messages_today=messages_today,
            messages_week=messages_week,
            automation_success_rate=automation_rate,
            llm_fallback_rate=llm_rate,
            handoff_rate=handoff_rate,
            failed_jobs_count=failed_jobs_count,
            top_selling_posts=top_posts,
            top_lost_demand_variants=top_lost,
            low_stock_variants=low_stock,
            conversion_funnel=funnel,
        )

    def get_trends(self, shop_id: UUID, user, period: str = "7d") -> DashboardTrends:
        """Daily activity series used by the Overview charts."""
        self.shop_service.get_shop(shop_id, user)
        days = 30 if period == "30d" else 7
        now = datetime.now(UTC)
        start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

        messages_by_day = self._inbound_messages_by_day(shop_id, start)
        traces_by_day = self._trace_outcomes_by_day(shop_id, start)
        conversions_by_day = self._paid_orders_by_day(shop_id, start)

        points: list[DashboardTrendPoint] = []
        for offset in range(days):
            day = (start + timedelta(days=offset)).date()
            key = day.isoformat()
            automated, llm, handoff = traces_by_day.get(key, (0, 0, 0))
            points.append(
                DashboardTrendPoint(
                    date=day.strftime("%b %d"),
                    messages=messages_by_day.get(key, 0),
                    automated=automated,
                    llm=llm,
                    handoff=handoff,
                    conversions=conversions_by_day.get(key, 0),
                )
            )
        return DashboardTrends(period=period, points=points)

    def _count_active_conversations(self, shop_id: UUID) -> int:
        stmt = select(func.count()).select_from(Conversation).where(
            Conversation.shop_id == shop_id,
            Conversation.state == ConversationState.OPEN,
        )
        return int(self.db.scalar(stmt) or 0)

    def _count_inbound_messages_since(self, shop_id: UUID, since: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Conversation.shop_id == shop_id,
                Message.direction == MessageDirection.INBOUND,
                Message.created_at >= since,
            )
        )
        return int(self.db.scalar(stmt) or 0)

    def _automation_rates(self, shop_id: UUID) -> tuple[float, float, float]:
        rows = self.db.execute(
            select(
                AgentDecisionTrace.auto_send_allowed,
                AgentDecisionTrace.human_handoff_required,
            )
            .join(Conversation, Conversation.id == AgentDecisionTrace.conversation_id)
            .where(Conversation.shop_id == shop_id)
        ).all()
        total = len(rows)
        if total == 0:
            return 0.0, 0.0, 0.0
        automated = sum(1 for auto, _ in rows if auto)
        handoff = sum(1 for _, ho in rows if ho)
        llm = total - automated - handoff
        return (
            round(automated / total, 4),
            round(max(llm, 0) / total, 4),
            round(handoff / total, 4),
        )

    def _count_failed_jobs(self, shop_id: UUID) -> int:
        stmt = select(func.count()).select_from(FailedJob).where(
            FailedJob.shop_id == shop_id,
            FailedJob.resolved.is_(False),
        )
        return int(self.db.scalar(stmt) or 0)

    def _inbound_messages_by_day(self, shop_id: UUID, start: datetime) -> dict[str, int]:
        rows = self.db.execute(
            select(func.date(Message.created_at), func.count())
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Conversation.shop_id == shop_id,
                Message.direction == MessageDirection.INBOUND,
                Message.created_at >= start,
            )
            .group_by(func.date(Message.created_at))
        ).all()
        return {str(day): int(count) for day, count in rows}

    def _trace_outcomes_by_day(self, shop_id: UUID, start: datetime) -> dict[str, tuple[int, int, int]]:
        rows = self.db.execute(
            select(
                func.date(AgentDecisionTrace.created_at),
                AgentDecisionTrace.auto_send_allowed,
                AgentDecisionTrace.human_handoff_required,
            )
            .join(Conversation, Conversation.id == AgentDecisionTrace.conversation_id)
            .where(
                Conversation.shop_id == shop_id,
                AgentDecisionTrace.created_at >= start,
            )
        ).all()
        buckets: dict[str, tuple[int, int, int]] = {}
        for day, auto, handoff in rows:
            automated, llm, ho = buckets.get(str(day), (0, 0, 0))
            if handoff:
                ho += 1
            elif auto:
                automated += 1
            else:
                llm += 1
            buckets[str(day)] = (automated, llm, ho)
        return buckets

    def _paid_orders_by_day(self, shop_id: UUID, start: datetime) -> dict[str, int]:
        rows = self.db.execute(
            select(func.date(Order.created_at), func.count())
            .where(
                Order.shop_id == shop_id,
                Order.payment_status == OrderPaymentStatus.PAID,
                Order.created_at >= start,
            )
            .group_by(func.date(Order.created_at))
        ).all()
        return {str(day): int(count) for day, count in rows}

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
                            OrderStatus.READY_FOR_CONFIRMATION,
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

    def _count_abandoned_orders(self, shop_id: UUID) -> int:
        stmt = select(func.count()).select_from(Order).where(
            Order.shop_id == shop_id,
            Order.status.in_([OrderStatus.EXPIRED, OrderStatus.CANCELLED]),
            Order.payment_status != OrderPaymentStatus.PAID,
            Order.recovery_status.in_([
                OrderRecoveryStatus.NONE,
                OrderRecoveryStatus.ELIGIBLE,
                OrderRecoveryStatus.IN_PROGRESS,
                OrderRecoveryStatus.FAILED,
            ]),
        )
        waiting = select(func.count()).select_from(Order).where(
            Order.shop_id == shop_id,
            Order.status == OrderStatus.PAYMENT_PENDING,
            Order.payment_status != OrderPaymentStatus.PAID,
        )
        return int(self.db.scalar(stmt) or 0) + int(self.db.scalar(waiting) or 0)

    def _recovery_stats(self, shop_id: UUID) -> tuple[int, float]:
        from decimal import Decimal

        recovered = int(
            self.db.scalar(
                select(func.count()).select_from(Order).where(
                    Order.shop_id == shop_id,
                    Order.recovery_status == OrderRecoveryStatus.RECOVERED,
                )
            )
            or 0
        )
        revenue = self.db.scalar(
            select(func.coalesce(func.sum(Order.total_amount), 0)).where(
                Order.shop_id == shop_id,
                Order.recovery_status == OrderRecoveryStatus.RECOVERED,
                Order.payment_status == OrderPaymentStatus.PAID,
            )
        ) or Decimal("0")
        return recovered, float(revenue)

    def _top_selling_posts(self, shop_id: UUID, limit: int = 5) -> list[TopSellingPostSummary]:
        from decimal import Decimal

        from app.domain.models import ConversationSlots

        slots = self.db.scalars(
            select(ConversationSlots).join(Conversation).where(
                Conversation.shop_id == shop_id,
                ConversationSlots.instagram_post_url.is_not(None),
            )
        ).all()
        conversation_posts = {slot.conversation_id: slot.instagram_post_url for slot in slots}
        rows: dict[str, TopSellingPostSummary] = {}
        orders = self.db.scalars(select(Order).where(Order.shop_id == shop_id)).all()
        for order in orders:
            url = conversation_posts.get(order.conversation_id)
            if not url:
                continue
            row = rows.setdefault(url, TopSellingPostSummary(instagram_post_url=url))
            if order.payment_status == OrderPaymentStatus.PAID:
                row.paid_orders += 1
                row.revenue = str(Decimal(row.revenue) + Decimal(str(order.total_amount)))
        ranked = sorted(rows.values(), key=lambda r: (Decimal(r.revenue), r.paid_orders), reverse=True)
        return ranked[:limit]

    def _top_lost_demand(self, shop_id: UUID, limit: int = 5) -> list[LostDemandVariantSummary]:
        stmt = (
            select(
                UnavailableDemandLog.requested_color_normalized,
                UnavailableDemandLog.requested_size_normalized,
                UnavailableDemandLog.product_id,
                func.count(UnavailableDemandLog.id),
            )
            .where(UnavailableDemandLog.shop_id == shop_id)
            .group_by(
                UnavailableDemandLog.requested_color_normalized,
                UnavailableDemandLog.requested_size_normalized,
                UnavailableDemandLog.product_id,
            )
            .order_by(func.count(UnavailableDemandLog.id).desc())
            .limit(limit)
        )
        return [
            LostDemandVariantSummary(
                requested_color=color,
                requested_size=size,
                product_id=product_id,
                count=count,
            )
            for color, size, product_id, count in self.db.execute(stmt).all()
        ]

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import MessageDirection, OrderPaymentStatus, OrderStatus
from app.domain.models import Conversation, ConversationSlots, Message, Order, UnavailableDemandLog
from app.domain.models import User
from app.schemas.analytics import FunnelAnalytics, HandoffAnalyticsRow, PostPerformanceRow, PostRevenueRow, ResponseTimeAnalytics, StockDemandRow, UnavailableDemandRow
from app.services.shop_service import ShopService


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.shop_service = ShopService(db)

    def funnel(self, shop_id: UUID, user: User, start: datetime | None = None, end: datetime | None = None) -> FunnelAnalytics:
        self.shop_service.get_shop(shop_id, user)
        inbound = self._count_inbound(shop_id, start, end)
        resolved_products = self._count_slots(shop_id, ConversationSlots.product_id.is_not(None), start, end)
        resolved_variants = self._count_slots(shop_id, ConversationSlots.product_variant_id.is_not(None), start, end)
        drafts = self._count_orders(shop_id, Order.status.in_([OrderStatus.DRAFT, OrderStatus.WAITING_FOR_CONFIRMATION, OrderStatus.WAITING_FOR_PAYMENT, OrderStatus.PAID]), start, end)
        paid = self._count_orders(shop_id, Order.payment_status == OrderPaymentStatus.PAID, start, end)
        revenue = self.db.scalar(self._range(select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.shop_id == shop_id, Order.payment_status == OrderPaymentStatus.PAID), Order.created_at, start, end)) or Decimal("0")
        total_conversations = self._count_conversations(shop_id, start, end)
        handoffs = self._count_conversations(shop_id, start, end, Conversation.handoff_required.is_(True))
        reasons = Counter(self.db.scalars(self._range(select(Conversation.handoff_reason).where(Conversation.shop_id == shop_id, Conversation.handoff_reason.is_not(None)), Conversation.created_at, start, end)).all())
        return FunnelAnalytics(
            inbound_messages=inbound,
            product_resolved_count=resolved_products,
            variant_resolved_count=resolved_variants,
            draft_orders=drafts,
            confirmed_orders=self._count_orders(shop_id, Order.status == OrderStatus.CONFIRMED, start, end),
            waiting_for_payment=self._count_orders(shop_id, Order.status == OrderStatus.WAITING_FOR_PAYMENT, start, end),
            resolved_product_rate=self._rate(resolved_products, inbound),
            variant_resolved_rate=self._rate(resolved_variants, inbound),
            draft_order_rate=self._rate(drafts, inbound),
            payment_conversion_rate=self._rate(paid, drafts),
            paid_orders=paid,
            revenue=revenue,
            abandoned_conversations=max(total_conversations - drafts - handoffs, 0),
            top_abandoned_reason=reasons.most_common(1)[0][0] if reasons else None,
            operator_handoff_rate=self._rate(handoffs, total_conversations),
        )

    def posts(self, shop_id: UUID, user: User, start: datetime | None = None, end: datetime | None = None) -> list[PostPerformanceRow]:
        self.shop_service.get_shop(shop_id, user)
        slots = self.db.scalars(self._range(select(ConversationSlots).join(Conversation).where(Conversation.shop_id == shop_id, ConversationSlots.instagram_post_url.is_not(None)), Conversation.created_at, start, end)).all()
        rows: dict[str, PostPerformanceRow] = {}
        for slot in slots:
            row = rows.setdefault(slot.instagram_post_url, PostPerformanceRow(instagram_post_url=slot.instagram_post_url, product_id=slot.product_id))
            row.inbound_messages += 1
        orders = self.db.scalars(self._range(select(Order).where(Order.shop_id == shop_id), Order.created_at, start, end)).all()
        by_conversation = {slot.conversation_id: slot.instagram_post_url for slot in slots}
        for order in orders:
            url = by_conversation.get(order.conversation_id)
            if not url:
                continue
            row = rows.setdefault(url, PostPerformanceRow(instagram_post_url=url))
            row.draft_orders += 1
            if order.payment_status == OrderPaymentStatus.PAID:
                row.paid_orders += 1
                row.revenue += Decimal(str(order.total_amount))
            row.conversion_rate = self._rate(row.paid_orders, max(row.inbound_messages, 1))
        return sorted(rows.values(), key=lambda r: (r.paid_orders, r.revenue), reverse=True)

    def post_revenue(
        self, shop_id: UUID, user: User, start: datetime | None = None, end: datetime | None = None
    ) -> list[PostRevenueRow]:
        self.shop_service.get_shop(shop_id, user)
        slots = self.db.scalars(
            self._range(
                select(ConversationSlots).join(Conversation).where(
                    Conversation.shop_id == shop_id,
                    ConversationSlots.instagram_post_url.is_not(None),
                ),
                Conversation.created_at,
                start,
                end,
            )
        ).all()
        rows: dict[str, PostRevenueRow] = {}
        conversation_posts: dict[UUID, str] = {}
        for slot in slots:
            url = slot.instagram_post_url
            conversation_posts[slot.conversation_id] = url
            row = rows.setdefault(
                url,
                PostRevenueRow(instagram_post_url=url, product_id=slot.product_id),
            )
            row.conversations += 1

        orders = self.db.scalars(
            self._range(select(Order).where(Order.shop_id == shop_id), Order.created_at, start, end)
        ).all()
        for order in orders:
            url = conversation_posts.get(order.conversation_id)
            if not url:
                continue
            row = rows.setdefault(url, PostRevenueRow(instagram_post_url=url))
            if order.status in {
                OrderStatus.DRAFT,
                OrderStatus.WAITING_FOR_CONFIRMATION,
                OrderStatus.WAITING_FOR_PAYMENT,
                OrderStatus.PAID,
            }:
                row.draft_orders += 1
            if order.payment_status == OrderPaymentStatus.PAID:
                row.paid_orders += 1
                row.revenue += Decimal(str(order.total_amount))
            row.conversion_rate = self._rate(row.paid_orders, max(row.conversations, 1))
            abandoned = max(row.draft_orders - row.paid_orders, 0)
            row.abandoned_rate = self._rate(abandoned, max(row.draft_orders, 1))
        return sorted(rows.values(), key=lambda r: (r.revenue, r.paid_orders), reverse=True)

    def stock_demand(self, shop_id: UUID, user: User, start: datetime | None = None, end: datetime | None = None) -> list[StockDemandRow]:
        self.shop_service.get_shop(shop_id, user)
        logs = self.db.scalars(
            self._range(
                select(UnavailableDemandLog).where(UnavailableDemandLog.shop_id == shop_id),
                UnavailableDemandLog.created_at,
                start,
                end,
            )
        ).all()
        colors: Counter[str] = Counter()
        sizes: Counter[str] = Counter()
        for log in logs:
            if log.requested_color_normalized:
                colors[log.requested_color_normalized] += 1
            if log.requested_size_normalized:
                sizes[log.requested_size_normalized] += 1
        return [StockDemandRow(type="color", value=k, requests=v) for k, v in colors.most_common(10)] + [
            StockDemandRow(type="size", value=k, requests=v) for k, v in sizes.most_common(10)
        ]

    def handoff(self, shop_id: UUID, user: User, start: datetime | None = None, end: datetime | None = None) -> list[HandoffAnalyticsRow]:
        self.shop_service.get_shop(shop_id, user)
        total = self._count_conversations(shop_id, start, end) or 1
        reasons = Counter(self.db.scalars(self._range(select(Conversation.handoff_reason).where(Conversation.shop_id == shop_id, Conversation.handoff_required.is_(True)), Conversation.created_at, start, end)).all())
        return [HandoffAnalyticsRow(reason=reason or "unknown", count=count, rate=self._rate(count, total)) for reason, count in reasons.most_common()]



    def unavailable_demand(self, shop_id: UUID, user: User, start: datetime | None = None, end: datetime | None = None) -> list[UnavailableDemandRow]:
        self.shop_service.get_shop(shop_id, user)
        rows = self.db.execute(
            self._range(
                select(
                    UnavailableDemandLog.requested_color_normalized,
                    UnavailableDemandLog.requested_size_normalized,
                    UnavailableDemandLog.product_id,
                    func.count(UnavailableDemandLog.id),
                    func.coalesce(func.sum(UnavailableDemandLog.estimated_lost_revenue), 0),
                )
                .where(UnavailableDemandLog.shop_id == shop_id)
                .group_by(
                    UnavailableDemandLog.requested_color_normalized,
                    UnavailableDemandLog.requested_size_normalized,
                    UnavailableDemandLog.product_id,
                ),
                UnavailableDemandLog.created_at,
                start,
                end,
            )
        ).all()
        return [
            UnavailableDemandRow(
                requested_color=color,
                requested_size=size,
                product_id=product_id,
                count=count,
                lost_revenue_estimate=lost,
            )
            for color, size, product_id, count, lost in rows
        ]

    def response_time(self, shop_id: UUID, user: User, start: datetime | None = None, end: datetime | None = None) -> ResponseTimeAnalytics:
        self.shop_service.get_shop(shop_id, user)
        # Conservative placeholders until event timestamps are fully normalized across channels.
        return ResponseTimeAnalytics(
            average_first_response_time_seconds=self.funnel(shop_id, user, start, end).average_time_to_first_response_seconds,
            average_time_to_draft_order_seconds=None,
            average_time_to_payment_seconds=self.funnel(shop_id, user, start, end).average_time_to_payment_seconds,
        )

    def _range(self, stmt, column, start, end):
        if start:
            stmt = stmt.where(column >= start)
        if end:
            stmt = stmt.where(column <= end)
        return stmt
    def _rate(self, numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 4) if denominator else 0.0
    def _count_inbound(self, shop_id, start, end):
        stmt = select(func.count(Message.id)).join(Conversation).where(Conversation.shop_id == shop_id, Message.direction == MessageDirection.INBOUND)
        return self.db.scalar(self._range(stmt, Message.created_at, start, end)) or 0
    def _count_slots(self, shop_id, predicate, start, end):
        stmt = select(func.count(ConversationSlots.id)).join(Conversation).where(Conversation.shop_id == shop_id, predicate)
        return self.db.scalar(self._range(stmt, Conversation.created_at, start, end)) or 0
    def _count_orders(self, shop_id, predicate, start, end):
        stmt = select(func.count(Order.id)).where(Order.shop_id == shop_id, predicate)
        return self.db.scalar(self._range(stmt, Order.created_at, start, end)) or 0
    def _count_conversations(self, shop_id, start, end, predicate=None):
        stmt = select(func.count(Conversation.id)).where(Conversation.shop_id == shop_id)
        if predicate is not None:
            stmt = stmt.where(predicate)
        return self.db.scalar(self._range(stmt, Conversation.created_at, start, end)) or 0

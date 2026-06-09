from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.domain.enums import AgentRunStatus, ConversationState, MessageDirection, OrderPaymentStatus, OrderStatus
from app.domain.models import AdminAuditLog, AgentDecisionAudit, AgentRun, Conversation, ConversationSlots, Message, Order, Product, ShopMember, UnavailableDemandLog, User
from app.schemas.analytics import (
    AgentPerformanceMetrics,
    FunnelAnalytics,
    HandoffAnalyticsRow,
    LostDemandListResponse,
    LostDemandRow,
    OperatorPerformanceListResponse,
    OperatorPerformanceRow,
    PostPerformanceRow,
    PostRevenueRow,
    ResponseTimeAnalytics,
    StockDemandRow,
    UnavailableDemandRow,
)
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
        drafts = self._count_orders(
            shop_id,
            Order.status.in_(
                [
                    OrderStatus.DRAFT,
                    OrderStatus.WAITING_FOR_CLARIFICATION,
                    OrderStatus.READY_FOR_CONFIRMATION,
                    OrderStatus.RESERVED,
                    OrderStatus.PAYMENT_PENDING,
                    OrderStatus.PAID,
                ]
            ),
            start,
            end,
        )
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
            confirmed_orders=self._count_orders(shop_id, Order.status == OrderStatus.READY_FOR_CONFIRMATION, start, end),
            waiting_for_payment=self._count_orders(shop_id, Order.status == OrderStatus.PAYMENT_PENDING, start, end),
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
                OrderStatus.READY_FOR_CONFIRMATION,
                OrderStatus.PAYMENT_PENDING,
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
        return ResponseTimeAnalytics(
            average_first_response_time_seconds=self.funnel(shop_id, user, start, end).average_time_to_first_response_seconds,
            average_time_to_draft_order_seconds=None,
            average_time_to_payment_seconds=self.funnel(shop_id, user, start, end).average_time_to_payment_seconds,
        )

    def lost_demand(
        self,
        shop_id: UUID,
        user: User,
        start: datetime | None = None,
        end: datetime | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> LostDemandListResponse:
        self.shop_service.get_shop(shop_id, user)
        rows = self.db.execute(
            self._range(
                select(
                    UnavailableDemandLog.product_id,
                    UnavailableDemandLog.requested_color_normalized,
                    UnavailableDemandLog.requested_size_normalized,
                    UnavailableDemandLog.reason,
                    func.count(UnavailableDemandLog.id),
                    func.coalesce(func.sum(UnavailableDemandLog.estimated_lost_revenue), 0),
                )
                .where(UnavailableDemandLog.shop_id == shop_id)
                .group_by(
                    UnavailableDemandLog.product_id,
                    UnavailableDemandLog.requested_color_normalized,
                    UnavailableDemandLog.requested_size_normalized,
                    UnavailableDemandLog.reason,
                ),
                UnavailableDemandLog.created_at,
                start,
                end,
            )
        ).all()
        product_titles = {
            product.id: product.title
            for product in self.db.scalars(select(Product).where(Product.shop_id == shop_id)).all()
        }
        items = [
            LostDemandRow(
                requested_product=product_titles.get(product_id) if product_id else None,
                requested_color=color,
                requested_size=size,
                product_id=product_id,
                count=count,
                estimated_lost_revenue=lost,
                reason=reason,
            )
            for product_id, color, size, reason, count, lost in rows
        ]
        items.sort(key=lambda row: (row.count, row.estimated_lost_revenue), reverse=True)
        total = len(items)
        offset = (page - 1) * page_size
        return LostDemandListResponse(
            items=items[offset : offset + page_size],
            total=total,
            page=page,
            page_size=page_size,
        )

    def operator_performance(
        self,
        shop_id: UUID,
        user: User,
        start: datetime | None = None,
        end: datetime | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> OperatorPerformanceListResponse:
        self.shop_service.get_shop(shop_id, user)
        members = self.db.scalars(
            select(ShopMember).options(joinedload(ShopMember.user)).where(ShopMember.shop_id == shop_id)
        ).all()
        rows: list[OperatorPerformanceRow] = []
        for member in members:
            operator = member.user
            if operator is None:
                continue
            assigned = self._count_conversations(
                shop_id,
                start,
                end,
                Conversation.assigned_operator_id == operator.id,
            )
            resolved = self._count_conversations(
                shop_id,
                start,
                end,
                (Conversation.assigned_operator_id == operator.id)
                & (Conversation.state == ConversationState.CLOSED),
            )
            manual_messages = self.db.scalar(
                self._range(
                    select(func.count(AdminAuditLog.id)).where(
                        AdminAuditLog.shop_id == shop_id,
                        AdminAuditLog.user_id == operator.id,
                        AdminAuditLog.action == "manual_message_sent",
                    ),
                    AdminAuditLog.created_at,
                    start,
                    end,
                )
            ) or 0
            orders_closed = self.db.scalar(
                self._range(
                    select(func.count(Order.id))
                    .join(Conversation, Conversation.id == Order.conversation_id)
                    .where(
                        Order.shop_id == shop_id,
                        Order.payment_status == OrderPaymentStatus.PAID,
                        Conversation.assigned_operator_id == operator.id,
                    ),
                    Order.created_at,
                    start,
                    end,
                )
            ) or 0
            revenue = self.db.scalar(
                self._range(
                    select(func.coalesce(func.sum(Order.total_amount), 0))
                    .join(Conversation, Conversation.id == Order.conversation_id)
                    .where(
                        Order.shop_id == shop_id,
                        Order.payment_status == OrderPaymentStatus.PAID,
                        Conversation.assigned_operator_id == operator.id,
                    ),
                    Order.created_at,
                    start,
                    end,
                )
            ) or Decimal("0")
            rows.append(
                OperatorPerformanceRow(
                    operator_id=operator.id,
                    operator_name=operator.full_name,
                    assigned_conversations=assigned,
                    resolved_conversations=resolved,
                    average_response_time_seconds=None,
                    manual_messages_sent=manual_messages,
                    orders_closed=orders_closed,
                    revenue_assisted=Decimal(str(revenue)),
                )
            )
        rows.sort(key=lambda row: (row.revenue_assisted, row.resolved_conversations), reverse=True)
        total = len(rows)
        offset = (page - 1) * page_size
        return OperatorPerformanceListResponse(
            items=rows[offset : offset + page_size],
            total=total,
            page=page,
            page_size=page_size,
        )

    def agent_performance(
        self,
        shop_id: UUID,
        user: User,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> AgentPerformanceMetrics:
        self.shop_service.get_shop(shop_id, user)
        total_conversations = self._count_conversations(shop_id, start, end) or 1
        handoffs = self._count_conversations(shop_id, start, end, Conversation.handoff_required.is_(True))
        auto_sent = self.db.scalar(
            self._range(
                select(func.count(AdminAuditLog.id)).where(
                    AdminAuditLog.shop_id == shop_id,
                    AdminAuditLog.action == "message_auto_sent",
                ),
                AdminAuditLog.created_at,
                start,
                end,
            )
        ) or 0
        preview_required = self.db.scalar(
            self._range(
                select(func.count(Conversation.id)).where(
                    Conversation.shop_id == shop_id,
                    Conversation.preview_required.is_(True),
                    Conversation.is_simulation.is_(False),
                ),
                Conversation.created_at,
                start,
                end,
            )
        ) or 0
        failed_runs = self.db.scalar(
            self._range(
                select(func.count(AgentRun.id))
                .join(Conversation)
                .where(
                    Conversation.shop_id == shop_id,
                    AgentRun.status == AgentRunStatus.FAILED,
                    AgentRun.is_simulation.is_(False),
                ),
                AgentRun.created_at,
                start,
                end,
            )
        ) or 0
        invalid_outputs = self.db.scalar(
            self._range(
                select(func.count(AgentRun.id))
                .join(Conversation)
                .where(
                    Conversation.shop_id == shop_id,
                    AgentRun.status == AgentRunStatus.FAILED,
                    AgentRun.error_message.is_not(None),
                    AgentRun.is_simulation.is_(False),
                ),
                AgentRun.created_at,
                start,
                end,
            )
        ) or 0
        intent_confidences: list[float] = []
        product_confidences: list[float] = []
        variant_confidences: list[float] = []
        audits = self.db.scalars(
            self._range(
                select(AgentDecisionAudit).where(AgentDecisionAudit.shop_id == shop_id),
                AgentDecisionAudit.created_at,
                start,
                end,
            )
        ).all()
        for audit in audits:
            slots = audit.extracted_slots or {}
            confidence = slots.get("confidence") or {}
            if isinstance(confidence, dict):
                if confidence.get("intent") is not None:
                    intent_confidences.append(float(confidence["intent"]))
                if confidence.get("product") is not None:
                    product_confidences.append(float(confidence["product"]))
                if confidence.get("variant") is not None:
                    variant_confidences.append(float(confidence["variant"]))
        runs = self.db.scalars(
            self._range(
                select(AgentRun)
                .join(Conversation)
                .where(Conversation.shop_id == shop_id, AgentRun.is_simulation.is_(False)),
                AgentRun.created_at,
                start,
                end,
            )
        ).all()
        for run in runs:
            confidence = (run.output_json or {}).get("confidence") or {}
            if isinstance(confidence, dict):
                if confidence.get("intent") is not None:
                    intent_confidences.append(float(confidence["intent"]))
                if confidence.get("product") is not None:
                    product_confidences.append(float(confidence["product"]))
                if confidence.get("variant") is not None:
                    variant_confidences.append(float(confidence["variant"]))

        def _avg(values: list[float]) -> float | None:
            return round(sum(values) / len(values), 4) if values else None

        return AgentPerformanceMetrics(
            auto_sent_messages=auto_sent,
            preview_required_messages=preview_required,
            handoff_rate=self._rate(handoffs, total_conversations),
            failed_agent_runs=failed_runs,
            invalid_llm_outputs=invalid_outputs,
            average_intent_confidence=_avg(intent_confidences),
            average_product_confidence=_avg(product_confidences),
            average_variant_confidence=_avg(variant_confidences),
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

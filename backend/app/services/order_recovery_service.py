from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import (
    MessageDirection,
    OrderPaymentStatus,
    OrderRecoveryAttemptStatus,
    OrderRecoveryStatus,
    OrderStatus,
)
from app.domain.models import (
    AbandonedOrderRecoveryRule,
    Conversation,
    Message,
    Order,
    OrderRecoveryAttempt,
    User,
)
from app.schemas.recovery import RecoveryRuleCreate, RecoveryRuleRead, RecoveryRuleUpdate
from app.services.channel_outbound_service import ChannelOutboundService
from app.services.shop_service import ShopService

logger = logging.getLogger(__name__)

TERMINAL_RECOVERY_STATUSES = {
    OrderRecoveryStatus.RECOVERED,
    OrderRecoveryStatus.STOPPED,
    OrderRecoveryStatus.FAILED,
}

INSTAGRAM_MESSAGING_WINDOW_HOURS = 24


class OrderRecoveryService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.shop_service = ShopService(db)
        self.send_service = ChannelOutboundService(db, self.settings)

    def list_rules(self, shop_id: UUID, user: User) -> list[RecoveryRuleRead]:
        self.shop_service.get_shop(shop_id, user)
        rules = self.db.scalars(
            select(AbandonedOrderRecoveryRule)
            .where(AbandonedOrderRecoveryRule.shop_id == shop_id)
            .order_by(AbandonedOrderRecoveryRule.created_at.desc())
        ).all()
        return [RecoveryRuleRead.model_validate(rule) for rule in rules]

    def create_rule(self, shop_id: UUID, payload: RecoveryRuleCreate, user: User) -> RecoveryRuleRead:
        self.shop_service.get_shop(shop_id, user)
        rule = AbandonedOrderRecoveryRule(shop_id=shop_id, **payload.model_dump())
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return RecoveryRuleRead.model_validate(rule)

    def update_rule(
        self, shop_id: UUID, rule_id: UUID, payload: RecoveryRuleUpdate, user: User
    ) -> RecoveryRuleRead:
        rule = self._get_rule(shop_id, rule_id, user)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(rule, field, value)
        self.db.commit()
        self.db.refresh(rule)
        return RecoveryRuleRead.model_validate(rule)

    def delete_rule(self, shop_id: UUID, rule_id: UUID, user: User) -> None:
        rule = self._get_rule(shop_id, rule_id, user)
        self.db.delete(rule)
        self.db.commit()

    def stop_recovery(self, shop_id: UUID, order_id: UUID, user: User) -> Order:
        self.shop_service.get_shop(shop_id, user)
        order = self.db.scalar(
            select(Order).where(Order.id == order_id, Order.shop_id == shop_id)
        )
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        self._stop_recovery(order, OrderRecoveryStatus.STOPPED)
        self.db.commit()
        self.db.refresh(order)
        return order

    def process_recovery_cycle(self) -> dict[str, int]:
        """Scan waiting_for_payment orders, mark eligible, send recovery attempts."""
        now = datetime.now(UTC)
        stats = {"eligible": 0, "sent": 0, "skipped": 0, "failed": 0}

        orders = self.db.scalars(
            select(Order).where(
                Order.status == OrderStatus.PAYMENT_PENDING,
                Order.payment_status != OrderPaymentStatus.PAID,
                Order.recovery_status.not_in(TERMINAL_RECOVERY_STATUSES),
            )
        ).all()

        for order in orders:
            rule = self._active_rule(order.shop_id)
            if rule is None:
                continue

            if order.recovery_status == OrderRecoveryStatus.NONE:
                if self._should_mark_eligible(order, rule, now):
                    order.recovery_status = OrderRecoveryStatus.ELIGIBLE
                    stats["eligible"] += 1
                    logger.info("Order marked eligible for recovery order=%s", order.id)

            if order.recovery_status not in {
                OrderRecoveryStatus.ELIGIBLE,
                OrderRecoveryStatus.IN_PROGRESS,
            }:
                continue

            if order.recovery_attempt_count >= rule.max_attempts:
                order.recovery_status = OrderRecoveryStatus.FAILED
                continue

            if not self._cooldown_elapsed(order, rule, now):
                continue

            attempt = self._create_recovery_attempt(order, rule, now)
            if attempt.status == OrderRecoveryAttemptStatus.SENT:
                stats["sent"] += 1
            elif attempt.status == OrderRecoveryAttemptStatus.SKIPPED:
                stats["skipped"] += 1
            else:
                stats["failed"] += 1

        self.db.commit()
        return stats

    def on_order_paid(self, order: Order) -> None:
        if order.recovery_status in TERMINAL_RECOVERY_STATUSES:
            if order.recovery_status != OrderRecoveryStatus.RECOVERED:
                order.recovery_status = OrderRecoveryStatus.RECOVERED
            return
        if order.recovery_attempt_count > 0 or order.recovery_status != OrderRecoveryStatus.NONE:
            order.recovery_status = OrderRecoveryStatus.RECOVERED
        else:
            order.recovery_status = OrderRecoveryStatus.NONE

    def on_order_terminal(self, order: Order) -> None:
        if order.recovery_status in TERMINAL_RECOVERY_STATUSES:
            return
        order.recovery_status = OrderRecoveryStatus.STOPPED

    def _get_rule(self, shop_id: UUID, rule_id: UUID, user: User) -> AbandonedOrderRecoveryRule:
        self.shop_service.get_shop(shop_id, user)
        rule = self.db.scalar(
            select(AbandonedOrderRecoveryRule).where(
                AbandonedOrderRecoveryRule.id == rule_id,
                AbandonedOrderRecoveryRule.shop_id == shop_id,
            )
        )
        if rule is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery rule not found")
        return rule

    def _active_rule(self, shop_id: UUID) -> AbandonedOrderRecoveryRule | None:
        return self.db.scalar(
            select(AbandonedOrderRecoveryRule)
            .where(
                AbandonedOrderRecoveryRule.shop_id == shop_id,
                AbandonedOrderRecoveryRule.is_active.is_(True),
            )
            .order_by(AbandonedOrderRecoveryRule.created_at.desc())
            .limit(1)
        )

    def _payment_waiting_since(self, order: Order) -> datetime:
        if order.expires_at is not None:
            return order.expires_at - timedelta(minutes=self.settings.order_expiration_minutes)
        return order.updated_at

    def _should_mark_eligible(
        self, order: Order, rule: AbandonedOrderRecoveryRule, now: datetime
    ) -> bool:
        waiting_since = self._payment_waiting_since(order)
        return now >= waiting_since + timedelta(minutes=rule.trigger_after_minutes)

    def _cooldown_elapsed(
        self, order: Order, rule: AbandonedOrderRecoveryRule, now: datetime
    ) -> bool:
        if order.last_recovery_at is None:
            return True
        return now >= order.last_recovery_at + timedelta(minutes=rule.trigger_after_minutes)

    def _inside_messaging_window(self, conversation_id: UUID, now: datetime) -> bool:
        last_inbound = self.db.scalar(
            select(Message.created_at)
            .where(
                Message.conversation_id == conversation_id,
                Message.direction == MessageDirection.INBOUND,
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        if last_inbound is None:
            return False
        return now <= last_inbound + timedelta(hours=INSTAGRAM_MESSAGING_WINDOW_HOURS)

    def _render_template(self, template: str, order: Order) -> str:
        customer_name = order.customer_name or "there"
        return (
            template.replace("{customer_name}", customer_name)
            .replace("{order_total}", str(order.total_amount))
            .replace("{currency}", order.currency)
            .replace("{order_id}", str(order.id)[:8])
        )

    def _create_recovery_attempt(
        self, order: Order, rule: AbandonedOrderRecoveryRule, now: datetime
    ) -> OrderRecoveryAttempt:
        message_text = self._render_template(rule.message_template, order)
        attempt = OrderRecoveryAttempt(
            order_id=order.id,
            conversation_id=order.conversation_id,
            message_text=message_text,
            status=OrderRecoveryAttemptStatus.CREATED,
        )
        self.db.add(attempt)
        order.recovery_status = OrderRecoveryStatus.IN_PROGRESS

        if rule.only_inside_allowed_messaging_window and not self._inside_messaging_window(
            order.conversation_id, now
        ):
            attempt.status = OrderRecoveryAttemptStatus.SKIPPED
            attempt.skip_reason = "outside_messaging_window"
            order.recovery_attempt_count += 1
            order.last_recovery_at = now
            logger.info(
                "Recovery skipped (messaging window) order=%s attempt=%s",
                order.id,
                attempt.id,
            )
            return attempt

        conversation = self.db.get(Conversation, order.conversation_id)
        if conversation and (conversation.agent_paused or conversation.assigned_operator_id):
            attempt.status = OrderRecoveryAttemptStatus.SKIPPED
            attempt.skip_reason = "human_control"
            order.recovery_attempt_count += 1
            order.last_recovery_at = now
            return attempt

        try:
            self.send_service.send_text_message(order.conversation_id, message_text, commit=False)
            attempt.status = OrderRecoveryAttemptStatus.SENT
            order.recovery_attempt_count += 1
            order.last_recovery_at = now
            logger.info("Recovery message sent order=%s attempt=%s", order.id, attempt.id)
        except Exception as exc:
            attempt.status = OrderRecoveryAttemptStatus.FAILED
            attempt.error_message = str(exc)
            order.recovery_attempt_count += 1
            order.last_recovery_at = now
            logger.warning("Recovery send failed order=%s: %s", order.id, exc)

        if order.recovery_attempt_count >= rule.max_attempts and order.payment_status != OrderPaymentStatus.PAID:
            if order.status == OrderStatus.PAYMENT_PENDING:
                order.recovery_status = OrderRecoveryStatus.FAILED

        return attempt

    def _stop_recovery(self, order: Order, status: OrderRecoveryStatus) -> None:
        order.recovery_status = status

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from statistics import mean
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.health import build_readiness_payload
from app.domain.enums import (
    AgentActionStatus,
    AgentRunStatus,
    ConversationState,
    FailedJobStatus,
    InstagramAccountStatus,
    MessageDirection,
    OrderPaymentStatus,
    OrderStatus,
    PilotEventSeverity,
    ProductStatus,
    UserRole,
)
from app.domain.models import (
    AdminAuditLog,
    AgentAction,
    AgentRun,
    Conversation,
    FailedJob,
    InstagramAccount,
    InstagramProductMap,
    InventoryMovement,
    Message,
    Order,
    PilotEvent,
    PilotSettings,
    Product,
    ProductVariant,
    ShopAgentSettings,
    ShopMember,
    SuggestedReply,
    TRLValidationRun,
)
from app.schemas.pilot import (
    PilotChecklistItem,
    PilotEventRead,
    PilotMetricsRead,
    PilotReadinessCriterion,
    PilotReadinessResponse,
    PilotSettingsRead,
    PilotSettingsUpdate,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _start_of_day() -> datetime:
    current = _now()
    return current.replace(hour=0, minute=0, second=0, microsecond=0)


def _uuid_strings(values: list[UUID] | None) -> list[str] | None:
    return None if values is None else [str(value) for value in values]


class PilotService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create_settings(self, shop_id: UUID) -> PilotSettings:
        settings = self.db.get(PilotSettings, shop_id)
        if settings is None:
            settings = PilotSettings(shop_id=shop_id, pilot_name="Pilot", allowed_instagram_account_ids=[])
            self.db.add(settings)
            self.db.flush()
        return settings

    def update_settings(self, shop_id: UUID, payload: PilotSettingsUpdate, *, user_id: UUID | None = None) -> PilotSettings:
        settings = self.get_or_create_settings(shop_id)
        before_enabled = settings.pilot_enabled
        updates = payload.model_dump(exclude_unset=True)
        for key, value in updates.items():
            if key in {"allowed_instagram_account_ids", "allowed_product_ids"}:
                value = _uuid_strings(value)
            setattr(settings, key, value)
        settings.updated_at = _now()
        if settings.pilot_enabled and not before_enabled:
            self.log_event(shop_id, "pilot_enabled", PilotEventSeverity.INFO, "Pilot mode enabled", user_id=user_id)
        elif before_enabled and not settings.pilot_enabled:
            self.log_event(shop_id, "pilot_disabled", PilotEventSeverity.WARNING, "Pilot mode disabled", user_id=user_id)
        self.db.commit()
        self.db.refresh(settings)
        return settings

    def set_emergency_stop(
        self,
        shop_id: UUID,
        enabled: bool,
        *,
        user_id: UUID | None = None,
        reason: str | None = None,
        open_incident: bool = True,
    ) -> tuple[PilotSettings, PilotEvent, dict]:
        settings = self.get_or_create_settings(shop_id)
        scope_preview = self.build_emergency_stop_scope_preview(shop_id)
        settings.emergency_stop_enabled = enabled
        settings.updated_at = _now()
        metadata = {
            "reason": reason,
            "scope_preview": scope_preview,
        }
        event = self.log_event(
            shop_id,
            "emergency_stop" if enabled else "resume",
            PilotEventSeverity.CRITICAL if enabled else PilotEventSeverity.INFO,
            "Emergency stop activated" if enabled else "Pilot automation resumed",
            description=reason or (
                "Auto-send and auto-order progression are blocked immediately."
                if enabled
                else "Automation restored subject to pilot limits and approvals."
            ),
            metadata=metadata,
            user_id=user_id,
            commit=False,
        )
        incident_id = None
        if enabled and open_incident:
            from app.services.incident_service import IncidentService

            incident = IncidentService(self.db).open_from_emergency_stop(
                shop_id,
                user_id=user_id,
                scope_preview=scope_preview,
                reason=reason,
            )
            incident_id = incident.id
            metadata["incident_id"] = str(incident_id)
        self.db.commit()
        self.db.refresh(settings)
        self.db.refresh(event)
        scope_preview["incident_id"] = str(incident_id) if incident_id else None
        return settings, event, scope_preview

    def build_emergency_stop_scope_preview(self, shop_id: UUID) -> dict:
        active_conversations = list(
            self.db.scalars(
                select(Conversation.id).where(
                    Conversation.shop_id == shop_id,
                    Conversation.is_simulation.is_(False),
                    Conversation.state.in_([ConversationState.OPEN, ConversationState.PENDING_HANDOFF]),
                )
            ).all()
        )
        simulation_conversations = list(
            self.db.scalars(
                select(Conversation.id).where(
                    Conversation.shop_id == shop_id,
                    Conversation.is_simulation.is_(True),
                )
            ).all()
        )
        return {
            "active_conversation_count": len(active_conversations),
            "simulation_conversation_count": len(simulation_conversations),
            "affected_conversation_ids": [str(conversation_id) for conversation_id in active_conversations[:50]],
        }

    def is_emergency_stop_active(self, shop_id: UUID) -> bool:
        settings = self.get_or_create_settings(shop_id)
        return bool(settings.emergency_stop_enabled)

    def log_event(
        self,
        shop_id: UUID,
        event_type: str,
        severity: PilotEventSeverity,
        title: str,
        *,
        description: str | None = None,
        metadata: dict | None = None,
        user_id: UUID | None = None,
        commit: bool = False,
    ) -> PilotEvent:
        event = PilotEvent(
            shop_id=shop_id,
            event_type=event_type,
            severity=severity,
            title=title,
            description=description,
            event_metadata=metadata,
        )
        self.db.add(event)
        self.db.add(AdminAuditLog(shop_id=shop_id, user_id=user_id, action=event_type, entity_type="pilot", details=metadata or {}))
        if commit:
            self.db.commit()
            self.db.refresh(event)
        else:
            self.db.flush()
        return event

    def list_events(self, shop_id: UUID, limit: int = 50) -> list[PilotEvent]:
        return list(
            self.db.scalars(
                select(PilotEvent).where(PilotEvent.shop_id == shop_id).order_by(PilotEvent.created_at.desc()).limit(limit)
            )
        )

    def enforce_auto_send_allowed(self, shop_id: UUID, instagram_account_id: UUID | None = None) -> tuple[bool, list[str]]:
        settings = self.get_or_create_settings(shop_id)
        reasons: list[str] = []
        if not settings.pilot_enabled:
            return True, reasons
        if settings.emergency_stop_enabled:
            reasons.append("pilot_emergency_stop_enabled")
        if settings.allowed_instagram_account_ids and instagram_account_id is not None and str(instagram_account_id) not in settings.allowed_instagram_account_ids:
            reasons.append("instagram_account_not_in_pilot")
        sent_today = self._auto_sent_today(shop_id)
        if sent_today >= settings.max_auto_sent_messages_per_day:
            reasons.append("pilot_auto_send_limit_reached")
            self.log_event(shop_id, "auto_send_limit_reached", PilotEventSeverity.WARNING, "Pilot auto-send daily limit reached", metadata={"limit": settings.max_auto_sent_messages_per_day, "sent_today": sent_today}, commit=True)
        return not reasons, reasons

    def enforce_order_allowed(self, shop_id: UUID, product_id: UUID | None = None) -> tuple[bool, list[str]]:
        settings = self.get_or_create_settings(shop_id)
        reasons: list[str] = []
        if not settings.pilot_enabled:
            return True, reasons
        if settings.emergency_stop_enabled:
            reasons.append("pilot_emergency_stop_enabled")
        if settings.allowed_product_ids is not None and product_id is not None and str(product_id) not in settings.allowed_product_ids:
            reasons.append("product_not_in_pilot")
        orders_today = self._auto_orders_today(shop_id)
        if orders_today >= settings.max_auto_created_orders_per_day:
            reasons.append("pilot_auto_order_limit_reached")
            self.log_event(shop_id, "auto_order_limit_reached", PilotEventSeverity.WARNING, "Pilot auto-order daily limit reached", metadata={"limit": settings.max_auto_created_orders_per_day, "orders_today": orders_today}, commit=True)
        if settings.require_operator_approval_for_first_50_orders and self._pilot_order_count(shop_id) < 50:
            reasons.append("first_50_orders_require_operator_approval")
        return not reasons, reasons

    def _auto_sent_today(self, shop_id: UUID) -> int:
        return int(self.db.scalar(select(func.count(AdminAuditLog.id)).where(AdminAuditLog.shop_id == shop_id, AdminAuditLog.action == "message_auto_sent", AdminAuditLog.created_at >= _start_of_day())) or 0)

    def _auto_orders_today(self, shop_id: UUID) -> int:
        return int(self.db.scalar(select(func.count(AdminAuditLog.id)).where(AdminAuditLog.shop_id == shop_id, AdminAuditLog.action == "pilot_auto_order_created", AdminAuditLog.created_at >= _start_of_day())) or 0)

    def _pilot_order_count(self, shop_id: UUID) -> int:
        return int(self.db.scalar(select(func.count(Order.id)).where(Order.shop_id == shop_id, Order.is_simulation.is_(False))) or 0)

    def metrics(self, shop_id: UUID) -> PilotMetricsRead:
        inbound = self._count_messages(shop_id, MessageDirection.INBOUND)
        outbound = self._count_audit(shop_id, "message_auto_sent")
        previewed = self._count_audit_like(shop_id, ["message_blocked_due_to_confidence", "suggested_reply_created"])
        handoff = int(self.db.scalar(select(func.count(Conversation.id)).where(Conversation.shop_id == shop_id, Conversation.handoff_required.is_(True))) or 0)
        failed_jobs = int(self.db.scalar(select(func.count(FailedJob.id)).where(FailedJob.shop_id == shop_id, FailedJob.status == FailedJobStatus.FAILED, FailedJob.resolved.is_(False))) or 0)
        invalid_llm = int(self.db.scalar(select(func.count(AgentRun.id)).join(Conversation).where(Conversation.shop_id == shop_id, AgentRun.status == AgentRunStatus.FAILED)) or 0)
        durations = [int(x or 0) for x in self.db.scalars(select(AgentAction.output_json["processing_time_ms"].as_integer()).join(Conversation).where(Conversation.shop_id == shop_id)).all() if x is not None]
        p95 = 0.0
        if durations:
            durations_sorted = sorted(durations)
            p95 = float(durations_sorted[min(len(durations_sorted) - 1, int(len(durations_sorted) * 0.95))])
        return PilotMetricsRead(
            inbound_messages=inbound,
            auto_sent_messages=outbound,
            previewed_messages=previewed,
            human_handoff_count=handoff,
            draft_orders=self._count_orders(shop_id, OrderStatus.DRAFT),
            confirmed_orders=self._count_orders(shop_id, OrderStatus.READY_FOR_CONFIRMATION)
            + self._count_orders(shop_id, OrderStatus.PAYMENT_PENDING),
            paid_orders=int(self.db.scalar(select(func.count(Order.id)).where(Order.shop_id == shop_id, Order.payment_status == OrderPaymentStatus.PAID)) or 0),
            cancelled_orders=self._count_orders(shop_id, OrderStatus.CANCELLED),
            failed_jobs=failed_jobs,
            invalid_llm_outputs=invalid_llm,
            average_response_time_ms=float(mean(durations)) if durations else 0.0,
            p95_response_time_ms=p95,
            operator_takeover_count=self._count_audit(shop_id, "conversation_take_over"),
        )

    def _count_messages(self, shop_id: UUID, direction: MessageDirection) -> int:
        return int(self.db.scalar(select(func.count(Message.id)).join(Conversation).where(Conversation.shop_id == shop_id, Message.direction == direction)) or 0)

    def _count_orders(self, shop_id: UUID, status_: OrderStatus) -> int:
        return int(self.db.scalar(select(func.count(Order.id)).where(Order.shop_id == shop_id, Order.status == status_)) or 0)

    def _count_audit(self, shop_id: UUID, action: str) -> int:
        return int(self.db.scalar(select(func.count(AdminAuditLog.id)).where(AdminAuditLog.shop_id == shop_id, AdminAuditLog.action == action)) or 0)

    def _count_audit_like(self, shop_id: UUID, actions: list[str]) -> int:
        return int(self.db.scalar(select(func.count(AdminAuditLog.id)).where(AdminAuditLog.shop_id == shop_id, AdminAuditLog.action.in_(actions))) or 0)

    def readiness(self, shop_id: UUID, *, product_mapping_threshold: float = 0.8) -> PilotReadinessResponse:
        settings = self.get_or_create_settings(shop_id)
        latest = self.db.scalar(select(TRLValidationRun).where(TRLValidationRun.shop_id == shop_id).order_by(TRLValidationRun.started_at.desc()))
        readiness_status, _checks, all_ready = build_readiness_payload()
        criteria = self._criteria(shop_id, latest, readiness_status, all_ready, product_mapping_threshold)
        checklist = self._checklist(shop_id, latest)
        warnings = [item.label for item in checklist if not item.passed] + [criterion.label for criterion in criteria if not criterion.passed]
        return PilotReadinessResponse(
            shop_id=shop_id,
            ready_for_trl6_pilot=all(item.passed for item in criteria),
            checklist=checklist,
            criteria=criteria,
            latest_trl_validation=self._trl_summary(latest),
            pilot_settings=self.to_settings_read(settings),
            warnings=warnings,
        )

    def _criteria(self, shop_id: UUID, latest: TRLValidationRun | None, readiness_status: str, all_ready: bool, threshold: float) -> list[PilotReadinessCriterion]:
        failed_critical = int(self.db.scalar(select(func.count(FailedJob.id)).where(FailedJob.shop_id == shop_id, FailedJob.status == FailedJobStatus.FAILED, FailedJob.resolved.is_(False), FailedJob.retry_count >= FailedJob.max_retries)) or 0)
        operator_assigned = self.db.scalar(select(ShopMember.id).where(ShopMember.shop_id == shop_id, ShopMember.role.in_([UserRole.OWNER, UserRole.ADMIN, UserRole.OPERATOR])).limit(1)) is not None
        agent_settings = self.db.get(ShopAgentSettings, shop_id)
        handoff_policy = bool(agent_settings and agent_settings.handoff_policy_json)
        emergency_tested = self.db.scalar(select(PilotEvent.id).where(PilotEvent.shop_id == shop_id, PilotEvent.event_type == "emergency_stop").limit(1)) is not None
        coverage = self._product_mapping_coverage(shop_id)
        inventory_verified = self.db.scalar(select(InventoryMovement.id).join(ProductVariant).join(Product).where(Product.shop_id == shop_id, InventoryMovement.created_at >= _now() - timedelta(hours=24)).limit(1)) is not None
        payment_mode = bool(agent_settings and (agent_settings.risk_policy_json or agent_settings.discount_policy_json is not None))
        audit_logging = self.db.scalar(select(AdminAuditLog.id).where(AdminAuditLog.shop_id == shop_id).limit(1)) is not None
        latest_metrics = (latest.metrics_json or {}) if latest else {}
        thresholds_passed = latest_metrics.get("thresholds_passed") or {}
        latest_ok = bool(latest and latest.status == "passed" and thresholds_passed)
        thresholds_ok = latest_ok and all(bool(v) for v in thresholds_passed.values())
        return [
            PilotReadinessCriterion(key="latest_trl_validation", label="Latest TRL validation run passed thresholds", passed=thresholds_ok, detail=latest.status if latest else "No run"),
            PilotReadinessCriterion(key="no_critical_failed_jobs", label="No critical failed jobs", passed=failed_critical == 0, detail=f"{failed_critical} critical failed jobs"),
            PilotReadinessCriterion(key="ready_endpoint", label="/ready is ok", passed=all_ready and readiness_status == "ok", detail=readiness_status),
            PilotReadinessCriterion(key="operator_assigned", label="Operator assigned", passed=operator_assigned),
            PilotReadinessCriterion(key="handoff_policy_configured", label="Handoff policy configured", passed=handoff_policy),
            PilotReadinessCriterion(key="emergency_stop_tested", label="Emergency stop tested", passed=emergency_tested),
            PilotReadinessCriterion(key="product_mapping_coverage", label="Product mapping coverage above threshold", passed=coverage >= threshold, detail=f"{coverage:.0%} / {threshold:.0%}"),
            PilotReadinessCriterion(key="inventory_verified", label="Inventory verified within last 24 hours", passed=inventory_verified),
            PilotReadinessCriterion(key="payment_mode_configured", label="Payment mode configured", passed=payment_mode),
            PilotReadinessCriterion(key="audit_logging_enabled", label="Audit logging enabled", passed=audit_logging),
        ]

    def _checklist(self, shop_id: UUID, latest: TRLValidationRun | None) -> list[PilotChecklistItem]:
        account_connected = self.db.scalar(select(InstagramAccount.id).where(InstagramAccount.shop_id == shop_id, InstagramAccount.status == InstagramAccountStatus.CONNECTED).limit(1)) is not None
        active_products = int(self.db.scalar(select(func.count(Product.id)).where(Product.shop_id == shop_id, Product.status == ProductStatus.ACTIVE)) or 0)
        active_variants = int(self.db.scalar(select(func.count(ProductVariant.id)).join(Product).where(Product.shop_id == shop_id, ProductVariant.is_active.is_(True))) or 0)
        agent_settings = self.db.get(ShopAgentSettings, shop_id)
        return [
            PilotChecklistItem(key="instagram_webhook_connected", label="Instagram webhook connected", passed=account_connected),
            PilotChecklistItem(key="latest_trl_validation_passed", label="Latest TRL validation passed", passed=bool(latest and latest.status == "passed")),
            PilotChecklistItem(key="demo_data_removed_or_isolated", label="Demo data removed or isolated", passed=True, detail="Simulation rows are marked with is_simulation."),
            PilotChecklistItem(key="real_products_configured", label="Real products configured", passed=active_products > 0, detail=f"{active_products} active products"),
            PilotChecklistItem(key="real_variants_configured", label="Real variants configured", passed=active_variants > 0, detail=f"{active_variants} active variants"),
            PilotChecklistItem(key="inventory_verified", label="Inventory verified", passed=self._criteria(shop_id, latest, "", False, 0)[7].passed),
            PilotChecklistItem(key="payment_mode_configured", label="Payment mode configured", passed=bool(agent_settings)),
            PilotChecklistItem(key="operator_assigned", label="Operator assigned", passed=self.db.scalar(select(ShopMember.id).where(ShopMember.shop_id == shop_id).limit(1)) is not None),
            PilotChecklistItem(key="handoff_policy_configured", label="Handoff policy configured", passed=bool(agent_settings and agent_settings.handoff_policy_json)),
            PilotChecklistItem(key="emergency_stop_tested", label="Emergency stop tested", passed=self.db.scalar(select(PilotEvent.id).where(PilotEvent.shop_id == shop_id, PilotEvent.event_type == "emergency_stop").limit(1)) is not None),
            PilotChecklistItem(key="support_contact_configured", label="Support contact configured", passed=bool(agent_settings and (agent_settings.risk_policy_json or {}).get("support_contact"))),
        ]

    def _product_mapping_coverage(self, shop_id: UUID) -> float:
        active_products = int(self.db.scalar(select(func.count(Product.id)).where(Product.shop_id == shop_id, Product.status == ProductStatus.ACTIVE)) or 0)
        if active_products == 0:
            return 0.0
        mapped = int(self.db.scalar(select(func.count(func.distinct(InstagramProductMap.product_id))).where(InstagramProductMap.shop_id == shop_id)) or 0)
        return mapped / active_products

    def _trl_summary(self, run: TRLValidationRun | None) -> dict | None:
        if run is None:
            return None
        return {"id": str(run.id), "status": run.status, "total_scenarios": run.total_scenarios, "passed_scenarios": run.passed_scenarios, "failed_scenarios": run.failed_scenarios, "started_at": run.started_at.isoformat(), "completed_at": run.completed_at.isoformat() if run.completed_at else None, "metrics_json": run.metrics_json}

    @staticmethod
    def to_settings_read(settings: PilotSettings) -> PilotSettingsRead:
        return PilotSettingsRead.model_validate(settings)

    @staticmethod
    def to_event_read(event: PilotEvent) -> PilotEventRead:
        return PilotEventRead(id=event.id, shop_id=event.shop_id, event_type=event.event_type, severity=event.severity.value, title=event.title, description=event.description, metadata=event.event_metadata, created_at=event.created_at)

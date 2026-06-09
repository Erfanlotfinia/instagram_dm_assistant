from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.domain.enums import (
    MessageChannel,
    MessageDirection,
    MessageType,
    SimulatorRunSourceType,
    SimulatorRunStatus,
    TraceEventType,
)
from app.domain.models import (
    AgentDecisionTrace,
    Conversation,
    Customer,
    InstagramAccount,
    Message,
    Order,
    PolicyVersion,
    Product,
    ProductVariant,
    SimulatorRun,
    SimulatorRunItem,
    User,
)
from app.schemas.replay import ReplayRunRequest, ReplayScenarioInput
from app.services.conversation_orchestrator import ConversationOrchestrator
from app.services.decision_trace_service import DecisionTraceService
from app.services.policy_engine import PolicyEngine, PolicyEvaluationContext, merge_policy_config
from app.services.slot_merge_service import slots_to_dict
from app.services.trl_validation_runner import DeterministicSemanticSearch, RuleBasedTRLExtractionService


class ReplayEngine:
    def __init__(self, db: Session, *, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.policy_engine = PolicyEngine()
        self.trace_service = DecisionTraceService(db)

    def run(self, shop_id: UUID, payload: ReplayRunRequest, user: User | None = None) -> SimulatorRun:
        account = self.db.scalar(select(InstagramAccount).where(InstagramAccount.shop_id == shop_id).limit(1))
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instagram account not found")

        policy_version = self._resolve_policy_version(shop_id, payload.policy_version_id)
        catalog_snapshot = self._freeze_catalog_snapshot(shop_id)
        model_version = payload.model_version or self.settings.default_model_version
        prompt_version = payload.prompt_version or self.settings.default_prompt_version

        run = SimulatorRun(
            shop_id=shop_id,
            created_by_user_id=user.id if user else None,
            label=payload.label or f"Replay {datetime.now(UTC).isoformat()}",
            source_type=SimulatorRunSourceType.MANUAL,
            model_version=model_version,
            prompt_version=prompt_version,
            policy_version_id=policy_version.id if policy_version else None,
            catalog_snapshot_hash=catalog_snapshot["hash"],
            catalog_snapshot_json=catalog_snapshot["payload"],
            status=SimulatorRunStatus.RUNNING,
            total_items=len(payload.scenarios),
        )
        self.db.add(run)
        self.db.flush()

        passed = 0
        failed = 0
        try:
            for scenario in payload.scenarios:
                item = self._replay_one(
                    shop_id=shop_id,
                    run=run,
                    account_id=account.id,
                    scenario=scenario,
                    policy_config=policy_version.config_json if policy_version else merge_policy_config(None),
                    model_version=model_version,
                    prompt_version=prompt_version,
                )
                if item.passed:
                    passed += 1
                else:
                    failed += 1
            run.status = SimulatorRunStatus.COMPLETED
            run.passed_items = passed
            run.failed_items = failed
            run.diff_summary_json = {
                "pass_rate": passed / max(len(payload.scenarios), 1),
                "passed": passed,
                "failed": failed,
                "campaign": payload.campaign,
            }
            run.completed_at = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(run)
            return run
        except Exception as exc:
            run.status = SimulatorRunStatus.FAILED
            run.diff_summary_json = {"error": str(exc)}
            run.completed_at = datetime.now(UTC)
            self.db.commit()
            raise

    def list_runs(self, shop_id: UUID, *, limit: int = 50) -> list[SimulatorRun]:
        return list(
            self.db.scalars(
                select(SimulatorRun)
                .where(SimulatorRun.shop_id == shop_id)
                .order_by(SimulatorRun.started_at.desc())
                .limit(limit)
            ).all()
        )

    def get_run(self, shop_id: UUID, run_id: UUID) -> SimulatorRun | None:
        return self.db.scalar(
            select(SimulatorRun).where(SimulatorRun.id == run_id, SimulatorRun.shop_id == shop_id)
        )

    def _resolve_policy_version(self, shop_id: UUID, policy_version_id: UUID | None) -> PolicyVersion | None:
        if policy_version_id is not None:
            policy = self.db.scalar(
                select(PolicyVersion).where(
                    PolicyVersion.id == policy_version_id,
                    PolicyVersion.shop_id == shop_id,
                )
            )
            if policy is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy version not found")
            return policy
        return self.db.scalar(
            select(PolicyVersion)
            .where(PolicyVersion.shop_id == shop_id, PolicyVersion.is_active.is_(True))
            .order_by(PolicyVersion.created_at.desc())
            .limit(1)
        )

    def _freeze_catalog_snapshot(self, shop_id: UUID) -> dict[str, Any]:
        products = list(
            self.db.scalars(select(Product).where(Product.shop_id == shop_id).order_by(Product.id.asc())).all()
        )
        payload: dict[str, Any] = {"products": []}
        for product in products:
            variants = list(
                self.db.scalars(
                    select(ProductVariant).where(ProductVariant.product_id == product.id).order_by(ProductVariant.id.asc())
                ).all()
            )
            payload["products"].append(
                {
                    "id": str(product.id),
                    "title": product.title,
                    "status": product.status.value,
                    "base_price": str(product.base_price),
                    "variants": [
                        {
                            "id": str(variant.id),
                            "color": variant.color,
                            "size": variant.size,
                            "price": str(variant.price),
                            "stock_quantity": variant.stock_quantity,
                            "reserved_quantity": variant.reserved_quantity,
                        }
                        for variant in variants
                    ],
                }
            )
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return {"hash": digest, "payload": payload}

    def _replay_one(
        self,
        *,
        shop_id: UUID,
        run: SimulatorRun,
        account_id: UUID,
        scenario: ReplayScenarioInput,
        policy_config: dict[str, Any],
        model_version: str,
        prompt_version: str,
    ) -> SimulatorRunItem:
        trace_id = self.trace_service.new_trace_id()
        self.trace_service.bind_trace_context(trace_id)

        customer_key = f"replay:{run.id}:{scenario.item_key}"
        customer = self.db.scalar(
            select(Customer).where(Customer.shop_id == shop_id, Customer.instagram_user_id == customer_key)
        )
        if customer is None:
            customer = Customer(shop_id=shop_id, instagram_user_id=customer_key, full_name="Replay Customer")
            self.db.add(customer)
            self.db.flush()

        conversation = Conversation(
            shop_id=shop_id,
            instagram_account_id=account_id,
            customer_id=customer.id,
            channel_provider="instagram",
            channel_conversation_id=f"replay:{run.id}:{scenario.item_key}",
            channel_customer_id=customer.instagram_user_id,
            is_simulation=True,
        )
        self.db.add(conversation)
        self.db.flush()

        message = Message(
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
            channel=MessageChannel.INSTAGRAM,
            instagram_message_id=f"replay:{run.id}:{scenario.item_key}",
            message_type=MessageType.SHARED_POST if scenario.shared_post_url else MessageType.TEXT,
            text=scenario.message_text,
            raw_payload={"_meta": {"shared_post_url": scenario.shared_post_url, "replay": True}},
            is_simulation=True,
        )
        self.db.add(message)
        self.db.commit()

        llm = RuleBasedTRLExtractionService()
        llm.model_name = model_version
        llm.prompt_version = prompt_version
        orchestrator = ConversationOrchestrator(
            self.db,
            llm_service=llm,
            semantic_search=DeterministicSemanticSearch(self.db),
            allow_simulated_order_side_effects=True,
            settings=self.settings,
        )

        started = time.perf_counter()
        orchestrator.process_inbound_message(conversation.id, message.id)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        self.db.refresh(conversation)
        order = self.db.scalar(
            select(Order).where(Order.conversation_id == conversation.id).order_by(Order.created_at.desc()).limit(1)
        )
        trace_row = self.db.scalar(
            select(AgentDecisionTrace)
            .where(AgentDecisionTrace.message_id == message.id)
            .order_by(AgentDecisionTrace.created_at.desc())
            .limit(1)
        )
        slots = conversation.slots
        risk = trace_row.risk_score if trace_row else {}
        actual = {
            "intent": conversation.last_intent,
            "state": conversation.workflow_state.value if conversation.workflow_state else None,
            "requires_handoff": conversation.handoff_required,
            "order_created": order is not None,
            "product_resolved": bool(slots and slots.product_id),
            "variant_resolved": bool(slots and slots.product_variant_id),
            "auto_sent": self.db.query(Message).filter_by(
                conversation_id=conversation.id, direction=MessageDirection.OUTBOUND
            ).count()
            > 0,
            "confidence": {
                "intent": float(risk.get("intent_confidence", 0) or 0),
                "product": float(risk.get("product_confidence", 0) or 0),
                "variant": float(risk.get("variant_confidence", 0) or 0),
            },
            "risk_score": risk,
            "suggested_reply": conversation.suggested_outbound,
        }

        policy_eval = self.policy_engine.evaluate(
            PolicyEvaluationContext(
                shop_id=shop_id,
                intent_confidence=actual["confidence"]["intent"] or 0.9,
                product_confidence=actual["confidence"]["product"] or 0.9,
                variant_confidence=actual["confidence"]["variant"] or 0.9,
                handoff_required=conversation.handoff_required,
                stock_reserved=bool(slots and slots.product_variant_id),
                requires_write=bool(order),
            ),
            policy_config,
        )
        actual["policy_evaluation"] = {
            "allowed": policy_eval.allowed,
            "checks": [check.__dict__ for check in policy_eval.checks],
            "blocked_actions": policy_eval.blocked_actions,
        }

        self.trace_service.record(
            trace_id=trace_id,
            shop_id=shop_id,
            event_type=TraceEventType.RETRIEVAL_EVIDENCE,
            payload={"product_resolved": actual["product_resolved"], "variant_resolved": actual["variant_resolved"]},
            conversation_id=conversation.id,
        )
        self.trace_service.record(
            trace_id=trace_id,
            shop_id=shop_id,
            event_type=TraceEventType.SLOTS_EXTRACTED,
            payload={"slots": slots_to_dict(slots) if slots else {}},
            conversation_id=conversation.id,
        )
        self.trace_service.record(
            trace_id=trace_id,
            shop_id=shop_id,
            event_type=TraceEventType.CONFIDENCE_BAND,
            payload={
                "intent_band": self.policy_engine.confidence_band(actual["confidence"]["intent"] or 0),
                "scores": actual["confidence"],
            },
            conversation_id=conversation.id,
        )
        self.trace_service.record_policy_checks(
            trace_id=trace_id,
            shop_id=shop_id,
            checks=[check.__dict__ for check in policy_eval.checks],
            conversation_id=conversation.id,
        )
        if policy_eval.allowed:
            self.trace_service.record(
                trace_id=trace_id,
                shop_id=shop_id,
                event_type=TraceEventType.ACTION_ATTEMPTED,
                payload={"actions": ["process_inbound_message"]},
                conversation_id=conversation.id,
            )
        else:
            self.trace_service.record(
                trace_id=trace_id,
                shop_id=shop_id,
                event_type=TraceEventType.ACTION_BLOCKED,
                payload={"blocked_actions": policy_eval.blocked_actions},
                conversation_id=conversation.id,
            )

        diff = self._compute_diff(scenario.expected_json, actual)
        passed = not diff.get("mismatches")

        item = SimulatorRunItem(
            run_id=run.id,
            item_key=scenario.item_key,
            input_json={
                "message_text": scenario.message_text,
                "shared_post_url": scenario.shared_post_url,
                "instagram_user_id": scenario.instagram_user_id,
            },
            expected_json=scenario.expected_json,
            actual_json=actual,
            diff_json=diff,
            passed=passed,
            trace_id=trace_id,
            conversation_id=conversation.id,
            processing_time_ms=elapsed_ms,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    @staticmethod
    def _compute_diff(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
        mismatches: list[str] = []
        for key, expected_value in expected.items():
            actual_value = actual.get(key)
            if expected_value != actual_value:
                mismatches.append(f"{key}: expected {expected_value!r}, got {actual_value!r}")
        return {
            "mismatches": mismatches,
            "matched_keys": [key for key in expected if expected.get(key) == actual.get(key)],
            "passed": not mismatches,
        }

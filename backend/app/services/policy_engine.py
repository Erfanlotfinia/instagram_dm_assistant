from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.domain.enums import PilotOperatingMode


POLICY_NAMES = (
    "explicit_confirmation_required",
    "messaging_window_enforced",
    "no_state_change_in_shadow_mode",
    "no_order_creation_if_stock_unreserved",
    "mandatory_handoff_on_low_confidence",
)

DEFAULT_POLICY_CONFIG: dict[str, Any] = {
    "explicit_confirmation_required": {"enabled": True, "actions": ["confirm", "payment_link", "complete"]},
    "messaging_window_enforced": {"enabled": True, "window_hours": 24},
    "no_state_change_in_shadow_mode": {"enabled": True},
    "no_order_creation_if_stock_unreserved": {"enabled": True},
    "mandatory_handoff_on_low_confidence": {
        "enabled": True,
        "intent_threshold": 0.65,
        "variant_threshold": 0.70,
        "product_threshold": 0.75,
    },
}


@dataclass(frozen=True)
class PolicyCheckResult:
    name: str
    passed: bool
    reason: str | None = None
    severity: str = "info"


@dataclass
class PolicyEvaluationContext:
    shop_id: UUID
    operating_mode: PilotOperatingMode = PilotOperatingMode.COPILOT
    intent_confidence: float = 1.0
    product_confidence: float = 1.0
    variant_confidence: float = 1.0
    customer_confirmed: bool = False
    stock_reserved: bool = True
    within_messaging_window: bool = True
    action_name: str | None = None
    requires_write: bool = False
    handoff_required: bool = False
    emergency_stop: bool = False


@dataclass
class PolicyEvaluationResult:
    allowed: bool
    checks: list[PolicyCheckResult] = field(default_factory=list)
    blocked_actions: list[str] = field(default_factory=list)

    @property
    def failed_checks(self) -> list[PolicyCheckResult]:
        return [check for check in self.checks if not check.passed]


def merge_policy_config(config: dict[str, Any] | None) -> dict[str, Any]:
    merged = {key: dict(value) for key, value in DEFAULT_POLICY_CONFIG.items()}
    if not config:
        return merged
    for name, policy_cfg in config.items():
        if name in merged and isinstance(policy_cfg, dict):
            merged[name].update(policy_cfg)
    return merged


class PolicyEngine:
    def validate(self, config: dict[str, Any] | None) -> tuple[bool, list[str]]:
        errors: list[str] = []
        merged = merge_policy_config(config)
        for name in POLICY_NAMES:
            if name not in merged:
                errors.append(f"missing_policy:{name}")
                continue
            policy_cfg = merged[name]
            if not isinstance(policy_cfg, dict):
                errors.append(f"invalid_policy_config:{name}")
                continue
            if "enabled" not in policy_cfg:
                errors.append(f"missing_enabled_flag:{name}")
        handoff_cfg = merged.get("mandatory_handoff_on_low_confidence", {})
        for threshold_key in ("intent_threshold", "variant_threshold", "product_threshold"):
            value = handoff_cfg.get(threshold_key)
            if value is not None and not (0 <= float(value) <= 1):
                errors.append(f"invalid_threshold:{threshold_key}")
        return not errors, errors

    def evaluate(self, context: PolicyEvaluationContext, config: dict[str, Any] | None = None) -> PolicyEvaluationResult:
        merged = merge_policy_config(config)
        checks: list[PolicyCheckResult] = []
        blocked: list[str] = []

        if context.emergency_stop:
            checks.append(PolicyCheckResult("emergency_stop", False, "pilot_emergency_stop", "critical"))
            blocked.append("all_state_changes")
            return PolicyEvaluationResult(allowed=False, checks=checks, blocked_actions=blocked)

        checks.extend(self._evaluate_policies(context, merged))
        failed = [check for check in checks if not check.passed]
        if failed:
            blocked.extend([check.name for check in failed if check.name not in blocked])
        return PolicyEvaluationResult(allowed=not failed, checks=checks, blocked_actions=blocked)

    def _evaluate_policies(self, context: PolicyEvaluationContext, config: dict[str, Any]) -> list[PolicyCheckResult]:
        results: list[PolicyCheckResult] = []
        results.append(self._explicit_confirmation_required(context, config))
        results.append(self._messaging_window_enforced(context, config))
        results.append(self._no_state_change_in_shadow_mode(context, config))
        results.append(self._no_order_creation_if_stock_unreserved(context, config))
        results.append(self._mandatory_handoff_on_low_confidence(context, config))
        return results

    @staticmethod
    def _explicit_confirmation_required(context: PolicyEvaluationContext, config: dict[str, Any]) -> PolicyCheckResult:
        policy = config["explicit_confirmation_required"]
        if not policy.get("enabled", True):
            return PolicyCheckResult("explicit_confirmation_required", True)
        actions = set(policy.get("actions") or [])
        if context.action_name in actions and not context.customer_confirmed:
            return PolicyCheckResult(
                "explicit_confirmation_required",
                False,
                f"customer_confirmation_required_for:{context.action_name}",
                "warning",
            )
        return PolicyCheckResult("explicit_confirmation_required", True)

    @staticmethod
    def _messaging_window_enforced(context: PolicyEvaluationContext, config: dict[str, Any]) -> PolicyCheckResult:
        policy = config["messaging_window_enforced"]
        if not policy.get("enabled", True):
            return PolicyCheckResult("messaging_window_enforced", True)
        if not context.within_messaging_window:
            return PolicyCheckResult("messaging_window_enforced", False, "outside_messaging_window", "warning")
        return PolicyCheckResult("messaging_window_enforced", True)

    @staticmethod
    def _no_state_change_in_shadow_mode(context: PolicyEvaluationContext, config: dict[str, Any]) -> PolicyCheckResult:
        policy = config["no_state_change_in_shadow_mode"]
        if not policy.get("enabled", True):
            return PolicyCheckResult("no_state_change_in_shadow_mode", True)
        if context.operating_mode == PilotOperatingMode.SHADOW and context.requires_write:
            return PolicyCheckResult("no_state_change_in_shadow_mode", False, "shadow_mode_blocks_writes", "warning")
        return PolicyCheckResult("no_state_change_in_shadow_mode", True)

    @staticmethod
    def _no_order_creation_if_stock_unreserved(
        context: PolicyEvaluationContext, config: dict[str, Any]
    ) -> PolicyCheckResult:
        policy = config["no_order_creation_if_stock_unreserved"]
        if not policy.get("enabled", True):
            return PolicyCheckResult("no_order_creation_if_stock_unreserved", True)
        if context.action_name in {"create_draft", "reserve", "confirm"} and not context.stock_reserved:
            return PolicyCheckResult(
                "no_order_creation_if_stock_unreserved",
                False,
                "stock_not_reserved",
                "critical",
            )
        return PolicyCheckResult("no_order_creation_if_stock_unreserved", True)

    @staticmethod
    def _mandatory_handoff_on_low_confidence(context: PolicyEvaluationContext, config: dict[str, Any]) -> PolicyCheckResult:
        policy = config["mandatory_handoff_on_low_confidence"]
        if not policy.get("enabled", True):
            return PolicyCheckResult("mandatory_handoff_on_low_confidence", True)
        intent_threshold = float(policy.get("intent_threshold", 0.65))
        variant_threshold = float(policy.get("variant_threshold", 0.70))
        product_threshold = float(policy.get("product_threshold", 0.75))
        low_confidence = (
            context.intent_confidence < intent_threshold
            or context.variant_confidence < variant_threshold
            or context.product_confidence < product_threshold
        )
        if low_confidence or context.handoff_required:
            return PolicyCheckResult(
                "mandatory_handoff_on_low_confidence",
                False,
                "low_confidence_requires_handoff",
                "warning",
            )
        return PolicyCheckResult("mandatory_handoff_on_low_confidence", True)

    @staticmethod
    def confidence_band(score: float) -> str:
        if score >= 0.85:
            return "high"
        if score >= 0.55:
            return "medium"
        return "low"

    @staticmethod
    def autonomous_allowed(evaluation: PolicyEvaluationResult, operating_mode: PilotOperatingMode) -> bool:
        if operating_mode != PilotOperatingMode.AUTONOMOUS_LOW_RISK:
            return False
        return evaluation.allowed and not evaluation.blocked_actions

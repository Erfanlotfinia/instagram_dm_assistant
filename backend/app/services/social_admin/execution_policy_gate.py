from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID, uuid4

from app.services.social_admin.scenario_router import ScenarioDecision

ExecutionType = Literal["automation", "llm", "handoff"]


@dataclass(frozen=True)
class ExecutionPolicyDecision:
    decision: Literal["allow", "block"]
    reason: str
    execution_trace_id: UUID
    execution_type: str | None = None
    checks: list[dict[str, Any]] = field(default_factory=list)


class ExecutionPolicyGate:
    """Mandatory gate between ScenarioRouter and all execution targets."""

    allowed_execution_types = {"automation", "llm", "handoff"}
    llm_handler_names = {"LLMFallbackOrchestrator", "LLM", "LLMHandler"}

    def evaluate(
        self,
        decision: ScenarioDecision | None,
        *,
        requested_execution: str | None = None,
        source: str = "ScenarioRouter",
        automation_attempted: bool = False,
        execution_trace_id: UUID | None = None,
    ) -> ExecutionPolicyDecision:
        trace_id = execution_trace_id or uuid4()
        checks: list[dict[str, Any]] = []
        if source != "ScenarioRouter":
            return self._block(
                trace_id, "handler_bypassing_policy", requested_execution, checks
            )
        if decision is None or not decision.scenario_code or not decision.handler:
            return self._block(
                trace_id, "invalid_scenario_routing_result", requested_execution, checks
            )

        expected = self._expected_execution(decision)
        requested = requested_execution or expected
        checks.append({"check": "execution_type_known", "requested": requested})
        if requested not in self.allowed_execution_types:
            return self._block(trace_id, "unknown_execution_type", requested, checks)
        if requested != expected:
            return self._block(
                trace_id,
                f"unsafe_transition_{expected}_to_{requested}",
                requested,
                checks,
            )
        if requested == "llm" and not automation_attempted:
            return self._block(
                trace_id, "automation_first_required_before_llm", requested, checks
            )
        if requested == "automation" and decision.handler in self.llm_handler_names:
            return self._block(
                trace_id, "llm_direct_service_call_blocked", requested, checks
            )
        checks.append(
            {
                "check": "allowed_flow",
                "flow": f"ScenarioRouter→ExecutionPolicyGate→{requested}",
            }
        )
        return ExecutionPolicyDecision(
            "allow", "policy_allowed", trace_id, requested, checks
        )

    def _expected_execution(self, decision: ScenarioDecision) -> ExecutionType:
        if decision.requires_handoff:
            return "handoff"
        if decision.requires_llm:
            return "llm"
        return "automation"

    def _block(
        self,
        trace_id: UUID,
        reason: str,
        execution_type: str | None,
        checks: list[dict[str, Any]],
    ) -> ExecutionPolicyDecision:
        checks.append({"check": "blocked", "reason": reason})
        return ExecutionPolicyDecision(
            "block", reason, trace_id, execution_type, checks
        )

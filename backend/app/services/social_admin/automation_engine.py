from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.social_admin.handlers import (
    AutomationHandlerRegistry,
    HandlerContext,
    HandlerResult,
)
from app.services.social_admin.scenario_router import ScenarioDecision


@dataclass(frozen=True)
class AutomationEngineResult:
    """Result of the deterministic automation phase.

    This object makes the Modira execution contract explicit: the automation
    engine may run rule/catalog/order/payment/shipping handlers, while LLMs are
    represented only as a skipped fallback route and are never dispatched here.
    """

    executed: bool
    handler_result: HandlerResult | None
    skipped_reason: str | None = None


class AutomationEngine:
    """Strict automation-first executor for social commerce decisions."""

    def __init__(self, registry: AutomationHandlerRegistry | None = None) -> None:
        self.registry = registry or AutomationHandlerRegistry()

    def execute(
        self,
        decision: ScenarioDecision,
        context: HandlerContext | dict[str, Any],
    ) -> AutomationEngineResult:
        if decision.requires_llm:
            return AutomationEngineResult(False, None, "llm_fallback_route")
        if decision.requires_handoff:
            return AutomationEngineResult(False, None, "human_handoff_route")
        if decision.handler == "LLMFallbackOrchestrator":
            return AutomationEngineResult(False, None, "llm_handler_blocked")
        return AutomationEngineResult(True, self.registry.dispatch(decision.handler, context))

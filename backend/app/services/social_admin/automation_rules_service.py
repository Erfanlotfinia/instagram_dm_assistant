from __future__ import annotations

from app.schemas.social_admin import AutomationRuleStepRead

HANDLER_PRIORITY: list[tuple[str, str, str]] = [
    (
        "Button / callback payloads",
        "deterministic",
        "Inline buttons and callback data map directly to a known action with no ambiguity.",
    ),
    (
        "Explicit commands",
        "deterministic",
        "Slash-style or keyword commands the customer types to request a specific operation.",
    ),
    (
        "Active order state",
        "deterministic",
        "When an order is mid-flow, replies are routed to that order's next expected step.",
    ),
    (
        "Active context reference",
        "deterministic",
        'Resolves "this", "the previous one", or a forwarded post against recent conversation context.',
    ),
    (
        "Deterministic keyword / rule match",
        "deterministic",
        "Operator-configured rules and keyword patterns produce a consistent, auditable response.",
    ),
    (
        "Catalog query parser",
        "deterministic",
        "Parses product, attribute, and price intents to search the catalog without an LLM call.",
    ),
    (
        "Structured LLM fallback",
        "llm",
        "Only when deterministic layers miss, a constrained LLM returns a schema-validated action.",
    ),
    (
        "Human handoff",
        "human",
        "Low confidence, high risk, or unsafe content escalates to an operator with full context.",
    ),
]


class AutomationRulesService:
    def list_priority_steps(self) -> list[AutomationRuleStepRead]:
        return [
            AutomationRuleStepRead(order=index + 1, label=label, tier=tier, detail=detail)
            for index, (label, tier, detail) in enumerate(HANDLER_PRIORITY)
        ]

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.domain.enums import AgentIntent
from app.schemas.agent import AgentExtractionResult
from app.services.slot_merge_service import has_provided_slot_values

HANDOFF_INTENTS = {
    AgentIntent.HUMAN_HELP,
    AgentIntent.TRACK_ORDER,
}


@dataclass
class HandoffDecision:
    required: bool
    reason: str | None = None


def evaluate_handoff(
    extraction: AgentExtractionResult,
    *,
    failure_count: int,
    settings: Settings | None = None,
) -> HandoffDecision:
    settings = settings or get_settings()

    if extraction.needs_human and extraction.human_reason:
        return HandoffDecision(required=True, reason=extraction.human_reason)

    if extraction.intent in HANDOFF_INTENTS:
        return HandoffDecision(required=True, reason=f"Unsupported or escalated intent: {extraction.intent.value}")

    if extraction.confidence.intent < settings.agent_intent_confidence_threshold:
        return HandoffDecision(
            required=True,
            reason=f"Low intent confidence ({extraction.confidence.intent:.2f})",
        )

    if has_provided_slot_values(extraction) and extraction.confidence.slots < settings.agent_slots_confidence_threshold:
        return HandoffDecision(
            required=True,
            reason=f"Low slot confidence ({extraction.confidence.slots:.2f})",
        )

    if failure_count > settings.agent_max_failures:
        return HandoffDecision(
            required=True,
            reason=f"Repeated agent failures ({failure_count})",
        )

    return HandoffDecision(required=False)

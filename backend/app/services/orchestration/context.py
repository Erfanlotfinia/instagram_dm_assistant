from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.enums import PilotOperatingMode
from app.domain.models import (
    AgentRun,
    Conversation,
    Message,
    Order,
    Product,
    ProductVariant,
)
from app.schemas.agent import AgentExtractionInput, AgentExtractionResult


@dataclass
class StageOutcome:
    """Signal returned by a stage to the pipeline.

    ``stop`` short-circuits the pipeline (mirroring the early ``return`` points of
    the original ``process_inbound_message``). When a stage stops, it is itself
    responsible for performing any commit / priority-refresh side effects, exactly
    as the original early returns did.
    """

    stop: bool = False
    result: bool = False


CONTINUE = StageOutcome(stop=False)


def stop_with(result: bool) -> StageOutcome:
    return StageOutcome(stop=True, result=result)


@dataclass
class ResolutionResult:
    """Product + variant resolution facts produced by the resolution stage."""

    product: Product | None = None
    resolve_source: str = "unresolved"
    product_info: dict[str, Any] | None = None
    valid_colors: list[str] = field(default_factory=list)
    valid_sizes: list[str] = field(default_factory=list)
    variant: ProductVariant | None = None
    variant_match: Any | None = None
    variant_result: Any | None = None
    inventory_available: bool | None = None


@dataclass
class RiskDecisionResult:
    """Risk scoring + first auto-send decision facts."""

    settings_row: Any | None = None
    estimated_order_value: Decimal = Decimal("0")
    risk_score: Any | None = None
    decision: Any | None = None


@dataclass
class SideEffectDecisionResult:
    """Gate flags that determine whether order side effects may run."""

    base_order_side_effects_allowed: bool = False
    draft_order_candidate: bool = False
    pilot_order_allowed: bool = True
    pilot_order_reasons: list[str] = field(default_factory=list)
    pilot_order_preview_reasons: list[str] = field(default_factory=list)
    trust_write_allowed: bool = True
    order_side_effects_allowed: bool = False


@dataclass
class ReplyDecisionResult:
    """Second auto-send decision + send-time gate flags."""

    decision: Any | None = None
    force_preview: bool = False
    pilot_send_allowed: bool = True
    pilot_send_reasons: list[str] = field(default_factory=list)
    trust_send_allowed: bool = True


@dataclass
class ConversationPipelineContext:
    """Mutable state threaded through every orchestration stage.

    Field names intentionally mirror the local variables of the original
    ``ConversationOrchestrator.process_inbound_message`` so the moved logic stays
    a faithful, line-for-line translation.
    """

    conversation_id: UUID
    message_id: UUID

    conversation: Conversation | None = None
    message: Message | None = None
    slots: Any | None = None

    trace_id: UUID | None = None

    shared_post_url: str | None = None
    media_id: str | None = None

    extraction_input: AgentExtractionInput | None = None
    extraction: AgentExtractionResult | None = None
    extraction_error: str | None = None
    agent_run: AgentRun | None = None

    size_confirmation_needed: bool = False
    live_agent_settings: dict[str, Any] = field(default_factory=dict)

    handoff: Any | None = None
    state_decision: Any | None = None

    pilot_service: Any | None = None

    active_order: Order | None = None
    payment_url: str | None = None
    upsell_text: str | None = None
    reply: str | None = None
    outbound: Message | None = None

    combined_reasons: list[str] = field(default_factory=list)
    preview_reason: str | None = None

    policy_eval: Any | None = None
    operating_mode: PilotOperatingMode | None = None

    resolution: ResolutionResult = field(default_factory=ResolutionResult)
    risk: RiskDecisionResult = field(default_factory=RiskDecisionResult)
    side_effects: SideEffectDecisionResult = field(default_factory=SideEffectDecisionResult)
    reply_decision: ReplyDecisionResult = field(default_factory=ReplyDecisionResult)

"""Staged conversation orchestration pipeline.

This package decomposes the legacy monolithic
``ConversationOrchestrator.process_inbound_message`` into a sequence of small,
independently testable stages. The orchestrator is reduced to a thin coordinator
that builds a :class:`ConversationPipelineContext`, wires the shared
:class:`OrchestrationServices`, and runs the :class:`ConversationPipeline`.

The refactor is behavior-preserving: logic is moved verbatim from the original
method into the stages, and the safety gates (human control, emergency stop,
handoff, preview requirement, pilot mode, trust threshold, simulation, and
policy/risk checks) are kept intact.
"""

from app.services.orchestration.context import (
    ConversationPipelineContext,
    ReplyDecisionResult,
    ResolutionResult,
    RiskDecisionResult,
    SideEffectDecisionResult,
    StageOutcome,
)
from app.services.orchestration.pipeline import ConversationPipeline
from app.services.orchestration.services import OrchestrationServices

__all__ = [
    "ConversationPipeline",
    "ConversationPipelineContext",
    "OrchestrationServices",
    "ReplyDecisionResult",
    "ResolutionResult",
    "RiskDecisionResult",
    "SideEffectDecisionResult",
    "StageOutcome",
]

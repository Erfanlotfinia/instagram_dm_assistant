from __future__ import annotations

from app.services.orchestration.base import Stage
from app.services.orchestration.context import ConversationPipelineContext
from app.services.orchestration.services import OrchestrationServices
from app.services.orchestration.stages.llm_extraction import LLMExtractionStage
from app.services.orchestration.stages.load_context import LoadContextStage
from app.services.orchestration.stages.order_side_effect import OrderSideEffectStage
from app.services.orchestration.stages.product_resolution import ProductResolutionStage
from app.services.orchestration.stages.reply_generation import ReplyGenerationStage
from app.services.orchestration.stages.risk_and_policy import RiskAndPolicyStage
from app.services.orchestration.stages.send_or_suggest import SendOrSuggestStage
from app.services.orchestration.stages.slot_merge import SlotMergeStage
from app.services.orchestration.stages.social_admin_automation import SocialAdminAutomationStage
from app.services.orchestration.stages.trace_and_audit import TraceAndAuditStage

DEFAULT_STAGE_TYPES: tuple[type[Stage], ...] = (
    LoadContextStage,
    SocialAdminAutomationStage,
    ProductResolutionStage,
    LLMExtractionStage,
    SlotMergeStage,
    RiskAndPolicyStage,
    OrderSideEffectStage,
    ReplyGenerationStage,
    SendOrSuggestStage,
    TraceAndAuditStage,
)


class ConversationPipeline:
    """Runs the ordered conversation stages, short-circuiting on the first stop.

    The terminal :class:`TraceAndAuditStage` always stops with the final boolean
    result, so a fully-traversed pipeline still yields a deterministic return
    value. The default of ``True`` mirrors the original method's success path.
    """

    def __init__(
        self,
        services: OrchestrationServices,
        stage_types: tuple[type[Stage], ...] = DEFAULT_STAGE_TYPES,
    ) -> None:
        self.services = services
        self.stages: list[Stage] = [stage_type(services) for stage_type in stage_types]

    def run(self, ctx: ConversationPipelineContext) -> bool:
        for stage in self.stages:
            outcome = stage.run(ctx)
            if outcome.stop:
                return outcome.result
        return True

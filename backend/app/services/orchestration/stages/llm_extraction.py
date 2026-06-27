from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.metrics import record_agent_failure
from app.domain.enums import AgentRunStatus
from app.domain.models import AgentRun
from app.schemas.agent import AgentExtractionInput, AgentExtractionResult
from app.services.llm_extraction_service import mask_sensitive_llm_output
from app.services.orchestration.base import Stage
from app.services.orchestration.context import CONTINUE, ConversationPipelineContext, StageOutcome
from app.services.slot_merge_service import slots_to_dict


class LLMExtractionStage(Stage):
    """Bounded LLM fallback: build the extraction input, run it, persist the run."""

    def run(self, ctx: ConversationPipelineContext) -> StageOutcome:
        services = self.services
        conversation = ctx.conversation
        slots = ctx.slots
        resolution = ctx.resolution

        extraction_input = AgentExtractionInput(
            message_text=ctx.message.text,
            shared_post_url=ctx.shared_post_url or slots.instagram_post_url,
            workflow_state=conversation.workflow_state,
            known_slots=slots_to_dict(slots),
            product_info=resolution.product_info,
            valid_colors=resolution.valid_colors,
            valid_sizes=resolution.valid_sizes,
        )
        ctx.extraction_input = extraction_input

        extraction, extraction_error = services.llm_service.extract(extraction_input)
        ctx.extraction = extraction
        ctx.extraction_error = extraction_error

        ctx.agent_run = self._store_agent_run(
            conversation_id=ctx.conversation_id,
            message_id=ctx.message_id,
            extraction_input=extraction_input,
            extraction=extraction,
            error_message=extraction_error,
            is_simulation=conversation.is_simulation,
            channel_provider=conversation.channel_provider,
        )

        if extraction_error:
            conversation.agent_failure_count += 1
        return CONTINUE

    def _store_agent_run(
        self,
        *,
        conversation_id: UUID,
        message_id: UUID,
        extraction_input: AgentExtractionInput,
        extraction: AgentExtractionResult,
        error_message: str | None,
        is_simulation: bool = False,
        channel_provider: object | None = None,
    ) -> AgentRun:
        services = self.services
        run = AgentRun(
            conversation_id=conversation_id,
            input_message_id=message_id,
            model_name=services.llm_service.model_name,
            prompt_version=services.llm_service.prompt_version,
            input_json=extraction_input.model_dump(mode="json"),
            output_json=self._agent_run_output_json(extraction, error_message),
            status=AgentRunStatus.FAILED if error_message else AgentRunStatus.SUCCESS,
            error_message=error_message,
            is_simulation=is_simulation,
        )
        if error_message:
            record_agent_failure(channel_provider)
        return services.agent_runs.create(run)

    def _agent_run_output_json(
        self, extraction: AgentExtractionResult, error_message: str | None
    ) -> dict[str, Any]:
        payload = extraction.model_dump(mode="json")
        if error_message:
            invalid_output = getattr(self.services.llm_service, "last_invalid_output", None)
            payload["safe_fallback"] = True
            payload["invalid_llm_output"] = (
                mask_sensitive_llm_output(invalid_output) if invalid_output else None
            )
        return payload

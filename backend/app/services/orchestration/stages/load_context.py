from __future__ import annotations

import logging

from app.domain.enums import ConversationEventType, ConversationResponseMode
from app.domain.models import Message
from app.services.conversation_event_service import ConversationEventService
from app.services.conversation_priority_service import ConversationPriorityService
from app.services.orchestration.base import Stage
from app.services.orchestration.context import (
    CONTINUE,
    ConversationPipelineContext,
    StageOutcome,
    stop_with,
)

logger = logging.getLogger(__name__)


class LoadContextStage(Stage):
    """Load conversation/message, dedup agent runs, and enforce human-control skip.

    Owns the original early-return semantics:
    - not found -> return False (no commit)
    - duplicate agent run -> commit, return True
    - human control -> refresh priority, commit, return True
    """

    def run(self, ctx: ConversationPipelineContext) -> StageOutcome:
        services = self.services
        conversation_id = ctx.conversation_id
        message_id = ctx.message_id

        conversation = services.conversations.get_by_id(conversation_id)
        if conversation is None:
            logger.warning("Conversation %s not found", conversation_id)
            return stop_with(False)
        ctx.conversation = conversation

        message = services.messages.get_by_id(message_id)
        if message is None:
            logger.warning("Message %s not found", message_id)
            return stop_with(False)
        ctx.message = message

        existing_run = services.agent_runs.get_by_input_message_id(message_id)
        if existing_run is not None:
            logger.info(
                "Agent run already exists for message %s; skipping duplicate processing",
                message_id,
            )
            services.db.commit()
            return stop_with(True)

        ctx.trace_id = services.trace_service.bind_trace_context(
            services.trace_service.new_trace_id()
        )

        ConversationEventService(services.db).record(
            conversation_id,
            ConversationEventType.INBOUND_MESSAGE,
            description=(message.text or "")[:200] or None,
            metadata={"message_id": str(message.id)},
        )
        if (
            conversation.agent_paused
            or conversation.assigned_operator_id is not None
            or conversation.response_mode in {
                ConversationResponseMode.HUMAN,
                ConversationResponseMode.PAUSED,
            }
        ):
            logger.info("Conversation %s is under human control; skipping agent", conversation_id)
            ConversationPriorityService(services.db).refresh(conversation_id)
            services.db.commit()
            return stop_with(True)

        ctx.slots = services.slots_repo.get_or_create(conversation_id)
        ctx.shared_post_url, ctx.media_id = self._extract_post_reference(message)
        return CONTINUE

    @staticmethod
    def _extract_post_reference(message: Message) -> tuple[str | None, str | None]:
        meta = message.raw_payload.get("_meta", {}) if message.raw_payload else {}
        shared_post_url = meta.get("shared_post_url")
        media_id = None
        attachment = message.raw_payload.get("message", {}).get("attachments", [])
        if attachment:
            payload = attachment[0].get("payload", {})
            media_id = payload.get("ig_post_media_id") or payload.get("media_id")
        return shared_post_url, media_id

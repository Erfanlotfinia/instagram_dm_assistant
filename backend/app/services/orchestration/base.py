from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.orchestration.context import ConversationPipelineContext, StageOutcome
from app.services.orchestration.services import OrchestrationServices


class Stage(ABC):
    """A single, independently testable step of the conversation pipeline."""

    def __init__(self, services: OrchestrationServices) -> None:
        self.services = services

    @abstractmethod
    def run(self, ctx: ConversationPipelineContext) -> StageOutcome:
        """Execute the stage, mutating ``ctx`` and returning a control signal."""
        raise NotImplementedError

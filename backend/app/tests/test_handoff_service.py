from app.core.config import Settings
from app.domain.enums import AgentIntent
from app.schemas.agent import AgentExtractionResult, ExtractedSlots, ExtractionConfidence
from app.services.handoff_service import evaluate_handoff


def test_low_intent_confidence_triggers_handoff() -> None:
    extraction = AgentExtractionResult(
        intent=AgentIntent.BUY_PRODUCT,
        confidence=ExtractionConfidence(intent=0.4, slots=0.9, product=0.9),
    )
    decision = evaluate_handoff(extraction, failure_count=0, settings=Settings())
    assert decision.required is True
    assert decision.reason is not None
    assert "intent confidence" in decision.reason


def test_low_slot_confidence_triggers_handoff_when_slots_provided() -> None:
    extraction = AgentExtractionResult(
        intent=AgentIntent.PROVIDE_INFO,
        slots=ExtractedSlots(color="black"),
        confidence=ExtractionConfidence(intent=0.9, slots=0.4, product=0.9),
    )
    decision = evaluate_handoff(extraction, failure_count=0, settings=Settings())
    assert decision.required is True
    assert "slot confidence" in (decision.reason or "")


def test_repeated_failures_trigger_handoff() -> None:
    extraction = AgentExtractionResult(
        intent=AgentIntent.BUY_PRODUCT,
        confidence=ExtractionConfidence(intent=0.9, slots=0.9, product=0.9),
    )
    settings = Settings(agent_max_failures=2)
    decision = evaluate_handoff(extraction, failure_count=3, settings=settings)
    assert decision.required is True
    assert "Repeated agent failures" in (decision.reason or "")

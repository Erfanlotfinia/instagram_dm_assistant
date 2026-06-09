from decimal import Decimal

from pydantic import ValidationError

from app.schemas.agent import AgentExtractionResult
from app.services.agent_risk_scoring_service import AgentRiskScoringInput, AgentRiskScoringService
from app.services.llm_extraction_service import LLMExtractionService, mask_sensitive_llm_output


class BadJsonClient:
    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        return '{"intent": "buy_product", "confidence": {"intent": 2}, "slots": {"phone": "09121234567"}'


def test_invalid_llm_json_fallback_masks_sensitive_output():
    service = LLMExtractionService(chat_client=BadJsonClient())
    result, error = service.extract(
        __import__('app.schemas.agent', fromlist=['AgentExtractionInput']).AgentExtractionInput(
            message_text='my phone is 09121234567', shared_post_url=None, workflow_state='idle', known_slots={}, product_info=None, valid_colors=[], valid_sizes=[]
        )
    )
    assert error
    assert result.needs_human is True
    assert result.intent.value == 'unclear'
    assert '[masked_phone]' in mask_sensitive_llm_output(service.last_invalid_output)


def test_invalid_confidence_values_rejected_by_schema():
    try:
        AgentExtractionResult.model_validate({'intent': 'buy_product', 'confidence': {'intent': 1.5}})
    except ValidationError:
        pass
    else:
        raise AssertionError('invalid confidence should be rejected')


def test_payment_dispute_requires_handoff():
    risk = AgentRiskScoringService().score(AgentRiskScoringInput(intent_confidence=0.9, slot_confidence=0.9, product_confidence=0.9, variant_confidence=0.9, address_confidence=0.9, message_text='I was charged twice, refund me', payment_related_message=True))
    assert risk.requires_handoff is True
    assert risk.risk_level == 'critical'


def test_angry_customer_requires_handoff():
    risk = AgentRiskScoringService().score(AgentRiskScoringInput(intent_confidence=0.9, slot_confidence=0.9, product_confidence=0.9, variant_confidence=0.9, address_confidence=0.9, message_text='angry complaint'))
    assert risk.requires_handoff is True


def test_high_value_order_requires_preview():
    risk = AgentRiskScoringService().score(AgentRiskScoringInput(intent_confidence=0.9, slot_confidence=0.9, product_confidence=0.9, variant_confidence=0.9, address_confidence=0.9, order_value=Decimal('750'), settings={'high_value_order_threshold': '500'}))
    assert risk.requires_preview is True
    assert 'high_value_order_requires_preview' in risk.risk_reasons


def test_low_variant_confidence_requires_preview_or_handoff():
    risk = AgentRiskScoringService().score(AgentRiskScoringInput(intent_confidence=0.9, slot_confidence=0.9, product_confidence=0.9, variant_confidence=0.2, address_confidence=0.9, settings={'handoff_for_low_variant_confidence': True}))
    assert risk.requires_preview is True
    assert risk.requires_handoff is True

import json

from app.integrations.openai_client import MockOpenAIChatClient
from app.schemas.agent import AgentExtractionInput, AgentIntent
from app.domain.enums import AgentWorkflowState
from app.services.llm_extraction_service import LLMExtractionService, PROMPT_VERSION


def test_llm_extraction_validates_mock_openai_response() -> None:
    mock_response = {
        "intent": "buy_product",
        "product_reference": {"instagram_post_url": None, "instagram_media_id": None},
        "slots": {
            "color": "black",
            "size": "L",
            "quantity": 1,
            "customer_name": None,
            "phone": None,
            "city": None,
            "address": None,
            "postal_code": None,
        },
        "missing_fields": ["customer_name", "phone", "city", "address"],
        "confidence": {"intent": 0.92, "slots": 0.88, "product": 0.95},
        "needs_human": False,
        "human_reason": None,
        "reply_style_hint": "friendly",
    }
    client = MockOpenAIChatClient(responses=[json.dumps(mock_response)])
    service = LLMExtractionService(chat_client=client)

    result, error = service.extract(
        AgentExtractionInput(
            message_text="black size L",
            shared_post_url="https://instagram.com/p/abc",
            workflow_state=AgentWorkflowState.IDLE,
            known_slots={},
            product_info={"title": "Hoodie"},
            valid_colors=["Black"],
            valid_sizes=["L", "M"],
        )
    )

    assert error is None
    assert result.intent == AgentIntent.BUY_PRODUCT
    assert result.slots.color == "black"
    assert service.prompt_version == PROMPT_VERSION


def test_llm_extraction_invalid_json_uses_safe_fallback() -> None:
    client = MockOpenAIChatClient(responses=["not-json"])
    service = LLMExtractionService(chat_client=client)
    result, error = service.extract(
        AgentExtractionInput(
            message_text="hello",
            shared_post_url=None,
            workflow_state=AgentWorkflowState.IDLE,
            known_slots={},
            product_info=None,
            valid_colors=[],
            valid_sizes=[],
        )
    )
    assert error is not None
    assert result.intent == AgentIntent.UNCLEAR
    assert result.confidence.intent == 0.0

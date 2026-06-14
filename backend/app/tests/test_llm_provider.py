from unittest.mock import MagicMock, patch
import sys

import pytest

from app.core.config import Settings
from app.domain.enums import AgentIntent, AgentWorkflowState
from app.integrations.gemini_client import LiveGeminiChatClient, LiveGeminiEmbeddingClient
from app.integrations.llm_client import build_chat_client, build_embedding_client
from app.integrations.openai_client import (
    LiveOpenAIChatClient,
    LiveOpenAIEmbeddingClient,
    MockOpenAIChatClient,
    MockOpenAIEmbeddingClient,
)
from app.schemas.agent import AgentExtractionInput
from app.services.llm_extraction_service import LLMExtractionService


def test_settings_chat_model_follows_provider(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    settings = Settings()
    assert settings.chat_model == "gemini-2.5-flash"
    assert settings.embedding_model == "gemini-embedding-001"


def test_settings_llm_api_key_configured_for_gemini(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    settings = Settings()
    assert settings.llm_api_key_configured is True


def test_build_chat_client_uses_openai_by_default(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    settings = Settings()
    client = build_chat_client(settings)
    assert isinstance(client, LiveOpenAIChatClient)


def test_build_chat_client_uses_gemini_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    settings = Settings()
    client = build_chat_client(settings)
    assert isinstance(client, LiveGeminiChatClient)


def test_build_chat_client_uses_mock_in_mock_mode(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "mock")
    settings = Settings()
    client = build_chat_client(settings)
    assert isinstance(client, MockOpenAIChatClient)


def test_build_embedding_client_uses_gemini_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    settings = Settings()
    client = build_embedding_client(settings)
    assert isinstance(client, LiveGeminiEmbeddingClient)


def _patch_google_genai(mock_client: MagicMock):
    mock_genai = MagicMock()
    mock_genai.Client = MagicMock(return_value=mock_client)
    mock_types = MagicMock()
    mock_genai.types = mock_types
    mock_google = MagicMock()
    mock_google.genai = mock_genai
    return patch.dict(
        sys.modules,
        {
            "google": mock_google,
            "google.genai": mock_genai,
            "google.genai.types": mock_types,
        },
    )


def test_gemini_chat_client_complete_json(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    settings = Settings()

    mock_response = MagicMock()
    mock_response.text = '{"intent":"unclear"}'
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with _patch_google_genai(mock_client):
        result = LiveGeminiChatClient(settings).complete_json("system", "user")

    assert result == '{"intent":"unclear"}'
    mock_client.models.generate_content.assert_called_once()


def test_gemini_embedding_client_embed_text(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    settings = Settings()

    mock_embedding = MagicMock()
    mock_embedding.values = [0.1, 0.2, 0.3]
    mock_response = MagicMock()
    mock_response.embeddings = [mock_embedding]
    mock_client = MagicMock()
    mock_client.models.embed_content.return_value = mock_response

    with _patch_google_genai(mock_client):
        vector = LiveGeminiEmbeddingClient(settings).embed_text("hello")

    assert vector == [0.1, 0.2, 0.3]


def test_gemini_chat_client_wraps_api_errors_as_runtime_error(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    settings = Settings()

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED")

    with _patch_google_genai(mock_client):
        with pytest.raises(RuntimeError, match="Gemini chat request failed"):
            LiveGeminiChatClient(settings).complete_json("system", "user")


class _ExplodingChatClient:
    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        raise RuntimeError("429 RESOURCE_EXHAUSTED")


def test_extraction_falls_back_to_handoff_when_provider_errors(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    service = LLMExtractionService(chat_client=_ExplodingChatClient(), settings=Settings())

    payload = AgentExtractionInput(
        message_text="Do you have this hoodie in medium?",
        shared_post_url=None,
        workflow_state=AgentWorkflowState.IDLE,
        known_slots={},
        product_info=None,
        valid_colors=[],
        valid_sizes=[],
    )

    result, error = service.extract(payload)

    assert result.intent == AgentIntent.UNCLEAR
    assert result.needs_human is True
    assert error is not None

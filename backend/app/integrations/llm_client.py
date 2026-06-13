from __future__ import annotations

from app.core.config import Settings, get_settings
from app.integrations.gemini_client import LiveGeminiChatClient, LiveGeminiEmbeddingClient
from app.integrations.openai_client import (
    LiveOpenAIChatClient,
    LiveOpenAIEmbeddingClient,
    MockOpenAIChatClient,
    MockOpenAIEmbeddingClient,
    OpenAIChatClient,
    OpenAIEmbeddingClient,
)


def build_chat_client(settings: Settings | None = None) -> OpenAIChatClient:
    settings = settings or get_settings()
    if settings.llm_mode == "mock":
        return MockOpenAIChatClient()
    if settings.llm_provider == "gemini":
        return LiveGeminiChatClient(settings)
    return LiveOpenAIChatClient(settings)


def build_embedding_client(settings: Settings | None = None) -> OpenAIEmbeddingClient:
    settings = settings or get_settings()
    if settings.llm_mode == "mock":
        return MockOpenAIEmbeddingClient()
    if settings.llm_provider == "gemini":
        return LiveGeminiEmbeddingClient(settings)
    return LiveOpenAIEmbeddingClient(settings)

from __future__ import annotations

import json
import logging
from typing import Protocol

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class OpenAIChatClient(Protocol):
    def complete_json(self, system_prompt: str, user_prompt: str) -> str: ...


class OpenAIEmbeddingClient(Protocol):
    def embed_text(self, text: str) -> list[float]: ...


def build_openai_client(settings: Settings):
    from openai import OpenAI

    kwargs: dict[str, str] = {"api_key": settings.openai_api_key}
    if settings.openai_api_base_url:
        kwargs["base_url"] = settings.openai_api_base_url.rstrip("/")
    return OpenAI(**kwargs)


class LiveOpenAIChatClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        client = build_openai_client(self.settings)
        try:
            response = client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
        except Exception as exc:  # normalize provider/API errors for graceful fallback
            raise RuntimeError(f"OpenAI chat request failed: {exc}") from exc
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI returned empty content")
        return content


class LiveOpenAIEmbeddingClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def embed_text(self, text: str) -> list[float]:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        client = build_openai_client(self.settings)
        try:
            response = client.embeddings.create(
                model=self.settings.openai_embedding_model,
                input=text,
            )
        except Exception as exc:  # normalize provider/API errors for graceful fallback
            raise RuntimeError(f"OpenAI embedding request failed: {exc}") from exc
        return response.data[0].embedding


class MockOpenAIChatClient:
    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = list(responses or [])
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        if not self._responses:
            return json.dumps(
                {
                    "intent": "unclear",
                    "product_reference": {"instagram_post_url": None, "instagram_media_id": None},
                    "slots": {
                        "color": None,
                        "size": None,
                        "quantity": None,
                        "customer_name": None,
                        "phone": None,
                        "city": None,
                        "address": None,
                        "postal_code": None,
                    },
                    "missing_fields": [],
                    "confidence": {"intent": 0.5, "slots": 0.5, "product": 0.5},
                    "needs_human": False,
                    "human_reason": None,
                    "reply_style_hint": None,
                }
            )
        return self._responses.pop(0)


class MockOpenAIEmbeddingClient:
    def embed_text(self, text: str) -> list[float]:
        seed = sum(ord(char) for char in text) % 997
        return [((seed + index) % 100) / 100.0 for index in range(8)]

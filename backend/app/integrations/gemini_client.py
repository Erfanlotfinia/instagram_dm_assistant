from __future__ import annotations

from app.core.config import Settings, get_settings


class LiveGeminiChatClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        if not self.settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.settings.gemini_api_key)
        try:
            response = client.models.generate_content(
                model=self.settings.gemini_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
        except Exception as exc:  # normalize provider/API errors for graceful fallback
            raise RuntimeError(f"Gemini chat request failed: {exc}") from exc
        content = response.text
        if not content:
            raise RuntimeError("Gemini returned empty content")
        return content


class LiveGeminiEmbeddingClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def embed_text(self, text: str) -> list[float]:
        if not self.settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        from google import genai

        client = genai.Client(api_key=self.settings.gemini_api_key)
        try:
            response = client.models.embed_content(
                model=self.settings.gemini_embedding_model,
                contents=text,
            )
        except Exception as exc:  # normalize provider/API errors for graceful fallback
            raise RuntimeError(f"Gemini embedding request failed: {exc}") from exc
        embeddings = response.embeddings
        if not embeddings:
            raise RuntimeError("Gemini returned empty embedding")
        values = embeddings[0].values
        if values is None:
            raise RuntimeError("Gemini returned empty embedding values")
        return list(values)

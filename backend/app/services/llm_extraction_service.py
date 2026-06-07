from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.integrations.openai_client import LiveOpenAIChatClient, OpenAIChatClient
from app.schemas.agent import AgentExtractionInput, AgentExtractionResult, AgentIntent, ExtractionConfidence

logger = logging.getLogger(__name__)

PROMPT_VERSION = "sprint4-v1"

SYSTEM_PROMPT = """You are an extraction engine for an Instagram DM ordering assistant.
Return ONLY valid JSON matching the schema below. Never invent prices, stock, or product facts.

Schema:
{
  "intent": "buy_product | ask_price | ask_stock | provide_info | confirm_order | cancel_order | track_order | unclear | human_help",
  "product_reference": {
    "instagram_post_url": "string|null",
    "instagram_media_id": "string|null"
  },
  "slots": {
    "color": "string|null",
    "size": "string|null",
    "quantity": "number|null",
    "customer_name": "string|null",
    "phone": "string|null",
    "city": "string|null",
    "address": "string|null",
    "postal_code": "string|null"
  },
  "missing_fields": ["string"],
  "confidence": {
    "intent": 0.0,
    "slots": 0.0,
    "product": 0.0
  },
  "needs_human": false,
  "human_reason": "string|null",
  "reply_style_hint": "string|null"
}

Rules:
- Use Persian-friendly slot values when the customer writes in Persian.
- Set needs_human=true for angry complaints, payment disputes, or unsupported requests.
- Do not guess product identity; only use provided references.
"""


class LLMExtractionService:
    def __init__(
        self,
        chat_client: OpenAIChatClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.chat_client = chat_client or LiveOpenAIChatClient(self.settings)

    @property
    def model_name(self) -> str:
        return self.settings.openai_model

    @property
    def prompt_version(self) -> str:
        return PROMPT_VERSION

    def extract(self, payload: AgentExtractionInput) -> tuple[AgentExtractionResult, str | None]:
        user_prompt = json.dumps(payload.model_dump(mode="json"), ensure_ascii=False)
        try:
            raw = self.chat_client.complete_json(SYSTEM_PROMPT, user_prompt)
            parsed = json.loads(raw)
            result = AgentExtractionResult.model_validate(parsed)
            return result, None
        except (json.JSONDecodeError, ValidationError, RuntimeError) as exc:
            logger.warning("LLM extraction failed; using safe fallback: %s", exc)
            return self._fallback_result(), str(exc)

    @staticmethod
    def _fallback_result() -> AgentExtractionResult:
        return AgentExtractionResult(
            intent=AgentIntent.UNCLEAR,
            missing_fields=[],
            confidence=ExtractionConfidence(intent=0.0, slots=0.0, product=0.0),
            needs_human=False,
            human_reason=None,
            reply_style_hint="apologetic",
        )

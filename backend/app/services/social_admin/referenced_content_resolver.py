from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import re

@dataclass
class ReferencedContentResolution:
    reference_type: str = "unknown"
    external_reference_id: str | None = None
    external_url: str | None = None
    candidate_products: list[str] = field(default_factory=list)
    selected_product_id: str | None = None
    selected_context_item_id: str | None = None
    confidence: float = 0.0
    needs_clarification: bool = False
    clarification_question: str | None = None

class ReferencedContentResolver:
    def __init__(self, context_service: Any) -> None:
        self.context_service = context_service

    def resolve(self, message: Any, raw_provider_payload: dict[str, Any] | None, conversation_id: str) -> ReferencedContentResolution:
        payload = raw_provider_payload or {}; text = getattr(message, "text", None) or (message.get("text") if isinstance(message, dict) else None) or payload.get("text") or ""
        meta = payload.get("reply_to") or payload.get("story") or payload.get("post") or payload.get("forwarded") or {}
        if meta:
            typ = "story_reply" if payload.get("story") else "reel_reply" if payload.get("reel") else "forwarded_message" if payload.get("forwarded") else "shared_post"
            return ReferencedContentResolution(typ, str(meta.get("id") or meta.get("mid") or ""), meta.get("url"), confidence=.9)
        url = re.search(r"https?://\S+", text)
        if url:
            return ReferencedContentResolution("shared_post", external_url=url.group(0), confidence=.82)
        ref = self.context_service.resolve_reference({"text": text}, conversation_id)
        if ref.selected_context_item_id:
            return ReferencedContentResolution("product_list_selection" if ref.reason.startswith("ordinal") else "previous_product", selected_product_id=ref.selected_product_id, selected_context_item_id=ref.selected_context_item_id, confidence=ref.confidence, needs_clarification=ref.needs_clarification, clarification_question=ref.clarification_question)
        return ReferencedContentResolution(needs_clarification=True, clarification_question="Please send the product link, image, or name.", confidence=.1)

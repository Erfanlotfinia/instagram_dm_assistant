from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4
import re

ORDINALS = {"1":0,"۱":0,"اول":0,"first":0,"one":0,"یک":0,"2":1,"۲":1,"دوم":1,"دومی":1,"second":1,"two":1,"دو":1,"3":2,"۳":2,"سوم":2,"third":2,"three":2}
REF_WORDS = ("this","that","it","same","before","yesterday","این","اون","همون","همونو","قبلی","دیروز","موجوده","چند")

@dataclass
class ContextItem:
    shop_id: str
    conversation_id: str
    provider: str
    channel_account_id: str | None = None
    item_type: str = "media"
    id: str = field(default_factory=lambda: str(uuid4()))
    source_message_id: str | None = None
    external_reference_id: str | None = None
    external_url: str | None = None
    title: str | None = None
    text: str | None = None
    media_json: dict[str, Any] | None = None
    candidate_product_ids_json: list[str] = field(default_factory=list)
    selected_product_id: str | None = None
    selected_variant_id: str | None = None
    attributes_json: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ReferenceLink:
    shop_id: str
    conversation_id: str
    from_message_id: str
    to_context_item_id: str
    relation_type: str
    confidence: float
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ReferenceResolution:
    selected_context_item_id: str | None
    selected_product_id: str | None
    selected_variant_id: str | None = None
    confidence: float = 0.0
    needs_clarification: bool = False
    clarification_question: str | None = None
    reason: str = "no_context"

class ConversationContextService:
    def __init__(self) -> None:
        self.items: list[ContextItem] = []
        self.links: list[ReferenceLink] = []

    def add_context_item(self, **kwargs: Any) -> ContextItem:
        item = ContextItem(**kwargs)
        self.items.append(item)
        return item

    def link_message_to_context(self, shop_id: str, conversation_id: str, from_message_id: str, to_context_item_id: str, relation_type: str, confidence: float = .9) -> ReferenceLink:
        link = ReferenceLink(shop_id, conversation_id, from_message_id, to_context_item_id, relation_type, confidence)
        self.links.append(link)
        return link

    def get_recent_context(self, conversation_id: str, limit: int = 10) -> list[ContextItem]:
        now = datetime.now(timezone.utc)
        rows = [i for i in self.items if i.conversation_id == conversation_id and (i.expires_at is None or i.expires_at > now)]
        return sorted(rows, key=lambda i: i.created_at, reverse=True)[:limit]

    def get_last_product_list(self, conversation_id: str) -> ContextItem | None:
        return next((i for i in self.get_recent_context(conversation_id, 20) if i.item_type in {"product_list","catalog_search_result"}), None)

    def get_active_product_context(self, conversation_id: str) -> ContextItem | None:
        return next((i for i in self.get_recent_context(conversation_id, 20) if i.selected_product_id or i.candidate_product_ids_json), None)

    def resolve_reference(self, message: Any, conversation_id: str) -> ReferenceResolution:
        text = (getattr(message, "text", None) or (message.get("text") if isinstance(message, dict) else "") or "").lower()
        for token, index in sorted(ORDINALS.items(), key=lambda kv: len(kv[0]), reverse=True):
            has_token = bool(re.search(rf"\b{re.escape(token)}\b", text)) if token.isascii() else token in text
            if has_token:
                lst = self.get_last_product_list(conversation_id)
                if lst and len(lst.candidate_product_ids_json) > index:
                    return ReferenceResolution(lst.id, lst.candidate_product_ids_json[index], confidence=.95, reason="ordinal_product_list_selection")
        if any(w in text for w in REF_WORDS):
            active = self.get_active_product_context(conversation_id)
            if active:
                product_id = active.selected_product_id or (active.candidate_product_ids_json[0] if len(active.candidate_product_ids_json)==1 else None)
                if product_id:
                    return ReferenceResolution(active.id, product_id, active.selected_variant_id, confidence=.88, reason="active_product_context")
                return ReferenceResolution(active.id, None, confidence=.6, needs_clarification=True, clarification_question="Which product do you mean?", reason="ambiguous_active_context")
        return ReferenceResolution(None, None)

    def expire_old_context(self, older_than_hours: int = 48) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        n = 0
        for item in self.items:
            if item.expires_at is None and item.created_at < cutoff and item.item_type not in {"order_summary","product_post","product_card"}:
                item.expires_at = datetime.now(timezone.utc); n += 1
        return n

    def explain_context_resolution(self, resolution: ReferenceResolution) -> dict[str, Any]:
        return resolution.__dict__

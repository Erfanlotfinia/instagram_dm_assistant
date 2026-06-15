from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.domain.models import ConversationContextItem, ConversationReferenceLink
from app.repositories.conversation_context_repository import ConversationContextRepository

ORDINALS = {
    "1": 0,
    "۱": 0,
    "اول": 0,
    "first": 0,
    "one": 0,
    "یک": 0,
    "2": 1,
    "۲": 1,
    "دوم": 1,
    "دومی": 1,
    "second": 1,
    "two": 1,
    "دو": 1,
    "3": 2,
    "۳": 2,
    "سوم": 2,
    "third": 2,
    "three": 2,
}
REF_WORDS = (
    "this",
    "that",
    "it",
    "same",
    "before",
    "yesterday",
    "این",
    "اون",
    "همون",
    "همونو",
    "قبلی",
    "دیروز",
    "موجوده",
    "چند",
)


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


def _parse_uuid(value: str | UUID | None) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _model_to_item(row: ConversationContextItem) -> ContextItem:
    candidates = row.candidate_product_ids_json or []
    return ContextItem(
        id=str(row.id),
        shop_id=str(row.shop_id),
        conversation_id=str(row.conversation_id),
        provider=row.provider,
        channel_account_id=row.channel_account_id,
        item_type=row.item_type,
        source_message_id=str(row.source_message_id) if row.source_message_id else None,
        external_reference_id=row.external_reference_id,
        external_url=row.external_url,
        title=row.title,
        text=row.text,
        media_json=row.media_json or {},
        candidate_product_ids_json=[str(c) for c in candidates],
        selected_product_id=str(row.selected_product_id) if row.selected_product_id else None,
        selected_variant_id=str(row.selected_variant_id) if row.selected_variant_id else None,
        attributes_json=row.attributes_json or {},
        confidence=float(row.confidence),
        expires_at=row.expires_at,
        created_at=row.created_at,
    )


class ConversationContextService:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db
        self._repo = ConversationContextRepository(db) if db is not None else None
        self.items: list[ContextItem] = []
        self.links: list[ReferenceLink] = []

    def add_context_item(self, **kwargs: Any) -> ContextItem:
        if self._repo is not None:
            shop_id = _parse_uuid(kwargs["shop_id"])
            conversation_id = _parse_uuid(kwargs["conversation_id"])
            if shop_id is None or conversation_id is None:
                raise ValueError("shop_id and conversation_id are required")
            row = ConversationContextItem(
                shop_id=shop_id,
                conversation_id=conversation_id,
                provider=kwargs.get("provider", "instagram"),
                channel_account_id=kwargs.get("channel_account_id"),
                item_type=kwargs.get("item_type", "media"),
                source_message_id=_parse_uuid(kwargs.get("source_message_id")),
                external_reference_id=kwargs.get("external_reference_id"),
                external_url=kwargs.get("external_url"),
                title=kwargs.get("title"),
                text=kwargs.get("text"),
                media_json=kwargs.get("media_json") or {},
                candidate_product_ids_json=kwargs.get("candidate_product_ids_json") or [],
                selected_product_id=_parse_uuid(kwargs.get("selected_product_id")),
                selected_variant_id=_parse_uuid(kwargs.get("selected_variant_id")),
                attributes_json=kwargs.get("attributes_json") or {},
                confidence=kwargs.get("confidence", 1.0),
                expires_at=kwargs.get("expires_at"),
            )
            saved = self._repo.add_item(row)
            return _model_to_item(saved)
        item = ContextItem(**kwargs)
        self.items.append(item)
        return item

    def link_message_to_context(
        self,
        shop_id: str,
        conversation_id: str,
        from_message_id: str,
        to_context_item_id: str,
        relation_type: str,
        confidence: float = 0.9,
    ) -> ReferenceLink:
        if self._repo is not None:
            shop_uuid = _parse_uuid(shop_id)
            conv_uuid = _parse_uuid(conversation_id)
            msg_uuid = _parse_uuid(from_message_id)
            ctx_uuid = _parse_uuid(to_context_item_id)
            if shop_uuid is None or conv_uuid is None or msg_uuid is None or ctx_uuid is None:
                raise ValueError("invalid ids for reference link")
            row = ConversationReferenceLink(
                shop_id=shop_uuid,
                conversation_id=conv_uuid,
                from_message_id=msg_uuid,
                to_context_item_id=ctx_uuid,
                relation_type=relation_type,
                confidence=confidence,
            )
            self._repo.add_link(row)
            return ReferenceLink(
                shop_id=shop_id,
                conversation_id=conversation_id,
                from_message_id=from_message_id,
                to_context_item_id=to_context_item_id,
                relation_type=relation_type,
                confidence=confidence,
                id=str(row.id),
                created_at=row.created_at,
            )
        link = ReferenceLink(
            shop_id,
            conversation_id,
            from_message_id,
            to_context_item_id,
            relation_type,
            confidence,
        )
        self.links.append(link)
        return link

    def get_recent_context(
        self,
        conversation_id: str,
        limit: int = 10,
        shop_id: str | None = None,
    ) -> list[ContextItem]:
        if self._repo is not None and shop_id is not None:
            shop_uuid = _parse_uuid(shop_id)
            conv_uuid = _parse_uuid(conversation_id)
            if shop_uuid and conv_uuid:
                return [
                    _model_to_item(row)
                    for row in self._repo.list_recent(shop_uuid, conv_uuid, limit=limit)
                ]
        now = datetime.now(timezone.utc)
        rows = [
            i
            for i in self.items
            if i.conversation_id == conversation_id
            and (i.expires_at is None or i.expires_at > now)
        ]
        return sorted(rows, key=lambda i: i.created_at, reverse=True)[:limit]

    def get_last_product_list(self, conversation_id: str, shop_id: str | None = None) -> ContextItem | None:
        return next(
            (
                i
                for i in self.get_recent_context(conversation_id, 20, shop_id=shop_id)
                if i.item_type in {"product_list", "catalog_search_result"}
            ),
            None,
        )

    def get_active_product_context(
        self, conversation_id: str, shop_id: str | None = None
    ) -> ContextItem | None:
        return next(
            (
                i
                for i in self.get_recent_context(conversation_id, 20, shop_id=shop_id)
                if i.selected_product_id or i.candidate_product_ids_json
            ),
            None,
        )

    def resolve_reference(
        self, message: Any, conversation_id: str, shop_id: str | None = None
    ) -> ReferenceResolution:
        text = (
            getattr(message, "text", None)
            or (message.get("text") if isinstance(message, dict) else "")
            or ""
        ).lower()
        for token, index in sorted(ORDINALS.items(), key=lambda kv: len(kv[0]), reverse=True):
            has_token = (
                bool(re.search(rf"\b{re.escape(token)}\b", text))
                if token.isascii()
                else token in text
            )
            if has_token:
                lst = self.get_last_product_list(conversation_id, shop_id=shop_id)
                if lst and len(lst.candidate_product_ids_json) > index:
                    return ReferenceResolution(
                        lst.id,
                        lst.candidate_product_ids_json[index],
                        confidence=0.95,
                        reason="ordinal_product_list_selection",
                    )
        if any(w in text for w in REF_WORDS):
            active = self.get_active_product_context(conversation_id, shop_id=shop_id)
            if active:
                product_id = active.selected_product_id or (
                    active.candidate_product_ids_json[0]
                    if len(active.candidate_product_ids_json) == 1
                    else None
                )
                if product_id:
                    return ReferenceResolution(
                        active.id,
                        product_id,
                        active.selected_variant_id,
                        confidence=0.88,
                        reason="active_product_context",
                    )
                return ReferenceResolution(
                    active.id,
                    None,
                    confidence=0.6,
                    needs_clarification=True,
                    clarification_question="Which product do you mean?",
                    reason="ambiguous_active_context",
                )
        return ReferenceResolution(None, None)

    def expire_old_context(self, older_than_hours: int = 48, shop_id: str | None = None) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        if self._repo is not None and shop_id is not None:
            shop_uuid = _parse_uuid(shop_id)
            if shop_uuid:
                return self._repo.expire_stale(shop_uuid, cutoff)
        n = 0
        for item in self.items:
            if (
                item.expires_at is None
                and item.created_at < cutoff
                and item.item_type not in {"order_summary", "product_post", "product_card"}
            ):
                item.expires_at = datetime.now(timezone.utc)
                n += 1
        return n

    def explain_context_resolution(self, resolution: ReferenceResolution) -> dict[str, Any]:
        return resolution.__dict__


# Product terminology alias used by the Modira architecture docs.
ConversationContextGraph = ConversationContextService

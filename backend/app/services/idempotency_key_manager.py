from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.enums import (
    WebhookDedupeOutcome,
    WebhookProcessingStatus,
    WebhookProvider,
)
from app.domain.models import WebhookEvent
from app.integrations.redis_cache import RedisCacheService
from app.repositories.webhook_event_repository import WebhookEventRepository


class IdempotencyScope(str, Enum):
    WEBHOOK_MESSAGE = "webhook_message"
    ORDER_CREATE = "order_create"
    PAYMENT_CALLBACK = "payment_callback"
    RETRY_JOB = "retry_job"
    LLM_FALLBACK = "llm_fallback"


@dataclass(frozen=True)
class IdempotencyDecision:
    allowed: bool
    key: str
    reason: str
    existing_event_id: UUID | None = None


class IdempotencyKeyManager:
    """Global idempotency guard for all externally retried side effects."""

    def __init__(self, db: Session, cache: RedisCacheService | None = None) -> None:
        self.db = db
        self.cache = cache
        self.webhook_events = WebhookEventRepository(db)

    @staticmethod
    def build_key(
        scope: IdempotencyScope | str,
        *parts: Any,
        payload: dict[str, Any] | None = None,
    ) -> str:
        scope_value = scope.value if isinstance(scope, IdempotencyScope) else str(scope)
        stable_parts = [str(p) for p in parts if p is not None and str(p) != ""]
        if payload is not None:
            body = json.dumps(
                payload, sort_keys=True, separators=(",", ":"), default=str
            )
            stable_parts.append(hashlib.sha256(body.encode()).hexdigest())
        return f"{scope_value}:" + ":".join(stable_parts)

    def reserve_webhook(
        self,
        *,
        provider: WebhookProvider,
        idempotency_key: str,
        event_type: str,
        raw_payload: dict[str, Any],
        trace_id: str | None = None,
    ) -> IdempotencyDecision:
        if self.cache is not None and not self.cache.try_acquire_idempotency(
            idempotency_key
        ):
            return IdempotencyDecision(False, idempotency_key, "duplicate_redis")

        existing = self.webhook_events.get_by_idempotency_key(provider, idempotency_key)
        if existing is not None:
            return IdempotencyDecision(
                False, idempotency_key, "duplicate_db", existing.id
            )

        event = WebhookEvent(
            provider=provider,
            event_type=event_type,
            raw_payload=raw_payload,
            processing_status=WebhookProcessingStatus.RECEIVED,
            idempotency_key=idempotency_key,
            trace_id=trace_id,
            dedupe_outcome=WebhookDedupeOutcome.PROCESSED,
        )
        try:
            self.webhook_events.create(event)
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            return IdempotencyDecision(False, idempotency_key, "duplicate_integrity")
        return IdempotencyDecision(True, idempotency_key, "reserved", event.id)

    def assert_side_effect_key(self, scope: IdempotencyScope, key: str) -> None:
        if not key.startswith(f"{scope.value}:"):
            raise ValueError(f"idempotency key for {scope.value} is required")

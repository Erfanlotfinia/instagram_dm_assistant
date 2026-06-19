"""Legacy compatibility wrapper around canonical channel webhook ingestion."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app.domain.enums import ChannelProvider, WebhookDedupeOutcome, WebhookProcessingStatus, WebhookProvider
from app.domain.models import ChannelAccount, WebhookEvent
from app.repositories.instagram_account_repository import InstagramAccountRepository
from app.schemas.webhook import WebhookAckResponse, WebhookIgnoredResponse
from app.services.channel_webhook_ingestion_service import ChannelWebhookIngestionService
from app.services.legacy_channel_compat import get_instagram_channel_account_id


def compute_webhook_idempotency_key(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{hashlib.sha256(body.encode()).hexdigest()}"


class WebhookIngestionService:
    """Deprecated API that delegates to the one channel ingestion pipeline."""

    def __init__(self, db: Session, **_: Any) -> None:
        self.db = db

    def handle_instagram_payload(
        self, payload: dict[str, Any], raw_body: bytes | None = None
    ) -> WebhookAckResponse | WebhookIgnoredResponse:
        recipient_id = self._recipient_id(payload)
        legacy_account = (
            InstagramAccountRepository(self.db).get_by_ig_user_id(recipient_id)
            if recipient_id
            else None
        )
        if legacy_account is None:
            self._store_unmatched_webhook(payload)
            return WebhookAckResponse(dedupe_outcome=WebhookDedupeOutcome.IGNORED.value)
        channel_account_id = get_instagram_channel_account_id(self.db, legacy_account.id)
        account = self.db.get(ChannelAccount, channel_account_id)
        return ChannelWebhookIngestionService(self.db).handle_payload(
            ChannelProvider.INSTAGRAM,
            payload,
            shop_id=account.shop_id if account else None,
            channel_account_id=channel_account_id,
        )

    def _store_unmatched_webhook(self, payload: dict[str, Any]) -> None:
        webhook_key = compute_webhook_idempotency_key(payload)
        event = WebhookEvent(
            provider=WebhookProvider.INSTAGRAM,
            shop_id=None,
            event_type="instagram.webhook.received",
            raw_payload=payload,
            processing_status=WebhookProcessingStatus.RECEIVED,
            idempotency_key=webhook_key,
            dedupe_outcome=WebhookDedupeOutcome.IGNORED,
        )
        self.db.add(event)
        self.db.commit()

    @staticmethod
    def _recipient_id(payload: dict[str, Any]) -> str | None:
        for entry in payload.get("entry", []):
            for event in entry.get("messaging", []):
                recipient_id = (event.get("recipient") or {}).get("id")
                if recipient_id:
                    return str(recipient_id)
        return None

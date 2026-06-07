from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class ParsedInstagramMessage:
    recipient_id: str
    sender_id: str
    message_id: str
    text: str | None
    message_type: str
    attachment_url: str | None
    shared_post_url: str | None
    timestamp: datetime | None
    messaging_event: dict[str, Any]


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return None
    if numeric > 1_000_000_000_000:
        numeric = numeric // 1000
    return datetime.fromtimestamp(numeric, tz=UTC)


def _extract_attachment_urls(attachments: Any) -> tuple[str | None, str | None]:
    if not isinstance(attachments, list):
        return None, None

    attachment_url: str | None = None
    shared_post_url: str | None = None

    for item in attachments:
        if not isinstance(item, dict):
            continue
        payload = _safe_dict(item.get("payload"))
        item_type = _safe_str(item.get("type"))
        url = _safe_str(payload.get("url"))

        if item_type == "share" and url:
            shared_post_url = url
        elif url and attachment_url is None:
            attachment_url = url

    return attachment_url, shared_post_url


def _classify_message(message: dict[str, Any], attachment_url: str | None, shared_post_url: str | None) -> str:
    if shared_post_url:
        return "shared_post"
    if attachment_url or message.get("attachments"):
        return "attachment"
    return "text"


def parse_instagram_webhook_payload(payload: dict[str, Any]) -> list[ParsedInstagramMessage]:
    """Extract messaging events from a Meta Instagram webhook payload."""
    if not isinstance(payload, dict):
        return []

    if _safe_str(payload.get("object")) not in {"instagram", "page"}:
        return []

    entries = payload.get("entry")
    if not isinstance(entries, list):
        return []

    parsed: list[ParsedInstagramMessage] = []

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        messaging_events = entry.get("messaging")
        if not isinstance(messaging_events, list):
            continue

        for event in messaging_events:
            if not isinstance(event, dict):
                continue

            message = _safe_dict(event.get("message"))
            if not message:
                continue

            message_id = _safe_str(message.get("mid"))
            sender_id = _safe_str(_safe_dict(event.get("sender")).get("id"))
            recipient_id = _safe_str(_safe_dict(event.get("recipient")).get("id"))

            if not message_id or not sender_id or not recipient_id:
                continue

            attachment_url, shared_post_url = _extract_attachment_urls(message.get("attachments"))
            message_type = _classify_message(message, attachment_url, shared_post_url)

            parsed.append(
                ParsedInstagramMessage(
                    recipient_id=recipient_id,
                    sender_id=sender_id,
                    message_id=message_id,
                    text=_safe_str(message.get("text")),
                    message_type=message_type,
                    attachment_url=attachment_url,
                    shared_post_url=shared_post_url,
                    timestamp=_parse_timestamp(event.get("timestamp")),
                    messaging_event=event,
                )
            )

    return parsed

from __future__ import annotations

from enum import Enum, StrEnum


class WorkerRetryReason(StrEnum):
    CONVERSATION_LOCKED = "conversation_locked"
    PROCESSING_ERROR = "processing_error"


class WorkerDlqReason(StrEnum):
    INVALID_PAYLOAD = "invalid_payload"
    CONVERSATION_LOCK_EXHAUSTED = "conversation_lock_exhausted"
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"


class WebhookMetricResult(StrEnum):
    DUPLICATE = "duplicate"
    PROCESSED = "processed"
    IGNORED = "ignored"


class WebhookIgnoredReason(StrEnum):
    CHANNEL_ACCOUNT_NOT_FOUND = "channel_account_not_found"
    NO_CHANNEL_MESSAGES = "no_channel_messages"
    UNMATCHED_RECIPIENT = "unmatched_recipient"
    MESSAGE_DUPLICATE = "message_duplicate"


class HandoffMetricReason(StrEnum):
    POLICY = "policy"
    RISK = "risk"
    SOCIAL_ADMIN = "social_admin"
    OTHER = "other"


class ProcessedMessageStatus(StrEnum):
    SUCCESS = "success"


_UNKNOWN_PROVIDER = "unknown"


def normalize_provider(provider: str | Enum | None) -> str:
    if provider is None:
        return _UNKNOWN_PROVIDER
    value = provider.value if isinstance(provider, Enum) else str(provider)
    allowed = {"instagram", "whatsapp", "telegram", "bale", "rubika"}
    return value if value in allowed else _UNKNOWN_PROVIDER


def normalize_handoff_reason(reason: str | HandoffMetricReason | None) -> HandoffMetricReason:
    if isinstance(reason, HandoffMetricReason):
        return reason
    if reason is None:
        return HandoffMetricReason.OTHER
    lowered = reason.lower()
    if "social_admin" in lowered or "social admin" in lowered:
        return HandoffMetricReason.SOCIAL_ADMIN
    if "risk" in lowered:
        return HandoffMetricReason.RISK
    if any(token in lowered for token in ("policy", "handoff", "confidence", "intent", "pilot")):
        return HandoffMetricReason.POLICY
    return HandoffMetricReason.OTHER

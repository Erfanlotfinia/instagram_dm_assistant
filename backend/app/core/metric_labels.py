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
    FAILURE = "failure"
    UNKNOWN = "unknown"


_UNKNOWN_PROVIDER = "unknown"


def normalize_provider(provider: object | None) -> str:
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


def normalize_processed_message_status(
    status: ProcessedMessageStatus | str | None,
) -> ProcessedMessageStatus:
    if isinstance(status, ProcessedMessageStatus):
        return status
    if status is None:
        return ProcessedMessageStatus.SUCCESS
    lowered = str(status).lower()
    if lowered == ProcessedMessageStatus.SUCCESS.value:
        return ProcessedMessageStatus.SUCCESS
    if lowered in {"failure", "error", "failed"}:
        return ProcessedMessageStatus.FAILURE
    return ProcessedMessageStatus.UNKNOWN


_ALLOWED_AUTOMATIONS = {
    "catalog_resolver",
    "order_state",
    "handoff_gate",
    "social_admin",
}


def normalize_automation(automation: str | None) -> str:
    if automation is None:
        return "unknown"
    lowered = automation.lower()
    return lowered if lowered in _ALLOWED_AUTOMATIONS else "unknown"

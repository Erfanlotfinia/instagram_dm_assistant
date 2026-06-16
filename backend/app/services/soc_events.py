from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class DomainEventType(StrEnum):
    MESSAGE_RECEIVED = "message_received"
    SCENARIO_ROUTED = "scenario_routed"
    AUTOMATION_EXECUTED = "automation_executed"
    LLM_FALLBACK_CALLED = "llm_fallback_called"
    ORDER_CREATED = "order_created"
    PAYMENT_UPDATED = "payment_updated"
    INVENTORY_UPDATED = "inventory_updated"
    HANDOFF_TRIGGERED = "handoff_triggered"


@dataclass(frozen=True, slots=True)
class TenantScope:
    tenant_id: str
    shop_id: str

    def assert_matches(self, other: "TenantScope") -> None:
        if self != other:
            raise PermissionError("cross_tenant_event_access_blocked")


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_type: DomainEventType
    tenant_id: str
    shop_id: str
    conversation_id: str
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    causation_id: str | None = None
    event_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 1
    sequence: int | None = None
    replay: bool = False

    @property
    def partition_key(self) -> str:
        return f"{self.tenant_id}:{self.conversation_id}"

    @property
    def partition_id(self) -> int:
        digest = hashlib.sha256(self.partition_key.encode("utf-8")).hexdigest()
        return int(digest[:8], 16)

    def validate(self) -> None:
        if not self.tenant_id or not self.shop_id or not self.conversation_id:
            raise ValueError("tenant_id, shop_id, and conversation_id are required")
        json.dumps(self.payload, sort_keys=True, default=str)
        if (
            self.event_type
            in {
                DomainEventType.ORDER_CREATED,
                DomainEventType.PAYMENT_UPDATED,
                DomainEventType.INVENTORY_UPDATED,
            }
            and self.replay
        ):
            raise ValueError("side_effecting_events_are_forbidden_during_replay")

    def with_sequence(self, sequence: int) -> "DomainEvent":
        return DomainEvent(**{**asdict(self), "sequence": sequence})

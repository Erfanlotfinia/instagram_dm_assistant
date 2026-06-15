from __future__ import annotations

import heapq
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable, Protocol

from app.services.soc_events import DomainEvent, DomainEventType, TenantScope


class EventConsumer(Protocol):
    consumer_group: str
    handled_events: set[DomainEventType]

    def handle(self, event: DomainEvent) -> None: ...


@dataclass(slots=True)
class DeadLetterEntry:
    event: DomainEvent
    consumer_group: str
    reason: str
    attempts: int


@dataclass(slots=True)
class ConsumerState:
    consumer: EventConsumer
    offsets: dict[str, int] = field(default_factory=dict)
    processed: set[str] = field(default_factory=set)


class InMemoryKafkaBackbone:
    """Kafka-style ordered log used for local/dev and tests.

    The production adapter can map the same EventBus contract to Kafka or RabbitMQ.
    Ordering is enforced per tenant_id+conversation_id partition, while consumer
    groups keep independent offsets and idempotency state.
    """

    def __init__(
        self,
        partitions: int = 16,
        max_attempts: int = 3,
        backoff: Callable[[int], float] | None = None,
    ) -> None:
        self.partitions = partitions
        self.max_attempts = max_attempts
        self.backoff = backoff or (
            lambda attempt: min(60.0, 0.1 * (2 ** (attempt - 1)))
        )
        self._streams: dict[int, list[DomainEvent]] = defaultdict(list)
        self._sequence_by_key: dict[str, int] = defaultdict(int)
        self._consumers: dict[str, ConsumerState] = {}
        self.dlq: list[DeadLetterEntry] = []

    def publish(self, event: DomainEvent) -> DomainEvent:
        event.validate()
        sequence = self._sequence_by_key[event.partition_key] + 1
        self._sequence_by_key[event.partition_key] = sequence
        sequenced = event.with_sequence(sequence)
        self._streams[sequenced.partition_id % self.partitions].append(sequenced)
        return sequenced

    def subscribe(self, consumer: EventConsumer) -> None:
        self._consumers[consumer.consumer_group] = ConsumerState(consumer=consumer)

    def poll(
        self,
        consumer_group: str,
        *,
        tenant_scope: TenantScope | None = None,
        limit: int = 100,
    ) -> int:
        state = self._consumers[consumer_group]
        delivered = 0
        heads: list[tuple[int, int, int, DomainEvent]] = []
        for partition, events in self._streams.items():
            offset = state.offsets.get(str(partition), 0)
            if offset < len(events):
                event = events[offset]
                heapq.heappush(
                    heads,
                    (
                        (
                            event.event_time.timestamp_ns()
                            if hasattr(event.event_time, "timestamp_ns")
                            else int(event.event_time.timestamp() * 1e9)
                        ),
                        partition,
                        offset,
                        event,
                    ),
                )
        while heads and delivered < limit:
            _, partition, offset, event = heapq.heappop(heads)
            if event.event_id in state.processed:
                state.offsets[str(partition)] = offset + 1
            elif event.event_type in state.consumer.handled_events:
                if tenant_scope:
                    TenantScope(event.tenant_id, event.shop_id).assert_matches(
                        tenant_scope
                    )
                self._deliver(state, event)
                state.processed.add(event.event_id)
                state.offsets[str(partition)] = offset + 1
                delivered += 1
            else:
                state.offsets[str(partition)] = offset + 1
            next_offset = state.offsets[str(partition)]
            if next_offset < len(self._streams[partition]):
                nxt = self._streams[partition][next_offset]
                heapq.heappush(
                    heads,
                    (
                        int(nxt.event_time.timestamp() * 1e9),
                        partition,
                        next_offset,
                        nxt,
                    ),
                )
        return delivered

    def _deliver(self, state: ConsumerState, event: DomainEvent) -> None:
        attempts = 0
        while True:
            attempts += 1
            try:
                state.consumer.handle(event)
                return
            except Exception as exc:
                if attempts >= self.max_attempts:
                    self.dlq.append(
                        DeadLetterEntry(
                            event, state.consumer.consumer_group, str(exc), attempts
                        )
                    )
                    return
                time.sleep(self.backoff(attempts))

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter
from typing import Iterator
from uuid import UUID, uuid4


@dataclass
class ObservabilityService:
    """In-process metrics/tracing facade; production deployments can bridge it to Prometheus/OTel."""

    counters: Counter[str] = field(default_factory=Counter)
    spans: list[dict[str, object]] = field(default_factory=list)
    alerts: list[dict[str, object]] = field(default_factory=list)

    def increment(self, metric: str, amount: int = 1) -> None:
        self.counters[metric] += amount

    @contextmanager
    def trace(self, name: str, **attrs: object) -> Iterator[UUID]:
        trace_id = uuid4()
        started = perf_counter()
        try:
            yield trace_id
            status = "ok"
        except Exception:
            status = "error"
            self.increment("error_rate")
            raise
        finally:
            self.spans.append({"trace_id": str(trace_id), "name": name, "status": status, "duration_ms": int((perf_counter() - started) * 1000), **attrs})

    def alert(self, name: str, **attrs: object) -> None:
        self.alerts.append({"name": name, **attrs})
        self.increment(f"alerts.{name}")

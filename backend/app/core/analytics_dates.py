from __future__ import annotations

from datetime import datetime


def resolve_analytics_range(
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> tuple[datetime | None, datetime | None]:
    """Accept Sprint F date_from/date_to aliases alongside legacy start/end."""
    return date_from or start, date_to or end

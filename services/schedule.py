from datetime import datetime, timedelta
from typing import Protocol


class DueGroup(Protocol):
    next_digest_at: datetime | None


def is_group_due(group: DueGroup, now: datetime) -> bool:
    return group.next_digest_at is not None and group.next_digest_at <= now


def calculate_next_digest_at(now: datetime, interval_hours: int) -> datetime:
    return now + timedelta(hours=interval_hours)

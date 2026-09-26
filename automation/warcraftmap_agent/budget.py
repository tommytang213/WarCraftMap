from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def recent_invocations(invocations: Iterable[str], now: datetime) -> list[str]:
    cutoff = now.astimezone(timezone.utc) - timedelta(days=7)
    return [value for value in invocations if parse_timestamp(value) > cutoff]


def budget_available(
    invocations: Iterable[str], now: datetime, max_daily: int, max_weekly: int
) -> tuple[bool, str]:
    recent = recent_invocations(invocations, now)
    today = now.astimezone(timezone.utc).date()
    daily = sum(parse_timestamp(value).date() == today for value in recent)
    if daily >= max_daily:
        return False, f"daily Codex budget exhausted ({daily}/{max_daily})"
    if len(recent) >= max_weekly:
        return False, f"rolling seven-day Codex budget exhausted ({len(recent)}/{max_weekly})"
    return True, "budget available"


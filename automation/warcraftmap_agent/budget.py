from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Mapping, Any


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def recent_runs(runs: Iterable[Mapping[str, Any]], now: datetime) -> list[dict[str, Any]]:
    cutoff = now.astimezone(timezone.utc) - timedelta(days=7)
    recent: list[dict[str, Any]] = []
    for item in runs:
        timestamp = item.get("timestamp")
        if not isinstance(timestamp, str):
            continue
        if parse_timestamp(timestamp) > cutoff:
            recent.append(dict(item))
    return recent


def usage_summary(runs: Iterable[Mapping[str, Any]], now: datetime) -> dict[str, int]:
    recent = recent_runs(runs, now)
    today = now.astimezone(timezone.utc).date()
    daily_runs = [item for item in recent if parse_timestamp(str(item["timestamp"])).date() == today]

    def known_tokens(items: Iterable[Mapping[str, Any]]) -> int:
        total = 0
        for item in items:
            value = item.get("tokens")
            if isinstance(value, int) and value >= 0:
                total += value
        return total

    return {
        "daily_tokens": known_tokens(daily_runs),
        "weekly_tokens": known_tokens(recent),
        "daily_runs": len(daily_runs),
        "weekly_runs": len(recent),
        "daily_unknown_runs": sum(item.get("tokens") is None for item in daily_runs),
        "weekly_unknown_runs": sum(item.get("tokens") is None for item in recent),
    }


def budget_available(
    runs: Iterable[Mapping[str, Any]],
    now: datetime,
    max_daily_tokens: int,
    max_weekly_tokens: int,
    max_daily_runs: int,
    max_weekly_runs: int,
) -> tuple[bool, str]:
    summary = usage_summary(runs, now)

    if summary["daily_tokens"] >= max_daily_tokens:
        return False, (
            "daily Codex token budget exhausted "
            f"({summary['daily_tokens']:,}/{max_daily_tokens:,})"
        )
    if summary["weekly_tokens"] >= max_weekly_tokens:
        return False, (
            "rolling seven-day Codex token budget exhausted "
            f"({summary['weekly_tokens']:,}/{max_weekly_tokens:,})"
        )
    if summary["daily_runs"] >= max_daily_runs:
        return False, (
            "daily emergency Codex run cap exhausted "
            f"({summary['daily_runs']}/{max_daily_runs})"
        )
    if summary["weekly_runs"] >= max_weekly_runs:
        return False, (
            "rolling seven-day emergency Codex run cap exhausted "
            f"({summary['weekly_runs']}/{max_weekly_runs})"
        )

    unknown = summary["daily_unknown_runs"]
    suffix = f", telemetry-missing runs today {unknown}" if unknown else ""
    return True, (
        "budget available "
        f"(today {summary['daily_tokens']:,}/{max_daily_tokens:,} tokens, "
        f"7d {summary['weekly_tokens']:,}/{max_weekly_tokens:,} tokens; "
        f"runs {summary['daily_runs']}/{max_daily_runs} today, "
        f"{summary['weekly_runs']}/{max_weekly_runs} in 7d{suffix})"
    )

"""Conservative integration policy and durable, per-issue measurements.

The controller remains the only writer. A slot is a claim on unpublished work,
including failed/interrupted work; it is never evicted to make room in the queue.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any


MAX_STAGED_DEPTH = 1
MAX_OPEN_PRS = 2
STAGE_TIMEOUT_HOURS = 24


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def seconds(start: str, end: str) -> float:
    return max(0.0, (datetime.fromisoformat(end.replace("Z", "+00:00")) -
                     datetime.fromisoformat(start.replace("Z", "+00:00"))).total_seconds())


def paths(values: list[str] | None) -> set[str] | None:
    """Reject incomplete/ambiguous inventories; comparisons are case insensitive."""
    if not values:
        return None
    result = set()
    for value in values:
        if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
            return None
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            return None
        result.add(str(path).casefold())
    return result


def isolation_domain(path: str) -> str:
    # Only these repository boundaries authorize independent CI. In particular,
    # two campaign changes share runtime/bootstrap/save/report inputs even when
    # their literal filenames differ. Build tooling and unknown paths are global.
    if path in {
        "automation/warcraftmap_agent/budget.py", "automation/tests/test_budget.py",
        "automation/warcraftmap_agent/self_update.py", "automation/tests/test_self_update.py",
        "automation/readme.md", "automation/warcraftmap-agent.env.example",
    }:
        return "controller"
    if path.startswith("maps/historical-world-rpg/"):
        return "campaign"
    return "global"


def classify(candidate: list[str] | None, predecessor: list[str] | None) -> dict[str, Any]:
    ours, theirs = paths(candidate), paths(predecessor)
    if ours is None or theirs is None:
        return {"independent": False, "overlaps": [], "reason": "unknown file inventory"}
    overlaps = sorted(ours & theirs)
    if overlaps:
        return {"independent": False, "overlaps": overlaps, "reason": "shared paths"}
    own_domains = {isolation_domain(path) for path in ours}
    other_domains = {isolation_domain(path) for path in theirs}
    independent = ("global" not in own_domains | other_domains and
                   not own_domains & other_domains)
    return {"independent": independent, "overlaps": [],
            "reason": "separate controller/campaign boundaries" if independent else
                      "shared or unclassified source/evidence inputs"}


def staged_numbers(state: dict) -> list[int]:
    return [int(number) for number, record in state["issues"].items()
            if record.get("stage") and not record.get("pr") and record.get("status") != "merged"]


def metrics(record: dict) -> dict:
    return record.setdefault("metrics", {
        "schema_version": 1, "first_validation_base_sha": None,
        "overlap_observations": [], "conflicts": [], "validations": [],
        "codex_runs": {}, "ci_runs": {}, "wall_seconds": {},
    })


def phase(record: dict, name: str, now: str | None = None) -> None:
    now = now or stamp()
    data = metrics(record)
    previous = data.get("phase")
    if previous and data.get("phase_started_at"):
        totals = data["wall_seconds"]
        totals[previous] = totals.get(previous, 0.0) + seconds(data["phase_started_at"], now)
    data.update(phase=name, phase_started_at=now)


def observe(record: dict, pr: dict, decision: dict) -> None:
    entry = {"pr": pr["number"], "head_sha": pr.get("headRefOid"), **decision}
    observations = metrics(record)["overlap_observations"]
    if entry not in observations:
        observations.append(entry)


def record_runs(state: dict) -> None:
    """Retain issue telemetry even after the global rolling quota window expires."""
    for run in state.get("runs", []):
        number = str(run.get("issue"))
        if number not in state["issues"]:
            continue
        key = run.get("id") or run["timestamp"]
        metrics(state["issues"][number])["codex_runs"][key] = dict(run)


def summary(record: dict) -> dict:
    data = metrics(record)
    codex = list(data["codex_runs"].values())
    ci = list(data["ci_runs"].values())
    ids = {row["id"] for row in ci}
    result = {key: value for key, value in data.items() if key not in {"codex_runs", "ci_runs"}}
    result["wall_seconds"] = dict(data["wall_seconds"])
    if data.get("phase") and data.get("phase_started_at") and data["phase"] != "merged":
        name = data["phase"]
        result["wall_seconds"][name] = result["wall_seconds"].get(name, 0.0) + seconds(data["phase_started_at"], stamp())
    result.update(
        conflict_count=len(data["conflicts"]),
        codex_tokens=sum(row.get("tokens") or 0 for row in codex),
        codex_unknown_runs=sum(row.get("tokens") is None for row in codex),
        codex_run_count=len(codex),
        ci_run_count=len(ids) if data.get("ci_observed_at") else None,
        ci_head_updates=max(0, len({row["head_sha"] for row in ci if row.get("head_sha")}) - 1)
                        if data.get("ci_observed_at") else None,
        ci_reruns=sum(max(row["attempt"] for row in ci if row["id"] == ident) - 1
                      for ident in ids) if data.get("ci_observed_at") else None,
        ci_elapsed_seconds=sum(row.get("seconds") or 0 for row in ci),
        ci_incomplete_attempts=sum(row.get("seconds") is None for row in ci),
    )
    return result

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import integration
from .budget import budget_available, recent_runs, usage_summary
from .closure import (APPROVED_NATIVE_LAUNCH_DIAGNOSTIC, Closure, REPORTS,
                      build_closure, is_open, marked_keys)


READY = re.compile(r"^\[agent-ready\]\s+", re.IGNORECASE)
NEEDS_DESIGN = re.compile(r"^\[needs-design\]\s+", re.IGNORECASE)
PLANNED = re.compile(r"^\[planned\]\s+", re.IGNORECASE)
PLANNED_PHASE = re.compile(r"^\[planned\]\s+Phase\s+(\d+)\s*:", re.IGNORECASE)
DEPENDENCY = re.compile(r"(?im)^\s*Depends on:\s*#(\d+)\b")
QUEUE_REFILL_THRESHOLD = 3
QUEUE_TARGET = 10
# Historical CI attribution can remain permanently incomplete. Limit its
# housekeeping so it cannot starve issue selection and new Codex work.
MERGED_METRICS_REFRESH_HOURS = 24
MERGED_METRICS_PER_WAKE = 2
_worker_lock = None


def lock_fds() -> tuple[int, ...]:
    # Long-running children retain the same flock if the controller crashes.
    # A restarted controller cannot write their worktrees or start another run.
    return (_worker_lock.fileno(),) if _worker_lock is not None and not _worker_lock.closed else ()


@dataclass
class Config:
    repo_root: Path
    state_dir: Path
    model: str = "gpt-5.6-sol"
    reasoning_effort: str = ""
    max_daily_tokens: int = 100_000_000
    max_weekly_tokens: int = 500_000_000
    max_daily_runs: int = 10
    max_weekly_runs: int = 50
    timeout_minutes: int = 45
    max_attempts: int = 3
    max_validation_repair_attempts: int = 5
    max_ci_repair_attempts: int = 5
    # Direct/test construction retains the legacy per-issue budget. make_config
    # supplies the independently configurable production default (5).
    max_conflict_attempts: int = 3
    checks_command: str = "./automation/run_checks.sh"
    issue_limit: int = 100
    design_notification_command: str = ""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def load_env(path: Path) -> dict[str, str]:
    """Read a deliberately small KEY=VALUE format without executing shell code."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Z][A-Z0-9_]*)=(.*)", line)
        if not match:
            raise ValueError(f"{path}:{number}: expected KEY=VALUE")
        key, value = match.groups()
        try:
            parts = shlex.split(value, posix=True)
        except ValueError as exc:
            raise ValueError(f"{path}:{number}: {exc}") from exc
        if len(parts) > 1:
            raise ValueError(f"{path}:{number}: value must be one shell word (quote spaces)")
        values[key] = parts[0] if parts else ""
    return values


def positive_int(values: dict[str, str], key: str, default: int) -> int:
    value = int(values.get(key, default))
    if value < 1:
        raise ValueError(f"{key} must be at least 1")
    return value


def make_config(repo_root: Path, env_path: Path) -> Config:
    values = load_env(env_path)
    reasoning_effort = values.get(
        "WARCRAFTMAP_AGENT_REASONING_EFFORT", ""
    ).lower()

    if reasoning_effort and reasoning_effort not in {
        "low", "medium", "high", "xhigh", "max"
    }:
        raise ValueError(
            "WARCRAFTMAP_AGENT_REASONING_EFFORT must be "
            "low, medium, high, xhigh, or max"
        )

    state = Path(
        values.get(
            "WARCRAFTMAP_AGENT_STATE_DIR",
            "~/.local/state/warcraftmap-agent",
        )
    ).expanduser()
    return Config(
        repo_root=repo_root.resolve(),
        state_dir=state.resolve(),
        model=values.get("WARCRAFTMAP_AGENT_MODEL", "gpt-5.6-sol"),
        reasoning_effort=reasoning_effort,
        max_daily_tokens=positive_int(values, "WARCRAFTMAP_AGENT_MAX_DAILY_TOKENS", 100_000_000),
        max_weekly_tokens=positive_int(values, "WARCRAFTMAP_AGENT_MAX_WEEKLY_TOKENS", 500_000_000),
        max_daily_runs=positive_int(values, "WARCRAFTMAP_AGENT_MAX_DAILY_RUNS", 10),
        max_weekly_runs=positive_int(values, "WARCRAFTMAP_AGENT_MAX_WEEKLY_RUNS", 50),
        timeout_minutes=positive_int(values, "WARCRAFTMAP_AGENT_TIMEOUT_MINUTES", 45),
        max_attempts=positive_int(values, "WARCRAFTMAP_AGENT_MAX_ATTEMPTS_PER_ISSUE", 3),
        max_validation_repair_attempts=positive_int(values, "WARCRAFTMAP_AGENT_MAX_VALIDATION_REPAIR_ATTEMPTS", 5),
        max_ci_repair_attempts=positive_int(values, "WARCRAFTMAP_AGENT_MAX_CI_REPAIR_ATTEMPTS", 5),
        max_conflict_attempts=positive_int(values, "WARCRAFTMAP_AGENT_MAX_CONFLICT_REPAIR_ATTEMPTS", 5),
        checks_command=values.get("WARCRAFTMAP_AGENT_CHECKS_COMMAND", "./automation/run_checks.sh"),
        issue_limit=positive_int(values, "WARCRAFTMAP_AGENT_ISSUE_LIMIT", 100),
        design_notification_command=values.get("WARCRAFTMAP_AGENT_DESIGN_NOTIFICATION_COMMAND", ""),
    )


def run(args: list[str], *, cwd: Path, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout,
                            pass_fds=lock_fds())
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"command failed ({result.returncode}): {shlex.join(args)}\n{detail}")
    return result


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 3, "runs": [], "issues": {}}

    data = json.loads(path.read_text(encoding="utf-8"))
    version = data.get("version")

    if version == 1:
        # v1 stored only invocation timestamps. Preserve them as telemetry-missing
        # runs so the emergency run caps still account for old activity.
        data = {
            "version": 2,
            "runs": [
                {
                    "timestamp": timestamp,
                    "tokens": None,
                    "telemetry": "legacy_missing",
                    "issue": None,
                }
                for timestamp in data.get("invocations", [])
            ],
            "issues": data.get("issues", {}),
        }
    elif version not in {2, 3}:
        raise ValueError("unsupported worker state version")

    # v3 adds durable integration claims and validation receipts. Older workers
    # reject v3 instead of silently ignoring an unpublished staging reservation.
    data["version"] = 3
    data.setdefault("runs", [])
    data.setdefault("issues", {})
    return data


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix="state.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(state, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def gh_json(repo: Path, args: list[str]) -> Any:
    result = run(["gh", *args], cwd=repo, timeout=120)
    if args[0] == "api" and "--paginate" in args:
        # gh 2.45 has --paginate but no --slurp. Decode its consecutive JSON
        # documents without dropping pages or requiring a CLI upgrade.
        remaining = result.stdout.lstrip()
        pages = []
        decoder = json.JSONDecoder()
        while remaining:
            page, end = decoder.raw_decode(remaining)
            pages.append(page)
            remaining = remaining[end:].lstrip()
        if not pages:
            raise ValueError("GitHub returned no paginated response")
        return pages
    return json.loads(result.stdout)


def remote_branch_oid(repo: Path, branch: str) -> str:
    """Return the current origin branch OID without mutating the checkout."""
    if not branch:
        return ""
    result = run(
        ["git", "ls-remote", "--exit-code", "origin", f"refs/heads/{branch}"],
        cwd=repo,
        check=False,
    )
    if result.returncode == 2:
        return ""
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"could not resolve origin/{branch}: {detail}")
    line = result.stdout.strip().splitlines()
    if not line:
        return ""
    return line[0].split()[0]


def list_issues(config: Config) -> list[dict[str, Any]]:
    issues = gh_json(config.repo_root, ["issue", "list", "--state", "open", "--limit", str(config.issue_limit), "--json", "number,title,body,url,createdAt"])
    return sorted((item for item in issues if READY.match(item["title"])), key=lambda item: (item["createdAt"], item["number"]))


def list_needs_design_issues(config: Config) -> list[dict[str, Any]]:
    issues = gh_json(
        config.repo_root,
        ["issue", "list", "--state", "open", "--limit", str(config.issue_limit), "--json", "number,title,body,url,createdAt"],
    )
    return sorted(
        (item for item in issues if NEEDS_DESIGN.match(item["title"])),
        key=lambda item: (item["createdAt"], item["number"]),
    )


def list_planned_issues(config: Config) -> list[dict[str, Any]]:
    """Return open roadmap reservations, which are never implementation work."""
    issues = gh_json(
        config.repo_root,
        ["issue", "list", "--state", "open", "--limit", str(config.issue_limit), "--json", "number,title,body,url,createdAt"],
    )
    return sorted(
        (item for item in issues if PLANNED.match(item["title"])),
        key=lambda item: (item["createdAt"], item["number"]),
    )


def roadmap_phase_complete(roadmap: str, phase: int) -> bool:
    """Use the checkboxes in one ROADMAP phase as its authoritative completion gate."""
    heading = re.compile(rf"(?m)^##\s+Phase\s+{phase}\b.*$")
    match = heading.search(roadmap)
    if not match:
        return False
    next_heading = re.search(r"(?m)^##\s+Phase\s+\d+\b.*$", roadmap[match.end():])
    section = roadmap[match.end():match.end() + next_heading.start()] if next_heading else roadmap[match.end():]
    boxes = re.findall(r"(?m)^\s*-\s+\[([ xX])\]", section)
    if boxes:
        return all(box.casefold() == "x" for box in boxes)
    return bool(re.search(r"(?im)^\s*Status:\s*complete\s*\.?\s*$", section))


def roadmap_path(repo_root: Path) -> Path:
    candidates = sorted(repo_root.glob("**/docs/ROADMAP.md"))
    if len(candidates) != 1:
        raise RuntimeError(f"expected exactly one authoritative docs/ROADMAP.md, found {len(candidates)}")
    return candidates[0]


def planned_issue_phase(issue: dict[str, Any]) -> int | None:
    match = PLANNED_PHASE.match(str(issue.get("title", "")))
    return int(match.group(1)) if match else None


def planned_dependency_numbers(issue: dict[str, Any]) -> set[int]:
    return {int(number) for number in DEPENDENCY.findall(str(issue.get("body") or ""))}


def eligible_planned_issues(
    planned: list[dict[str, Any]], roadmap: str, dependency_states: dict[int, str],
    closure: Closure | None = None,
) -> list[dict[str, Any]]:
    """Find reservations whose preceding phase and explicit dependencies are complete."""
    # Roadmap checkboxes and closed issues never substitute for release evidence.
    if closure is None or closure.active:
        return []
    eligible = []
    for issue in planned:
        phase = planned_issue_phase(issue)
        if phase is None or phase <= 0 or not roadmap_phase_complete(roadmap, phase - 1):
            continue
        dependencies = planned_dependency_numbers(issue)
        if any(dependency_states.get(number, "OPEN").upper() != "CLOSED" for number in dependencies):
            continue
        eligible.append(issue)
    return eligible


def promote_planned_issues(config: Config, dry_run: bool = False, closure: Closure | None = None) -> list[dict[str, Any]]:
    """Promote eligible existing issues in place and return those issues."""
    if closure is None:
        context = planning_context(config)
        closure = context["closure"]
    if closure.active:
        return []
    planned = list_planned_issues(config)
    dependency_states: dict[int, str] = {}
    for number in sorted({number for issue in planned for number in planned_dependency_numbers(issue)}):
        try:
            view = gh_json(config.repo_root, ["issue", "view", str(number), "--json", "state"])
            dependency_states[number] = str(view.get("state", "OPEN"))
        except RuntimeError:
            # An inaccessible or invalid dependency is not evidence that it is complete.
            dependency_states[number] = "OPEN"
    eligible = eligible_planned_issues(
        planned, roadmap_path(config.repo_root).read_text(encoding="utf-8"), dependency_states, closure,
    )
    if dry_run:
        return eligible
    promoted = []
    for issue in eligible:
        latest = Closure(closure.revision, closure.fresh, closure.blockers,
                         list_history(config, "issue"), list_history(config, "pr"), closure.reports)
        # History refreshes and preceding promotions take time. Recheck main
        # after those operations for every mutation, not once for the batch.
        if latest.active or remote_branch_oid(config.repo_root, default_branch(config.repo_root)) != closure.revision:
            break
        title = PLANNED.sub("", issue["title"]).strip()
        run(["gh", "issue", "edit", str(issue["number"]), "--title", f"[agent-ready] {title}"], cwd=config.repo_root)
        promoted.append(issue)
    return promoted


def queue_refill_count(open_ready_count: int, design_blocked: bool = False) -> int:
    """Return the bounded number of issues needed to maintain the ready buffer."""
    # A design blocker affects its dependants, not the whole queue. The second
    # argument is retained for compatibility with callers of the old gate.
    return QUEUE_TARGET - open_ready_count if open_ready_count < QUEUE_REFILL_THRESHOLD else 0


def normalized_work_title(title: str) -> str:
    title = READY.sub("", title.strip())
    title = NEEDS_DESIGN.sub("", title)
    title = PLANNED.sub("", title)
    return re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip()


def decision_question(body: str) -> str:
    """Return only the first decision-question block from an issue body.

    Planner/issue edits can accidentally duplicate the Decision required
    section. Treat only the first paragraph after the first marker as the
    canonical question so repeated headings cannot defeat duplicate detection.
    """
    marker = re.search(r"(?im)^## Decision required\s*$", body)
    if not marker:
        return ""
    remainder = body[marker.end():].lstrip()
    if not remainder:
        return ""
    next_heading = re.search(r"(?m)^#{1,6}\s+\S.*$", remainder)
    if next_heading:
        remainder = remainder[:next_heading.start()]
    return re.split(r"\n\s*\n", remainder, maxsplit=1)[0].strip()


def normalized_question(question: str) -> str:
    return re.sub(r"\s+", " ", question.casefold()).strip()


def prepare_plan_items(
    plan: dict[str, Any], existing_titles: list[str], limit: int,
    existing_questions: list[str] | None = None,
    closure: Closure | None = None,
) -> list[dict[str, str]]:
    """Validate/deduplicate a planner result while preserving roadmap order."""
    # Response-format JSON Schema deliberately uses only Codex-supported
    # keywords. Enforce maxItems and uniqueItems here rather than asking the
    # model API to accept unsupported schema constraints (HTTP 400).
    rows = plan.get("issues", [])
    if not isinstance(rows, list) or len(rows) > 10:
        raise ValueError("planner may return at most ten issues")
    for raw in rows:
        if not isinstance(raw, dict):
            raise ValueError("planner issues must be objects")
        blocker_keys = raw.get("blocker_keys", [])
        if (not isinstance(blocker_keys, list) or len(blocker_keys) > 4
                or any(not isinstance(key, str) for key in blocker_keys)
                or len(set(blocker_keys)) != len(blocker_keys)):
            raise ValueError("planner blocker_keys must contain at most four unique string IDs")
    if plan.get("outcome") == "exhausted":
        if closure is not None and closure.active:
            raise ValueError("exhausted is forbidden while release closure is unresolved")
        return []
    seen = {normalized_work_title(title) for title in existing_titles}
    seen_questions = {normalized_question(question) for question in (existing_questions or []) if question}
    prepared: list[dict[str, str]] = []
    design_seen = False
    claimed: set[str] = set()
    for raw in rows:
        if len(prepared) >= limit:
            break
        kind = raw.get("kind")
        keys = set(raw.get("blocker_keys", []))
        if closure is not None and closure.active:
            if not keys or not keys <= set(closure.actionable[:limit]):
                raise ValueError("closure plans must address actionable blockers before optional expansion")
            if len(keys) > 4:
                raise ValueError("split closure work into implementation-sized repairs (at most four blocker identities)")
            if keys & claimed:
                continue
        elif keys:
            raise ValueError("plan names blockers absent from the current closure queue")
        clean_title = READY.sub("", NEEDS_DESIGN.sub("", PLANNED.sub("", str(raw.get("title", "")).strip()))).strip()
        key = normalized_work_title(clean_title)
        if not clean_title or not key or key in seen:
            continue
        seen.add(key)
        body = re.sub(r"(?m)^Closure (?:blocker|revision):[^\n]*\n?", "", str(raw.get("body", ""))).strip()
        # The owner has delegated routine research gameplay tuning. Missing
        # typed research consumers must become implementation work, not one
        # owner-facing design question per catalog unlock.
        delegated_research = (
            closure is not None and closure.active and bool(keys)
            and all(key.startswith("release:RESEARCH-UNBOUND-") for key in keys)
        )
        if delegated_research and kind == "needs-design":
            kind = "agent-ready"
            clean_title = re.sub(r"(?i)^specify\b", "Implement", clean_title)
            body = (
                "Owner-approved design delegation: implement the researched "
                "typed unlock gameplay consumers as reusable scenario-driven "
                "mechanisms. Use docs/HISTORICAL_BALANCE_AND_RESEARCH_EFFECTS.md "
                "and scenario/progression/gameplay-effect-design.json, the "
                "existing research catalogue, historical era, economy, "
                "eligible recipients and configured costs. Choose modest, "
                "tunable, historically plausible initial values from the "
                "approved domain ranges for effects not explicitly listed. "
                "Do not fabricate free troops, gold, food or buildings; do "
                "not hardcode campaign-specific names into shared code. "
                "Keep the original unbound audit findings until executed. "
                "No further player design question is required for ordinary "
                "modifier values, recipient conditions, or existing unlock "
                "actions.\n\n"
                "## Acceptance criteria\n"
                "- Implement actual production consumer(s) for the linked "
                "research-unbound IDs, including controller/category/era "
                "filters, costs/eligibility, source-aware stacking and "
                "player-visible previews.\n"
                "- Preserve research costs, prerequisites, supported saves, "
                "AI/player parity, legitimate historical asymmetry and "
                "viable weaker-country routes. Reconstruct all derived "
                "effects without duplicate grants on map/load/control "
                "changes.\n\n"
                "## Automated validation\n"
                "- Run registered actions/production callbacks for each "
                "eligible and ineligible condition with deterministic "
                "headless plus pinned Wurst evidence, negative stacking "
                "tests, save/load, rollback and abstract/live parity.\n"
                "- Regenerate current-main release, runtime and requirement "
                "audits. Do not claim native Warcraft launch or waive #438.\n"
            )
        if keys and closure is not None:
            body += "\n\n## Closure findings\n\n"
            for blocker_key in sorted(keys):
                finding = closure.blockers[blocker_key]
                body += f"- {blocker_key}: {finding.title}\n"
                body += "  Audits: " + ", ".join(finding.reports) + "\n"
            body += "\n\n" + "\n".join(f"Closure blocker: {key}" for key in sorted(keys))
            body += f"\nClosure revision: {closure.revision}\n\n"
            body += "After merge, regenerate release-blocker, runtime-acceptance and requirement-traceability audits on the new main revision. A closed issue or merged PR does not establish blocker closure.\n"
        if kind == "needs-design":
            question = str(raw.get("question", "")).strip()
            if not question or question.count("?") != 1:
                raise ValueError("a needs-design plan item must contain one exact question")
            question_key = normalized_question(question)
            if question_key in seen_questions:
                continue
            seen_questions.add(question_key)
            design_seen = True
            prepared.append({"title": f"[needs-design] {clean_title}", "body": body + "\n\n## Decision required\n\n" + question, "question": question})
            claimed.update(keys)
            continue
        if kind != "agent-ready":
            raise ValueError(f"unsupported planned issue kind: {kind!r}")
        if design_seen and "independent of" not in body.casefold():
            continue
        if "acceptance criteria" not in body.casefold() or "automated validation" not in body.casefold():
            raise ValueError("agent-ready plan items require acceptance criteria and automated validation")
        prepared.append({"title": f"[agent-ready] {clean_title}", "body": body, "question": ""})
        claimed.update(keys)
    return prepared


def legacy_pr_history(config: Config) -> list[dict[str, Any]]:
    """Read all PRs via GraphQL when gh's --json lacks closing issue links.

    Ubuntu's older gh releases do not expose closingIssuesReferences in
    `gh pr list --json`. It is vital for dependency gating: omitting it would
    let a manually closed issue conceal a still-open implementing PR.
    """
    repo = gh_json(config.repo_root, ["repo", "view", "--json", "nameWithOwner"])
    full_name = str(repo.get("nameWithOwner") or "")
    if full_name.count("/") != 1 or not all(full_name.split("/")):
        raise RuntimeError("cannot identify repository for complete PR history")
    owner, name = full_name.split("/", 1)
    query = """query($owner: String!, $name: String!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        pullRequests(first: 100, after: $cursor, orderBy: {field: CREATED_AT, direction: ASC}) {
          nodes {
            number title body state url createdAt closedAt mergedAt headRefName headRefOid
            mergeCommit { oid }
            closingIssuesReferences(first: 25) {
              nodes { number }
              pageInfo { hasNextPage }
            }
          }
          pageInfo { hasNextPage endCursor }
        }
      }
    }"""
    rows: list[dict[str, Any]] = []
    seen_numbers: set[int] = set()
    seen_cursors: set[str] = set()
    cursor: str | None = None
    while True:
        args = ["api", "graphql", "-f", f"query={query}",
                "-F", f"owner={owner}", "-F", f"name={name}"]
        if cursor is not None:
            args.extend(["-F", f"cursor={cursor}"])
        response = gh_json(config.repo_root, args)
        if not isinstance(response, dict) or response.get("errors"):
            raise RuntimeError("GitHub returned a failed or partial PR history query")
        try:
            collection = response["data"]["repository"]["pullRequests"]
            nodes = collection["nodes"]
            page = collection["pageInfo"]
        except (KeyError, TypeError) as exc:
            raise RuntimeError("GitHub returned incomplete PR history data") from exc
        if not isinstance(nodes, list) or not isinstance(page, dict):
            raise RuntimeError("GitHub returned malformed PR history pagination")
        for row in nodes:
            if not isinstance(row, dict) or type(row.get("number")) is not int:
                raise RuntimeError("GitHub returned malformed PR history entry")
            number = row["number"]
            refs = row.get("closingIssuesReferences")
            if (number in seen_numbers or not isinstance(refs, dict)
                    or not isinstance(refs.get("nodes"), list)
                    or not isinstance(refs.get("pageInfo"), dict)
                    or refs["pageInfo"].get("hasNextPage") is not False):
                # Never accept a truncated closing-issue association or
                # a repeated page as evidence that a dependency was merged.
                raise RuntimeError(f"GitHub returned incomplete closing references for PR #{number}")
            seen_numbers.add(number)
            rows.append({**row, "closingIssuesReferences": refs["nodes"]})
        if page.get("hasNextPage") is False:
            return rows
        next_cursor = page.get("endCursor")
        if (page.get("hasNextPage") is not True or not isinstance(next_cursor, str)
                or not next_cursor or next_cursor in seen_cursors or not nodes):
            raise RuntimeError("GitHub PR history pagination failed or repeated a cursor")
        seen_cursors.add(next_cursor)
        cursor = next_cursor


def list_history(config: Config, kind: str) -> list[dict[str, Any]]:
    """Read complete history, growing gh's limit until no entries are omitted."""
    fields = "number,title,body,state,url,createdAt,closedAt"
    if kind == "pr":
        fields += ",mergedAt,mergeCommit,closingIssuesReferences,headRefName,headRefOid"
    limit = max(config.issue_limit, 100)
    while True:
        try:
            rows = gh_json(config.repo_root, [kind, "list", "--state", "all",
                                               "--limit", str(limit), "--json", fields])
        except RuntimeError as exc:
            message = str(exc)
            if (kind != "pr" or not re.search(
                r"(?i)(?:unknown|invalid|unsupported)\s+JSON\s+field:[^\n]*closingIssuesReferences",
                message,
            )):
                raise
            # Only this known gh CLI schema mismatch authorizes the fallback.
            # Network/authentication problems and unrelated bad fields remain
            # fatal instead of being mistaken for an empty history.
            return legacy_pr_history(config)
        if len(rows) < limit:
            return rows
        limit *= 2


def read_closure(config: Config, issues: list[dict], prs: list[dict]) -> Closure:
    project = roadmap_path(config.repo_root).parent.parent
    bundle: dict[str, Any] = {"reports": {}}
    # Read saved findings even if regeneration cannot run. Missing/old PASS
    # reports cannot authorize ordinary planning or release promotion.
    for name, relative in REPORTS.items():
        try:
            bundle["reports"][name] = {"recorded": json.loads((project / relative).read_text())}
        except (OSError, ValueError):
            bundle["reports"][name] = {}
    revision = remote_branch_oid(config.repo_root, default_branch(config.repo_root))
    head = run(["git", "rev-parse", "HEAD"], cwd=config.repo_root).stdout.strip()
    status = run(["git", "status", "--porcelain"], cwd=config.repo_root).stdout.strip()
    current = bool(revision) and revision == head and not status
    if current:
        try:
            generated = run([sys.executable, str(project / "tooling/planning_audit.py"),
                             "--source-revision", revision], cwd=config.repo_root, timeout=300)
            bundle = json.loads(generated.stdout)
        except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
            for report in bundle["reports"].values():
                report["error"] = f"audit regeneration failed: {exc}"
        # A merge or checkout change during the audits invalidates closure.
        current = (remote_branch_oid(config.repo_root, default_branch(config.repo_root)) == revision and
                   run(["git", "rev-parse", "HEAD"], cwd=config.repo_root).stdout.strip() == revision and
                   not run(["git", "status", "--porcelain"], cwd=config.repo_root).stdout.strip())
    return build_closure(bundle, revision, issues, prs, checkout_current=current)


def planning_context(config: Config) -> dict[str, Any]:
    """Collect issue/PR history used with the authoritative repository files."""
    issues = list_history(config, "issue")
    prs = list_history(config, "pr")
    closure = read_closure(config, issues, prs)
    history = run(["git", "log", "--oneline", "--decorate", "-100"], cwd=config.repo_root).stdout
    status = run(["git", "status", "--short"], cwd=config.repo_root).stdout
    return {"issues": issues, "pull_requests": prs, "git_history": history, "git_status": status, "closure": closure}


# A planner needs a *catalogue* of historical work, not every archived issue
# body. GitHub remains the source of truth; no issue/PR is removed from history.
# Reserve headroom for Codex-side instructions and later repository growth.
PLANNER_INPUT_BUDGET = 750_000


def compact_planning_history(context: dict[str, Any], body_limit: int) -> dict[str, Any]:
    """Preserve complete history identities while bounding narrative payloads."""
    result = dict(context)
    for field in ("issues", "pull_requests"):
        compact = []
        for item in context.get(field, []):
            entry = dict(item)
            body = str(entry.get("body") or "")
            # Closed records still provide identity, state, title, timestamps,
            # dependency references and PR linkage. Their prose is not needed
            # on each planner run; the selected task can retrieve it from GitHub.
            active = is_open(item)
            if active and body_limit:
                excerpt = body[:body_limit]
                if len(body) > body_limit:
                    excerpt += "\n[truncated; retrieve full GitHub record when needed]"
            else:
                excerpt = ""
            # Preserve *all* explicit dependencies and blocker IDs even when
            # a long active body was abbreviated.
            references = list(dict.fromkeys(
                re.findall(r"(?im)^\s*Depends on:\s*#\d+[^\n]*", body)
                + re.findall(r"(?im)^\s*(?:Closure blocker|Blocker key):[^\n]*", body)
            ))
            entry["body"] = excerpt
            if references:
                entry["planning_references"] = references
            compact.append(entry)
        result[field] = compact
    return result


def planning_prompt(context: dict[str, Any], requested: int) -> str:
    # First shrink narrative only; keep the closure findings and full history
    # identities available for duplicate/dependency checking.
    context = compact_planning_history(context, body_limit=4000)
    closure = context.get("closure")
    context["closure"] = closure.planning_view(requested) if closure is not None else None
    prefix = f"""Plan the next implementation-sized GitHub issues for WarCraftMap.

FIRST read the release-blocker, runtime-acceptance and requirement-traceability reports and the freshly regenerated closure findings below, plus open/closed issue and PR history. These findings are the authoritative closure queue, ahead of ROADMAP.md checkboxes or optional content expansion. Read DESIGN_LOCK.md, ARCHITECTURE.md and AGENTS.md for implementation constraints.

When closure.active is true, return only implementation-sized repairs for the supplied closure candidates, with their exact identities in blocker_keys. Group at most four closely related identities per issue. Preserve dependencies; blocked findings become candidates only after their prerequisites pass a fresh audit. Do not refill with optional content to meet queue depth. Never return exhausted while closure is active, even when all repairs are already represented or need design. Return planned with no issues in that case. Closed work whose finding persists on a freshly audited new main revision needs a scoped follow-up referencing the previous issue/PR; never repeat the original implementation claim. A merged PR alone is not evidence of closure. Planned release/launch work (including #397) must wait for a freshly regenerated zero-blocker state and closed repair issues.

Only when closure.active is false, resume ordinary roadmap/content planning, using an empty blocker_keys list. Preserve roadmap and dependency order; choose only the next incomplete work that is actually unblocked. Do not duplicate open, completed, superseded, or PR-represented work.

The owner explicitly delegated ordinary research effects and game balance. Read age-of-sail-world/docs/HISTORICAL_BALANCE_AND_RESEARCH_EFFECTS.md and scenario/progression/gameplay-effect-design.json alongside DESIGN_LOCK.md. Research-unbound modifiers/policies/buildings/abilities/unit unlocks are preauthorized implementation work, **not** a new needs-design per technology. Group related effect consumers sharing one engine mechanism into at most four distinct exact research-unbound blocker keys per agent-ready issue; give actual effects with historically plausible scenario-owned tuning and deterministic tests. Preserve historically unequal 1450 starting strengths and meaningful weaker-polity survival paths without ahistorical bonus armies or forced historical outcomes. Do not turn a real novel gameplay architecture conflict into an invented default.\n\nReturn at most {requested} items, in implementation order. Every agent-ready body must include explicit `## Acceptance criteria` and `## Automated validation` sections and must not require player QA. An open needs-design issue blocks only work that materially depends on its decision: continue independent blocker repairs (or roadmap work once closure is clean), and explicitly state in each such issue body why it is independent of the open decision. Never skip a real dependency or invent a design choice. When a material decision is missing, return one needs-design item with exactly one decision question, then continue only with work explicitly independent of it. Do not duplicate an unresolved decision already represented by an open needs-design issue. Do not create repeated per-region needs-design questions for geography/content scope when DESIGN_LOCK.md already provides a reusable global rule; derive region-specific boundaries, compression, historical coverage, settlements, routes, terrain, and borders from the locked rules plus historical/geographic evidence and performance constraints. Ask the player only for a genuinely new material gameplay/design choice that cannot be resolved from those authorities. Only if closure is clean and no independent planned work remains, return outcome `exhausted` and no issues. Do not edit files or interact with GitHub.

GitHub and repository history:
{json.dumps(context, sort_keys=True)}
"""
    if len(prefix) <= PLANNER_INPUT_BUDGET:
        return prefix
    # A second pass reduces only active narratives, never issue identities,
    # closure findings, dependency references, or blocker identities.
    context = compact_planning_history(context, body_limit=700)
    context["closure"] = closure.planning_view(requested) if closure is not None else None
    marker = "GitHub and repository history:\n"
    prefix = prefix.split(marker, 1)[0] + marker + json.dumps(context, sort_keys=True) + "\n"
    if len(prefix) > PLANNER_INPUT_BUDGET:
        raise ValueError(
            f"planner context exceeds safe {PLANNER_INPUT_BUDGET}-character budget "
            f"({len(prefix)} chars) even after historical compaction; "
            "reduce closure/audit payload without dropping blocker identities"
        )
    return prefix


def invoke_planner(config: Config, context: dict[str, Any], requested: int, run_entry: dict[str, Any]) -> dict[str, Any]:
    schema = config.repo_root / "automation" / "codex-plan.schema.json"
    output = config.state_dir / "last-codex-plan.json"
    output.unlink(missing_ok=True)
    command = build_codex_command(config, config.repo_root, schema, output)
    process = subprocess.Popen(
        command, cwd=config.repo_root, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        start_new_session=True, env=os.environ.copy(),
        pass_fds=lock_fds(),
    )
    stream = ""
    timed_out = False
    try:
        stream, _ = process.communicate(
            planning_prompt(context, requested), timeout=config.timeout_minutes * 60,
        )
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stream, _ = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stream, _ = process.communicate()
    finally:
        tokens = parse_codex_token_usage(stream or "")
        run_entry["tokens"] = tokens
        run_entry["telemetry"] = "reported" if tokens is not None else "missing"
        run_entry["completed_at"] = utcnow().isoformat().replace("+00:00", "Z")
        log = config.state_dir / "logs" / f"planning-{run_entry['timestamp'].replace(':', '-')}.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(stream or "", encoding="utf-8")
    if timed_out:
        raise RuntimeError(f"Codex planning exceeded {config.timeout_minutes}-minute timeout")
    if process.returncode:
        raise RuntimeError(f"Codex planning exited {process.returncode}; see {log}")
    if not output.exists():
        raise RuntimeError(f"Codex planning produced no structured result; see {log}")
    return json.loads(output.read_text(encoding="utf-8"))


def notify_design_blocker(config: Config, issue: dict[str, Any], question: str) -> None:
    """Best-effort one-shot delivery to a generic command via JSON stdin."""
    if not config.design_notification_command:
        return
    command = shlex.split(config.design_notification_command)
    if not command:
        return
    payload = {"issue_number": int(issue["number"]), "title": issue["title"], "url": issue["url"], "question": question}
    result = subprocess.run(command, cwd=config.repo_root, input=json.dumps(payload) + "\n", text=True, capture_output=True, timeout=30)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"design notification failed ({result.returncode}): {detail}")


def create_plan_issues(config: Config, items: list[dict[str, str]], closure: Closure | None = None) -> int:
    created = 0
    for item in items:
        current = list_history(config, "issue")
        prs = list_history(config, "pr")
        if closure is not None:
            if remote_branch_oid(config.repo_root, default_branch(config.repo_root)) != closure.revision:
                raise ValueError("main advanced during planning; regenerate audits before creating work")
            latest = Closure(closure.revision, closure.fresh, closure.blockers, current, prs, closure.reports)
            keys = marked_keys(item)
            if latest.active and (not keys or any(key not in latest.actionable for key in keys)):
                continue
        existing = {normalized_work_title(entry["title"]) for entry in [*current, *prs]}
        if normalized_work_title(item["title"]) in existing:
            continue
        if NEEDS_DESIGN.match(item["title"]):
            question_key = normalized_question(item.get("question", ""))
            historical_questions = {
                normalized_question(question)
                for entry in current
                if (question := decision_question(entry.get("body") or ""))
            }
            if question_key and question_key in historical_questions:
                continue
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", encoding="utf-8") as body_file:
            body_file.write(item["body"])
            body_file.flush()
            result = run(["gh", "issue", "create", "--title", item["title"], "--body-file", body_file.name], cwd=config.repo_root)
        created += 1
        if NEEDS_DESIGN.match(item["title"]):
            url = result.stdout.strip().splitlines()[-1]
            match = re.search(r"/(\d+)/?$", url)
            if match:
                try:
                    notify_design_blocker(config, {"number": int(match.group(1)), "title": item["title"], "url": url}, item["question"])
                except Exception as exc:
                    print(f"notification warning for {url}: {exc}", file=sys.stderr)
    return created


def issue_blocker_numbers(issue: dict[str, Any]) -> set[int]:
    explicit = issue.get("blockedBy") or issue.get("blocked_by") or []
    numbers = {int(value) for value in explicit if str(value).isdigit()}
    body = issue.get("body") or ""
    for match in re.finditer(r"(?im)^\s*(?:blocked by|depends on)\s*:?[ \t]*#(\d+)\b", body):
        numbers.add(int(match.group(1)))
    return numbers


def completed_dependency_numbers(
    issues: list[dict[str, Any]], pull_requests: list[dict[str, Any]],
) -> set[int]:
    """Only closed issues or genuinely merged PRs can satisfy # dependencies.

    A closed but unmerged PR is not complete. Merged PRs must have their
    mergedAt timestamp, and are distinct from GitHub Issues history.
    """
    closed_issues = {int(row["number"]) for row in issues if not is_open(row)}
    merged_prs = {
        int(row["number"]) for row in pull_requests
        if str(row.get("state") or "").upper() == "MERGED" and row.get("mergedAt")
    }
    return closed_issues | merged_prs


def repair_kind(record: dict[str, Any]) -> str:
    """Return the retry lane, including recovery for legacy CI-repair records."""
    explicit = str(record.get("repair_kind") or "")
    if explicit in {"validation", "ci", "merge_conflict"}:
        return explicit
    failure = str(record.get("last_failure", ""))
    if record.get("pr") and "GitHub CI failed on PR #" in failure:
        return "ci"
    if not record.get("pr") and "./automation/run_checks.sh" in failure:
        return "validation"
    return ""


def attempt_budget(
    record: dict[str, Any],
    max_attempts: int,
    max_validation_repair_attempts: int = 5,
    max_ci_repair_attempts: int = 5,
    max_conflict_attempts: int = 5,
) -> tuple[str, int, int]:
    kind = repair_kind(record)
    if kind == "validation":
        key, limit = "validation_repair_attempts", max_validation_repair_attempts
    elif kind == "ci":
        key, limit = "ci_repair_attempts", max_ci_repair_attempts
    elif kind == "merge_conflict":
        key, limit = "conflict_attempts", max_conflict_attempts
    else:
        key, limit = "attempts", max_attempts
    return key, int(record.get(key, 0)), limit


def select_issue(
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    max_attempts: int,
    open_design_numbers: set[int] | None = None,
    max_validation_repair_attempts: int = 5,
    max_ci_repair_attempts: int = 5,
    max_conflict_attempts: int = 5,
    closure: Closure | None = None,
) -> dict[str, Any] | None:
    blockers = open_design_numbers or set()
    slots = integration.staged_numbers(state)
    if closure is not None:
        closed = completed_dependency_numbers(closure.issues, closure.prs)
        blockers = blockers | {number for issue in issues for number in issue_blocker_numbers(issue) if number not in closed}
    # Keep the original order for ordinary repairs. Explicitly verified
    # native launch failure #438 takes precedence only while release closure
    # remains active; the one-worker lock and all attempt/CI gates still apply.
    ordered = (sorted(issues, key=lambda issue: (
        0 if issue.get("number") in APPROVED_NATIVE_LAUNCH_DIAGNOSTIC
             and closure is not None and closure.active and closure.permits_issue(issue)
        else 1))
        if closure is not None and closure.active else issues)
    for issue in ordered:
        if not READY.match(str(issue.get("title", ""))):
            continue
        if closure is not None and not closure.permits_issue(issue):
            continue
        if issue_blocker_numbers(issue) & blockers:
            continue
        record = state["issues"].get(str(issue["number"]), {})
        if slots and int(issue["number"]) not in slots and not record.get("pr"):
            continue
        if record.get("status") in {"pr_open", "pr_closed", "needs_design", "merged", "waiting_dependency"}:
            continue
        # Resuming completed local work only runs integration/validation. It
        # neither launches Codex nor consumes another implementation attempt.
        if record.get("status") == "staged":
            return issue
        _attempt_key, attempts, limit = attempt_budget(
            record, max_attempts, max_validation_repair_attempts,
            max_ci_repair_attempts, max_conflict_attempts
        )
        if attempts >= limit:
            continue
        return issue
    return None


def issue_record(state: dict[str, Any], number: int) -> dict[str, Any]:
    return state["issues"].setdefault(str(number), {"attempts": 0, "status": "queued"})


def refresh_validation_repair_bases(config: Config, state: dict[str, Any]) -> None:
    """Revive pre-PR validation repairs when the controller base has advanced."""
    branch = default_branch(config.repo_root)
    base_oid = remote_branch_oid(config.repo_root, branch)
    if not base_oid:
        return
    for record in state["issues"].values():
        if record.get("pr") or repair_kind(record) != "validation":
            continue
        previous = str(record.get("validation_base_oid") or "")
        exhausted = int(record.get("validation_repair_attempts", 0)) >= config.max_validation_repair_attempts
        if not previous or previous != base_oid:
            record["validation_base_oid"] = base_oid
            record["validation_repair_attempts"] = 0
            if record.get("status") == "failed" or exhausted:
                record["status"] = "repair"


def dependency_completion_receipt(issue: dict[str, Any], closure: Closure) -> dict[str, str] | None:
    """Prove dependencies from current GitHub issue/PR history, not stale errors.

    A closed issue is not enough when its associated closing PR remains open.
    Merge history is only dependency evidence, never proof of native launch.
    """
    required = issue_blocker_numbers(issue)
    if not required:
        return None
    issues = {int(row["number"]): row for row in closure.issues}
    prs = {int(row["number"]): row for row in closure.prs}
    receipt = {}
    for number in sorted(required):
        pr = prs.get(number)
        if pr is not None:
            if str(pr.get("state") or "").upper() != "MERGED" or not pr.get("mergedAt"):
                return None
            receipt[str(number)] = "pr:" + str(pr["mergedAt"])
            continue
        prior = issues.get(number)
        if prior is None or is_open(prior) or not prior.get("closedAt"):
            return None
        # For an issue with a known implementing PR, a manually closed issue
        # cannot bypass the required PR merge.
        linked = [row for row in closure.prs if any(
            int(ref.get("number", -1)) == number
            for ref in (row.get("closingIssuesReferences") or []) if isinstance(ref, dict)
        )]
        if linked:
            merged = [row for row in linked if
                      str(row.get("state") or "").upper() == "MERGED" and row.get("mergedAt")]
            if not merged:
                return None
            receipt[str(number)] = "issue:" + str(prior["closedAt"]) + ":merged:" + str(
                sorted(str(row["mergedAt"]) for row in merged)[-1]
            )
        else:
            receipt[str(number)] = "issue:" + str(prior["closedAt"])
    return receipt


def reconcile_dependency_exhaustion(
    issues: list[dict[str, Any]], state: dict[str, Any],
    closure: Closure, max_attempts: int,
) -> None:
    """Give exhausted prerequisite-only failures one fresh chance after merge.

    Historical Codex runs, reported tokens, and previous attempt failures remain
    in the state. Replaying the same dependency receipt cannot grant more runs.
    """
    if not closure.fresh:
        return
    for issue in issues:
        record = state["issues"].get(str(issue["number"]))
        if (not record or record.get("status") not in {"failed", "waiting_dependency"}
                or record.get("pr")
                or (record.get("status") == "failed"
                    and int(record.get("attempts", 0)) < max_attempts)
                or not closure.permits_issue(issue)):
            continue
        failure = str(record.get("last_failure") or "")
        if (not failure.startswith("Codex implementation blocked:")
                or not re.search(r"\b(?:unmerged|not merged)\b", failure, re.I)):
            continue
        receipt = dependency_completion_receipt(issue, closure)
        if receipt is None:
            continue
        proof = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
        if proof == record.get("dependency_recovery_receipt"):
            continue
        record.setdefault("dependency_recovery_history", []).append({
            "attempts": int(record.get("attempts", 0)),
            "last_failure": failure,
            "completion_receipt": receipt,
            "recovery_revision": closure.revision,
        })
        record["dependency_recovery_receipt"] = proof
        # A wait consuming one Codex invocation keeps its remaining attempts;
        # an already exhausted historical record gets one fresh generation.
        if int(record.get("attempts", 0)) >= max_attempts:
            record["attempts"] = 0
        record["status"] = "queued"
        # Validation/CI repair lanes are unrelated to this prerequisite retry.
        for key in ("last_failure", "repair_kind", "validation_failure",
                    "validation_repair_attempts", "ci_repair_attempts", "conflict_attempts",
                    "validation_base_oid", "ci_base_oid", "conflict_base_oid"):
            record.pop(key, None)


def reconcile_ready_issue_states(issues: list[dict[str, Any]], state: dict[str, Any]) -> None:
    """Allow externally resolved design issues to re-enter the implementation queue."""
    for issue in issues:
        record = state["issues"].get(str(issue["number"]))
        if not record or record.get("status") != "needs_design":
            continue
        record["status"] = "queued"
        record["attempts"] = 0
        record["validation_repair_attempts"] = 0
        record["ci_repair_attempts"] = 0
        record["conflict_attempts"] = 0
        record.pop("last_failure", None)
        record.pop("repair_kind", None)
        record.pop("validation_failure", None)
        record.pop("ci_base_oid", None)
        record.pop("conflict_base_oid", None)


def comment(config: Config, number: int, body: str) -> None:
    run(["gh", "issue", "comment", str(number), "--body", body], cwd=config.repo_root)


def mark_needs_design(config: Config, issue: dict[str, Any], question: str) -> None:
    clean = READY.sub("", issue["title"]).strip()
    body = (issue.get("body") or "").rstrip()
    marker = re.search(r"(?im)^## Decision required\s*$", body)
    if marker:
        body = body[:marker.start()].rstrip()
    body += "\n\n## Decision required\n\n" + question.strip() + "\n"
    run(
        ["gh", "issue", "edit", str(issue["number"]), "--title", f"[needs-design] {clean}", "--body", body],
        cwd=config.repo_root,
    )
    comment(config, issue["number"], "Autonomous work paused because a material design decision is required:\n\n" + question)
    try:
        notify_design_blocker(config, {**issue, "title": f"[needs-design] {clean}"}, question)
    except Exception as exc:
        print(f"notification warning for issue #{issue['number']}: {exc}", file=sys.stderr)


def worktree_for(config: Config, issue_number: int) -> tuple[Path, str]:
    path = config.state_dir / "worktrees" / f"issue-{issue_number}"
    branch = f"agent/issue-{issue_number}"
    if path.exists():
        return path, branch
    run(["git", "fetch", "origin"], cwd=config.repo_root)
    default_branch = run(["gh", "repo", "view", "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"], cwd=config.repo_root).stdout.strip()
    branch_exists = run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=config.repo_root, check=False).returncode == 0
    args = ["git", "worktree", "add", str(path), branch] if branch_exists else ["git", "worktree", "add", "-b", branch, str(path), f"origin/{default_branch}"]
    run(args, cwd=config.repo_root)
    return path, branch


def default_branch(repo: Path) -> str:
    return run(
        ["gh", "repo", "view", "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"],
        cwd=repo,
    ).stdout.strip()


def codex_prompt(issue: dict[str, Any], repair_context: str, *, repair_kind: str = "") -> str:
    conflict_instructions = ""
    if repair_kind == "merge_conflict" or (
        not repair_kind and repair_context.startswith("Merge conflict repair required:")
    ):
        conflict_instructions = """

This is an integration repair. Current main has already been merged into this worktree and may have left unmerged paths. Resolve only actual merge conflicts, preserving the completed work from both main and the issue branch. Do not discard or broadly rewrite either work stream. Stage each resolved path with git add so no unmerged paths remain; do not commit. After the merge is clean, continue any previous validation repair included in the failure context and make only the minimal integration/validation changes needed for repository validation."""
    return f"""Implement GitHub issue #{issue['number']} in this isolated WarCraftMap worktree.

Title: {issue['title']}
Body:
{issue.get('body') or '(empty)'}

Follow AGENTS.md and the Age of Sail design documentation. Source and scenario data are authoritative. Do not ask the player to perform incremental testing. Do not commit, push, create or edit GitHub issues/PRs, install services, alter global tooling, or touch anything outside this worktree. Never bind-mount this worktree read/write into Docker or another container that runs as root or as a different UID/GID, and never run chown or chmod against this worktree from inside a container. If containerized validation is useful, mount the worktree read-only, copy the required source into container-private temporary storage such as /tmp, and build there. Run the relevant automated tests that are available inside this Codex environment. The outer worker performs the authoritative repository validation after you return outcome \"complete\"; therefore do NOT return \"blocked\" solely because a repository-level validation tool such as Grill is unavailable, or because Docker/external validation is denied by the Codex approval sandbox, when the implementation itself is complete and its available targeted/headless tests pass. In that case report the unavailable validation in the summary and return \"complete\" so the outer worker can run its configured validation command. Return \"blocked\" when a technical problem actually prevents completing the implementation or obtaining enough local verification for it to be ready for outer validation. Never invent a material game-design choice: use outcome \"needs_design\" ONLY when a material game-design decision is genuinely missing, with one exact player-facing design question. Tool availability, sandbox permissions, missing commands, patch/edit mechanics, CI problems, merge conflicts, and implementation failures are NOT design decisions.

Previous failure context, if any:
{repair_context or '(none)'}
{conflict_instructions}

Return the required JSON result. Use outcome \"complete\" only when the implementation is ready for repository validation."""


def build_codex_command(config: Config, worktree: Path, schema: Path, output: Path) -> list[str]:
    """Build the non-interactive Codex command for the installed CLI contract."""
    # In Codex CLI 0.153.x, --approve-for-me already routes approvals through
    # the workspace-write sandbox and is mutually exclusive with --sandbox.
    command = [
        "codex", "exec",
        "--ignore-user-config",
        "--ephemeral",
        "--approve-for-me",
        "--json",
        "--model", config.model,
    ]

    if config.reasoning_effort:
        command += [
            "-c",
            f'model_reasoning_effort="{config.reasoning_effort}"',
        ]

    command += [
        "--cd", str(worktree),
        "--output-schema", str(schema),
        "--output-last-message", str(output),
        "-",
    ]

    return command


def parse_codex_token_usage(output: str) -> int | None:
    """Return total tokens reported by one `codex exec --json` invocation.

    Modern Codex emits a turn.completed event for each model turn. We sum those
    per-turn usage values. A fallback understands older token_count-shaped
    events, but is used only when no turn.completed usage was observed.
    """
    completed_total = 0
    completed_seen = False
    cumulative_fallback: list[int] = []

    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        if event.get("type") == "turn.completed":
            usage = event.get("usage")
            if isinstance(usage, dict):
                total = usage.get("total_tokens")
                if not isinstance(total, int):
                    input_tokens = usage.get("input_tokens")
                    output_tokens = usage.get("output_tokens")
                    if isinstance(input_tokens, int) and isinstance(output_tokens, int):
                        total = input_tokens + output_tokens
                if isinstance(total, int) and total >= 0:
                    completed_total += total
                    completed_seen = True
            continue

        # Compatibility fallback for older JSON event envelopes.
        candidates = []
        payload = event.get("payload")
        if isinstance(payload, dict):
            candidates.append(payload)
        msg = event.get("msg")
        if isinstance(msg, dict):
            candidates.append(msg)
        for candidate in candidates:
            if candidate.get("type") != "token_count":
                continue
            info = candidate.get("info")
            if not isinstance(info, dict):
                continue
            usage = info.get("total_token_usage")
            if not isinstance(usage, dict):
                continue
            total = usage.get("total_tokens")
            if not isinstance(total, int):
                input_tokens = usage.get("input_tokens")
                output_tokens = usage.get("output_tokens")
                if isinstance(input_tokens, int) and isinstance(output_tokens, int):
                    total = input_tokens + output_tokens
            if isinstance(total, int) and total >= 0:
                cumulative_fallback.append(total)

    if completed_seen:
        return completed_total
    if cumulative_fallback:
        # token_count.total_token_usage is cumulative for the session.
        return max(cumulative_fallback)
    return None


def invoke_codex(
    config: Config,
    worktree: Path,
    issue: dict[str, Any],
    record: dict[str, Any],
    run_entry: dict[str, Any],
) -> dict[str, str]:
    schema = config.repo_root / "automation" / "codex-result.schema.json"
    run_entry.setdefault("id", uuid.uuid4().hex)
    run_dir = config.state_dir / "runs" / f"issue-{issue['number']}" / run_entry["id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    output = run_dir / "result.json"
    output.unlink(missing_ok=True)
    command = build_codex_command(config, worktree, schema, output)
    env = os.environ.copy()
    process = subprocess.Popen(
        command,
        cwd=worktree,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
        env=env,
        pass_fds=lock_fds(),
    )
    stdout = ""
    timed_out = False
    prompt = codex_prompt(issue, record.get("last_failure", ""), repair_kind=repair_kind(record))
    predecessors = record.get("stage", {}).get("predecessors", [])
    if predecessors and not record.get("pr"):
        prompt += (
            "\n\nThe controller reserved the single unpublished staging slot for this implementation. "
            "Managed predecessor PRs: " + ", ".join(f"#{row['number']}" for row in predecessors) + ". "
            "Implement and run focused automated tests in this worktree. Leave complete repository "
            "validation to the controller after integration preflight. Do not merge an unmerged "
            "predecessor branch or reuse its CI/artifacts as evidence for this code."
        )
    try:
        stdout, _ = process.communicate(
            prompt,
            timeout=config.timeout_minutes * 60,
        )
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        try:
            stdout, _ = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, _ = process.communicate()
    finally:
        tokens = parse_codex_token_usage(stdout or "")
        run_entry["tokens"] = tokens
        run_entry["telemetry"] = "reported" if tokens is not None else "missing"
        run_entry["completed_at"] = utcnow().isoformat().replace("+00:00", "Z")
        log = run_dir / "codex.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(stdout or "", encoding="utf-8")

    if timed_out:
        raise RuntimeError(f"Codex exceeded {config.timeout_minutes}-minute timeout")
    if process.returncode:
        raise RuntimeError(f"Codex exited {process.returncode}; see {log}")
    if not output.exists():
        raise RuntimeError(f"Codex produced no structured result; see {log}")
    return json.loads(output.read_text(encoding="utf-8"))


def run_checks(config: Config, worktree: Path) -> None:
    command = shlex.split(config.checks_command)
    if not command:
        raise ValueError("WARCRAFTMAP_AGENT_CHECKS_COMMAND may not be empty")
    run(command, cwd=worktree, timeout=config.timeout_minutes * 60)


def prepare_validation_repair(config: Config, worktree: Path, issue_number: int) -> tuple[str, list[str]]:
    """Checkpoint dirty issue work, then merge current main before retrying validation."""
    run(["git", "fetch", "origin"], cwd=worktree)
    branch = default_branch(config.repo_root)
    upstream = f"origin/{branch}"
    # Identify the commit actually fetched/merged, not a later ls-remote result.
    base_oid = run(["git", "rev-parse", upstream], cwd=worktree).stdout.strip()
    merge_head = run(["git", "rev-parse", "--verify", "--quiet", "MERGE_HEAD"], cwd=worktree, check=False)
    if merge_head.returncode not in {0, 1}:
        raise RuntimeError(f"could not inspect merge state (git exited {merge_head.returncode})")
    conflicts = unmerged_paths(worktree)
    if conflicts:
        # Legacy validation records can already contain an unfinished merge.
        # Never checkpoint its conflict markers or partially resolved index.
        return merge_head.stdout.strip() or base_oid, conflicts
    status = run(["git", "status", "--porcelain"], cwd=worktree).stdout
    if status.strip() or merge_head.returncode == 0:
        run(["git", "add", "-A"], cwd=worktree)
        run(["git", "commit", "-m", f"Checkpoint issue #{issue_number} before validation repair"], cwd=worktree)
    merge = run(["git", "merge", "--no-edit", upstream], cwd=worktree, check=False)
    conflicts = unmerged_paths(worktree)
    if merge.returncode and not conflicts:
        detail = (merge.stderr or merge.stdout).strip()
        raise RuntimeError(f"could not merge {upstream}: {detail}")
    return base_oid, conflicts


def unmerged_paths(worktree: Path) -> list[str]:
    return run(
        ["git", "diff", "--name-only", "--diff-filter=U"], cwd=worktree
    ).stdout.splitlines()


def prepare_merge_conflict_repair(config: Config, worktree: Path) -> list[str]:
    """Merge current upstream main, leaving genuine conflicts for Codex."""
    run(["git", "fetch", "origin"], cwd=worktree)
    merge_head = run(
        ["git", "rev-parse", "--verify", "--quiet", "MERGE_HEAD"], cwd=worktree, check=False,
    )
    if merge_head.returncode not in {0, 1}:
        raise RuntimeError(f"could not inspect merge state (git exited {merge_head.returncode})")
    if merge_head.returncode == 1:
        upstream = f"origin/{default_branch(config.repo_root)}"
        merge = run(["git", "merge", "--no-edit", upstream], cwd=worktree, check=False)
        if merge.returncode:
            conflicts = unmerged_paths(worktree)
            if not conflicts:
                detail = (merge.stderr or merge.stdout).strip()
                raise RuntimeError(f"could not merge {upstream}: {detail}")
    return unmerged_paths(worktree)


def resume_validation_repair(record: dict[str, Any], conflicts: list[str]) -> None:
    """Resume the suspended validation lane only after the index is resolved."""
    if (
        not conflicts and repair_kind(record) == "merge_conflict"
        and not record.get("pr") and "validation_failure" in record
    ):
        record["repair_kind"] = "validation"


def prepare_repair(config: Config, worktree: Path, issue_number: int, record: dict[str, Any]) -> None:
    """Determine the actual repair lane before charging a Codex attempt."""
    kind = repair_kind(record)
    base_oid = record.get("stage", {}).get("integration_base_sha") or record.get("conflict_base_oid")
    if kind == "validation":
        # Kept separately because last_failure is replaced by Codex errors and
        # conflict diagnostics on subsequent worker invocations.
        record.setdefault("validation_failure", str(record.get("last_failure") or ""))
        base_oid, conflicts = prepare_validation_repair(config, worktree, issue_number)
        record["validation_base_oid"] = base_oid
        record["repair_kind"] = "merge_conflict" if conflicts else "validation"
    elif kind == "merge_conflict":
        conflicts = prepare_merge_conflict_repair(config, worktree)
        resume_validation_repair(record, conflicts)
    elif not record.get("pr"):
        # Even a queued/initial retry may have a worktree created against an
        # obsolete main. Bring it forward *before* consuming any Codex quota.
        # Existing changes are checkpointed, never thrown away.
        base_oid, conflicts = prepare_validation_repair(config, worktree, issue_number)
        if conflicts:
            record["repair_kind"] = "merge_conflict"
            record["last_failure"] = (
                "Merge conflict repair required: prerequisite changes from main "
                "conflict with the preserved issue worktree; resolve: "
                + ", ".join(conflicts)
            )
        else:
            return
    else:
        return

    if record["repair_kind"] == "merge_conflict":
        if conflicts:
            event = {"base_sha": base_oid, "paths": conflicts}
            if event not in integration.metrics(record)["conflicts"]:
                integration.metrics(record)["conflicts"].append(event)
        record["last_failure"] = (
            "Merge conflict repair required: current main was merged into the issue "
            "worktree; resolve only these unmerged paths while preserving both work "
            f"streams: {', '.join(conflicts) if conflicts else '(none remain)'}"
        )
        if "validation_failure" in record:
            record["last_failure"] += (
                "\nResolve the merge first, then continue the validation repair. "
                "Previous validation failure:\n" + record["validation_failure"]
            )
    else:
        record["last_failure"] = (
            "Repository validation repair required: current main was merged into this "
            "pre-PR worktree before retrying. No unmerged paths remain. "
            "Preserve the issue implementation and current main changes, and resolve "
            "only integration/validation problems. Previous validation failure:\n"
            + record["validation_failure"]
        )


def push_existing_pr_repair(worktree: Path, issue_number: int, pr: int) -> None:
    """Commit a resolved merge when needed, then update the existing PR branch."""
    status = run(["git", "status", "--porcelain"], cwd=worktree).stdout
    if status.strip():
        run(["git", "add", "-A"], cwd=worktree)
        run(["git", "commit", "-m", f"Repair PR #{pr} for issue #{issue_number}"], cwd=worktree)
    run(["git", "push"], cwd=worktree)


def reconcile_pr_claims(state: dict, history: list[dict]) -> None:
    """Recover a crash between PR creation and state persistence, without a new claim."""
    owners: dict[int, int] = {}
    for row in history:
        match = re.fullmatch(r"agent/issue-(\d+)", str(row.get("headRefName") or ""))
        if not match:
            continue
        number, pr = int(match[1]), int(row["number"])
        existing = state["issues"].get(str(number), {})
        recovering_publication = (
            not existing.get("pr") and existing.get("metrics", {}).get("phase") == "publication" and
            existing.get("validation_receipt", {}).get("head_sha") and
            existing["validation_receipt"]["head_sha"] == row.get("headRefOid")
        )
        if str(row.get("state")).upper() != "OPEN" and not recovering_publication:
            continue
        if number in owners and owners[number] != pr:
            raise RuntimeError(f"multiple managed PRs claim issue #{number}; integration paused")
        owners[number] = pr
        record = issue_record(state, number)
        if record.get("pr") and record["pr"] != pr:
            raise RuntimeError(f"issue #{number} already owns PR #{record['pr']}; integration paused")
        if not record.get("pr") or record.get("status") == "pr_closed":
            record.update(pr=pr, status="pr_open")
            integration.phase(record, "pr_ci")


def predecessor_snapshot(config: Config, state: dict, history: list[dict], record: dict) -> list[dict]:
    tracked = {int(row["pr"]) for row in state["issues"].values() if row.get("pr")}
    remembered = {int(row["number"]) for row in record.get("stage", {}).get("predecessors", [])}
    numbers = remembered | {int(row["number"]) for row in history
                           if str(row.get("state")).upper() == "OPEN" and
                           (int(row["number"]) in tracked or
                            re.fullmatch(r"agent/issue-\d+", str(row.get("headRefName") or "")))}
    numbers.discard(record.get("pr"))
    snapshots = []
    fields = "number,state,headRefOid,headRefName,baseRefName,changedFiles,mergedAt,mergeCommit,statusCheckRollup"
    for number in sorted(numbers):
        snapshot = {"number": number, "state": "UNKNOWN", "files": None}
        try:
            view = gh_json(config.repo_root, ["pr", "view", str(number), "--json", fields])
            if view.get("number") != number or view.get("state") not in {"OPEN", "CLOSED", "MERGED"}:
                raise ValueError("GitHub returned incomplete PR identity/state")
            snapshot.update({key: value for key, value in view.items() if key != "statusCheckRollup"})
            checks = view.get("statusCheckRollup") or []
            snapshot["ci"] = ("failed" if any(check_state(row) == "failed" for row in checks) else
                              "pending" if not checks or any(check_state(row) == "pending" for row in checks)
                              else "passed")
            if view["state"] == "OPEN":
                pages = gh_json(config.repo_root, ["api", "--paginate",
                    f"repos/{{owner}}/{{repo}}/pulls/{number}/files?per_page=100"])
                rows = [row for page in pages for row in page]
                if (not rows or len(rows) != view.get("changedFiles") or
                        any(not isinstance(row, dict) or not row.get("filename") for row in rows)):
                    raise ValueError("incomplete PR changed-file inventory")
                filenames = [row["filename"] for row in rows]
                if len(set(filenames)) != len(rows):
                    raise ValueError("duplicate paths in PR changed-file inventory")
                filenames += [row["previous_filename"] for row in rows if row.get("previous_filename")]
                if integration.paths(filenames) is None:
                    raise ValueError("ambiguous PR changed-file inventory")
                current = gh_json(config.repo_root, ["pr", "view", str(number), "--json", "state,headRefOid"])
                if not view.get("headRefOid") or current.get("headRefOid") != view["headRefOid"] or current["state"] != "OPEN":
                    raise ValueError("PR changed while its files were being read")
                snapshot["files"] = sorted(set(filenames))
        except Exception as exc:
            snapshot["files"] = None
            snapshot["error"] = str(exc)[-1000:]
        snapshots.append(snapshot)
    return snapshots


def changed_paths(worktree: Path, base: str) -> list[str]:
    # --no-renames deliberately includes both names of moved/deleted files.
    tracked = run(["git", "diff", "--name-only", "--no-renames", "-z", base], cwd=worktree).stdout
    new = run(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=worktree).stdout
    return sorted(set(path for path in (tracked + new).split("\0") if path))


def reserve_stage(config: Config, state: dict, issue: dict, record: dict, worktree: Path,
                  predecessors: list[dict]) -> None:
    if record.get("stage"):
        return
    slots = integration.staged_numbers(state)
    if not record.get("pr") and len(slots) >= integration.MAX_STAGED_DEPTH and issue["number"] not in slots:
        raise RuntimeError("the single unpublished staging slot is occupied")
    base = run(["git", "merge-base", "HEAD", f"origin/{default_branch(config.repo_root)}"], cwd=worktree).stdout.strip()
    record["stage"] = {"created_at": integration.stamp(), "implementation_base_sha": base,
                       "predecessors": predecessors, "implementation_complete": False,
                       "worktree": str(worktree), "branch": f"agent/issue-{issue['number']}"}
    integration.phase(record, "implementation")


def integration_hold(record: dict, files: list[str], predecessors: list[dict]) -> str:
    stage = record["stage"]
    stage["predecessors"] = predecessors
    stage["files"] = files
    holds = []
    for pr in predecessors:
        if pr.get("error"):
            holds.append(f"PR #{pr['number']}: {pr['error']}")
        elif pr.get("state") == "MERGED":
            if not pr.get("mergedAt") or not (pr.get("mergeCommit") or {}).get("oid"):
                holds.append(f"PR #{pr['number']}: merge evidence is incomplete")
        elif pr.get("state") == "CLOSED":
            holds.append(f"PR #{pr['number']} closed without merging; preserved work needs review or a reopened predecessor")
        else:
            decision = integration.classify(files, pr.get("files"))
            integration.observe(record, pr, decision)
            if not decision["independent"]:
                holds.append(f"PR #{pr['number']} {pr.get('ci', 'unknown')}: {decision['reason']}")
    if not record.get("pr") and sum(pr.get("state") == "OPEN" for pr in predecessors) >= integration.MAX_OPEN_PRS:
        holds.append("two managed PRs already occupy the bounded CI trial")
    if holds and integration.seconds(stage["created_at"], integration.stamp()) >= integration.STAGE_TIMEOUT_HOURS * 3600:
        holds.insert(0, "staging wait exceeded 24 hours; attention required (work remains preserved)")
    return "; ".join(holds)


def defer_integration(config: Config, state: dict, issue: dict, record: dict, reason: str) -> None:
    record["status"] = "staged"
    record["stage"]["hold_reason"] = reason
    integration.phase(record, "staging_wait")
    save_state(config.state_dir / "state.json", state)
    print(f"issue #{issue['number']}: staged in {record['stage']['worktree']}; {reason}")


def regenerate_integration_reports(config: Config, worktree: Path, files: list[str]) -> None:
    """Generate reports from merged source, never select a conflict side or old PASS."""
    for script in sorted(worktree.glob("maps/*/*/tooling/requirement_traceability_audit.py")):
        project = script.parent.parent
        relative = project.relative_to(worktree).as_posix() + "/"
        if not any(path.startswith((relative, "maps/historical-world-rpg/_shared/")) for path in files):
            continue
        run([sys.executable, str(script), "--write", "--check"], cwd=worktree,
            timeout=config.timeout_minutes * 60)
        reports = [project / "reports/traceability" / f"requirements.{suffix}" for suffix in ("json", "md")]
        run(["git", "add", "--", *(str(path.relative_to(worktree)) for path in reports)], cwd=worktree)


def generated_report(path: str) -> bool:
    return bool(re.fullmatch(r"maps/[^/]+/[^/]+/reports/traceability/requirements\.(json|md)", path))


def checkpoint_candidate(worktree: Path, number: int) -> None:
    if unmerged_paths(worktree):
        raise RuntimeError("cannot checkpoint unresolved integration conflicts")
    dirty = run(["git", "status", "--porcelain"], cwd=worktree).stdout.strip()
    merging = run(["git", "rev-parse", "--verify", "--quiet", "MERGE_HEAD"], cwd=worktree, check=False).returncode == 0
    if dirty or merging:
        run(["git", "add", "-A"], cwd=worktree)
        run(["git", "commit", "-m", f"Integrate issue #{number} before complete validation"], cwd=worktree)


def run_scoped_checks(config: Config, worktree: Path, files: list[str]) -> None:
    directories = []
    if any(path.startswith("automation/") for path in files):
        directories.append(worktree / "automation/tests")
    if any(path.startswith("maps/") for path in files):
        directories.extend(sorted(worktree.glob("maps/*/*/tests")))
    for directory in directories:
        if directory.is_dir():
            run([sys.executable, "-m", "unittest", "discover", "-s", str(directory), "-p", "test_*.py"],
                cwd=worktree, timeout=config.timeout_minutes * 60)


def assert_validation_receipt(config: Config, worktree: Path, receipt: dict) -> None:
    if (not receipt.get("base_sha") or not receipt.get("head_sha") or
            remote_branch_oid(config.repo_root, default_branch(config.repo_root)) != receipt["base_sha"] or
            run(["git", "rev-parse", "HEAD"], cwd=worktree).stdout.strip() != receipt["head_sha"] or
            run(["git", "status", "--porcelain"], cwd=worktree).stdout.strip() or
            run(["git", "merge-base", "--is-ancestor", receipt["base_sha"], "HEAD"],
                cwd=worktree, check=False).returncode):
        raise RuntimeError("code or main advanced after validation; fresh integration and complete validation required")


def complete_candidate(config: Config, state: dict, issue: dict, record: dict, worktree: Path, branch: str) -> None:
    """One preflight per wake; no previous CI/validation result authorizes new code."""
    stage = record["stage"]
    stage["implementation_complete"] = True
    record["status"] = "staged"
    record.pop("validation_receipt", None)
    save_state(config.state_dir / "state.json", state)
    history = list_history(config, "pr")
    predecessors = predecessor_snapshot(config, state, history, record)
    files = changed_paths(worktree, stage["implementation_base_sha"])
    hold = integration_hold(record, files, predecessors)
    if hold:
        defer_integration(config, state, issue, record, hold)
        return
    integration.phase(record, "integration")
    save_state(config.state_dir / "state.json", state)
    base, conflicts = prepare_validation_repair(config, worktree, issue["number"])
    stage["integration_base_sha"] = base
    if conflicts:
        event = {"base_sha": base, "paths": conflicts}
        if event not in integration.metrics(record)["conflicts"]:
            integration.metrics(record)["conflicts"].append(event)
    if not conflicts or all(generated_report(path) for path in conflicts):
        try:
            regenerate_integration_reports(config, worktree, files + conflicts)
        except Exception as exc:
            record.update(repair_kind="validation", validation_failure=str(exc)[-4000:], validation_base_oid=base)
            raise
        conflicts = unmerged_paths(worktree)
    if conflicts:
        record.update(status="repair", repair_kind="merge_conflict",
                      last_failure="Merge conflict repair required: " + ", ".join(conflicts))
        save_state(config.state_dir / "state.json", state)
        return
    # The new main must actually contain each confirmed merge, not merely have
    # a newer timestamp or an unrelated successful CI run.
    for pr in predecessors:
        if pr.get("state") == "MERGED" and run(
            ["git", "merge-base", "--is-ancestor", pr["mergeCommit"]["oid"], base],
            cwd=worktree, check=False,
        ).returncode:
            defer_integration(config, state, issue, record, f"main does not contain merged PR #{pr['number']} yet")
            return
    checkpoint_candidate(worktree, issue["number"])
    stage["implementation_base_sha"] = base
    files = changed_paths(worktree, base)
    receipt = {"base_sha": base, "head_sha": run(["git", "rev-parse", "HEAD"], cwd=worktree).stdout.strip()}
    data = integration.metrics(record)
    if data["first_validation_base_sha"] is None:
        data["first_validation_base_sha"] = base
    validation = {**receipt, "started_at": integration.stamp(), "result": "running"}
    data["validations"].append(validation)
    integration.phase(record, "validation")
    save_state(config.state_dir / "state.json", state)
    try:
        run_scoped_checks(config, worktree, files)
        run_checks(config, worktree)
    except Exception as exc:
        validation["result"] = "failed"
        record.update(repair_kind="validation" if not record.get("pr") else "ci",
                      validation_failure=str(exc)[-4000:], validation_base_oid=base)
        raise
    finally:
        validation["completed_at"] = integration.stamp()
        validation["seconds"] = integration.seconds(validation["started_at"], validation["completed_at"])
    validation["result"] = "passed"
    try:
        assert_validation_receipt(config, worktree, receipt)
    except RuntimeError as exc:
        defer_integration(config, state, issue, record, str(exc))
        return
    # Refresh both claims and release/dependency gates after the expensive work.
    context = planning_context(config)
    current_issue = next((row for row in context["issues"] if row["number"] == issue["number"]), {})
    if (not current_issue or not is_open(current_issue) or not READY.match(current_issue["title"]) or
            not context["closure"].fresh or not context["closure"].permits_issue(current_issue) or
            (issue_blocker_numbers(current_issue) and dependency_completion_receipt(current_issue, context["closure"]) is None)):
        defer_integration(config, state, issue, record, "current issue, release or dependency gate no longer permits publication")
        return
    predecessors = predecessor_snapshot(config, state, context["pull_requests"], record)
    hold = integration_hold(record, files, predecessors)
    if hold:
        defer_integration(config, state, issue, record, hold)
        return
    record["validation_receipt"] = receipt
    for key in ("last_failure", "repair_kind", "validation_failure"):
        record.pop(key, None)
    integration.phase(record, "publication")
    save_state(config.state_dir / "state.json", state)
    if record.get("pr"):
        assert_validation_receipt(config, worktree, receipt)
        push_existing_pr_repair(worktree, issue["number"], int(record["pr"]))
    else:
        record["pr"] = publish(config, issue, worktree, branch, receipt=receipt)
    record["status"] = "pr_open"
    stage.pop("hold_reason", None)
    integration.phase(record, "pr_ci")
    save_state(config.state_dir / "state.json", state)


def publish(config: Config, issue: dict[str, Any], worktree: Path, branch: str, *, receipt: dict) -> int:
    assert_validation_receipt(config, worktree, receipt)
    ahead = run(["git", "rev-list", "--count", f"{receipt['base_sha']}..HEAD"], cwd=worktree).stdout.strip()
    if int(ahead or "0") < 1:
        raise RuntimeError("Codex reported completion but made no changes")
    run(["git", "push", "--set-upstream", "origin", branch], cwd=worktree)
    existing = run(
        ["gh", "pr", "list", "--head", branch, "--state", "open", "--json", "number", "--jq", ".[0].number"],
        cwd=worktree,
    ).stdout.strip()
    if existing:
        return int(existing)
    # Native launch #438 cannot be marked fixed by static/headless CI: do not
    # let GitHub's closing-keyword automation close it on a PR merge.
    relation = "Investigates" if issue["number"] in APPROVED_NATIVE_LAUNCH_DIAGNOSTIC else "Closes"
    result = run(["gh", "pr", "create", "--base", default_branch(config.repo_root), "--head", branch, "--title", READY.sub("", issue["title"]), "--body", f"{relation} #{issue['number']}\n\nCreated by the low-priority WarCraftMap autonomous worker after repository validation."], cwd=worktree)
    match = re.search(r"/(\d+)\s*$", result.stdout.strip())
    if not match:
        raise RuntimeError(f"could not parse PR number from: {result.stdout.strip()}")
    return int(match.group(1))


def check_state(item: dict[str, Any]) -> str:
    """Normalize GitHub CheckRun and legacy StatusContext rollup entries."""
    conclusion = item.get("conclusion")
    if conclusion:
        return "failed" if conclusion in {
            "FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"
        } else "passed"
    status = item.get("status")
    if status:
        return "passed" if status == "COMPLETED" else "pending"
    state = item.get("state")
    if state in {"SUCCESS", "NEUTRAL"}:
        return "passed"
    if state in {"ERROR", "FAILURE"}:
        return "failed"
    return "pending"


def build_pr_merge_command(pr: int) -> list[str]:
    """Merge without asking gh to delete a branch still checked out by a worktree."""
    return ["gh", "pr", "merge", str(pr), "--merge"]


def cleanup_merged_issue(config: Config, issue_number: int) -> list[str]:
    """Best-effort cleanup after GitHub confirms an issue PR merged."""
    worktree = config.state_dir / "worktrees" / f"issue-{issue_number}"
    branch = f"agent/issue-{issue_number}"
    errors: list[str] = []
    worktree_removed = not worktree.exists()
    if worktree.exists():
        try:
            status = run(["git", "status", "--porcelain"], cwd=worktree).stdout
            if status.strip():
                errors.append(f"preserved dirty worktree {worktree}")
            else:
                run(["git", "worktree", "remove", str(worktree)], cwd=config.repo_root)
                worktree_removed = True
        except Exception as exc:
            errors.append(f"could not remove worktree {worktree}: {exc}")
    else:
        try:
            run(["git", "worktree", "prune"], cwd=config.repo_root)
        except Exception as exc:
            errors.append(f"could not prune missing worktree {worktree}: {exc}")
    if worktree_removed:
        try:
            result = run(
                ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
                cwd=config.repo_root, check=False,
            )
            if result.returncode not in {0, 1}:
                raise RuntimeError(f"git show-ref exited {result.returncode}")
            if result.returncode == 0:
                run(["git", "branch", "--delete", "--force", branch], cwd=config.repo_root)
        except Exception as exc:
            errors.append(f"could not delete local branch {branch}: {exc}")
    try:
        result = run(
            ["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
            cwd=config.repo_root, check=False,
        )
        if result.returncode not in {0, 2}:
            raise RuntimeError(f"git ls-remote exited {result.returncode}")
        if result.returncode == 0:
            run(["git", "push", "origin", "--delete", branch], cwd=config.repo_root)
    except Exception as exc:
        errors.append(f"could not delete remote branch {branch}: {exc}")
    for error in errors:
        print(f"cleanup warning for issue #{issue_number}: {error}", file=sys.stderr)
    return errors


def finish_merged_issue(config: Config, number: str, record: dict[str, Any]) -> None:
    """Keep merge success authoritative even when issue-close/cleanup reports warnings."""
    record["status"] = "merged"
    if record.get("metrics"):
        integration.phase(record, "merged")
    errors: list[str] = []
    if int(number) in APPROVED_NATIVE_LAUNCH_DIAGNOSTIC:
        # Code integration succeeded; a real client smoke has NOT been run.
        # Keep the incident open so a second speculative static fix cannot be
        # mistaken for the player's actual launch acceptance.
        record["native_validation"] = "pending"
    else:
        try:
            run(["gh", "issue", "close", str(number), "--reason", "completed"], cwd=config.repo_root)
        except Exception as exc:
            errors.append(f"could not close merged issue #{number}: {exc}")
    errors.extend(cleanup_merged_issue(config, int(number)))
    if errors:
        record["cleanup_errors"] = errors
    else:
        record.pop("cleanup_errors", None)


def service_open_prs(config: Config, state: dict[str, Any], allowed_issues: set[int] | None = None) -> bool:
    """Merge or recover one tracked open PR per worker invocation."""
    for number, record in state["issues"].items():
        if allowed_issues is not None and int(number) not in allowed_issues:
            continue
        pr = record.get("pr")
        if not pr:
            continue
        failed_conflict = (
            record.get("status") == "failed"
            and "unmergeable because main conflicts" in str(record.get("last_failure", ""))
        )
        if record.get("status") != "pr_open" and not failed_conflict:
            continue
        view = gh_json(config.repo_root, ["pr", "view", str(pr), "--json", "state,mergeStateStatus,mergeable,statusCheckRollup,baseRefName,headRefOid"])
        if view["state"] == "MERGED":
            finish_merged_issue(config, number, record)
            return True
        if view["state"] == "CLOSED":
            record["status"] = "pr_closed"
            record["last_failure"] = f"PR #{pr} was closed without merging; manual review is required."
            if record.get("metrics"):
                integration.phase(record, "attention")
            return True
        receipt = record.get("validation_receipt")
        if receipt:
            base = remote_branch_oid(config.repo_root, str(view.get("baseRefName") or default_branch(config.repo_root)))
            if view.get("headRefOid") != receipt["head_sha"] or base != receipt["base_sha"]:
                # Green checks for an older head/base cannot validate a new
                # combined tree. Resume local preflight without a Codex charge.
                record["status"] = "staged"
                record["stage"]["hold_reason"] = "PR head/base changed; fresh integration and CI required"
                integration.phase(record, "staging_wait")
                return True
        merge_state = str(view.get("mergeStateStatus") or "").upper()
        mergeable = str(view.get("mergeable") or "").upper()
        if merge_state == "DIRTY" or mergeable == "CONFLICTING":
            base_oid = remote_branch_oid(config.repo_root, str(view.get("baseRefName") or ""))
            previous_base_oid = str(record.get("conflict_base_oid") or "")
            if base_oid and base_oid != previous_base_oid:
                record["conflict_base_oid"] = base_oid
                record["conflict_attempts"] = 0
            conflict_attempts = int(record.get("conflict_attempts", 0))
            record["repair_kind"] = "merge_conflict"
            if conflict_attempts >= config.max_conflict_attempts:
                record["status"] = "failed"
                record["last_failure"] = (
                    f"PR #{pr} is unmergeable because main conflicts with the issue branch, "
                    f"and the conflict-repair attempt limit ({config.max_conflict_attempts}) is exhausted "
                    f"for base {base_oid[:12] or 'unknown'}."
                )
            else:
                record["status"] = "repair"
                record["last_failure"] = (
                    f"Merge conflict repair required: PR #{pr} is DIRTY against base "
                    f"{base_oid[:12] or 'unknown'} because current main conflicts with the issue "
                    "branch. Preserve completed work from both branches."
                )
            return True
        checks = view.get("statusCheckRollup") or []
        failed = any(check_state(item) == "failed" for item in checks)
        pending = any(check_state(item) == "pending" for item in checks)
        if failed:
            base_oid = remote_branch_oid(config.repo_root, str(view.get("baseRefName") or ""))
            previous_base_oid = str(record.get("ci_base_oid") or "")
            if base_oid and previous_base_oid and base_oid != previous_base_oid:
                record["ci_repair_attempts"] = 0
            if base_oid:
                record["ci_base_oid"] = base_oid
            record["repair_kind"] = "ci"
            ci_attempts = int(record.get("ci_repair_attempts", 0))
            if ci_attempts >= config.max_ci_repair_attempts:
                record["status"] = "failed"
                record["last_failure"] = (
                    f"GitHub CI failed on PR #{pr}, and the CI-repair attempt limit "
                    f"({config.max_ci_repair_attempts}) is exhausted for base "
                    f"{base_oid[:12] or 'unknown'}."
                )
            else:
                record["status"] = "repair"
                record["last_failure"] = (
                    f"GitHub CI failed on PR #{pr}. Inspect it with gh pr checks {pr} "
                    "and repair the implementation."
                )
            return True
        if pending:
            if failed_conflict:
                return True
            continue
        if merge_state not in {"CLEAN", "HAS_HOOKS", "UNSTABLE"}:
            # A PR already known to have failed from merge conflicts remains
            # owned by PR recovery while GitHub recomputes mergeability. Do not
            # fall through to queue planning and burn Codex on unrelated work.
            if failed_conflict:
                return True
            continue
        # Never merge a PR that has not reported any CI checks. Repositories
        # without branch-protection "required" checks are still gated by the
        # complete successful statusCheckRollup above.
        if not checks:
            continue
        command = build_pr_merge_command(int(pr))
        if receipt:
            # GitHub atomically rejects a changed head between inspection and merge.
            command += ["--match-head-commit", receipt["head_sha"]]
        run(command, cwd=config.repo_root)
        finish_merged_issue(config, number, record)
        return True
    return False


def record_attempt_failure(config: Config, record: dict, exc: Exception) -> None:
    if record.get("status") == "staged" and not repair_kind(record):
        # A transport/checkpoint/publication failure is not a request to rerun
        # the finished implementation, nor a reason to lose its reserved slot.
        record["stage"]["hold_reason"] = str(exc)[-4000:]
        integration.phase(record, "staging_wait")
        print(f"integration deferred: {exc}", file=sys.stderr)
        return
    _key, attempts, limit = attempt_budget(
        record, config.max_attempts, config.max_validation_repair_attempts,
        config.max_ci_repair_attempts, config.max_conflict_attempts,
    )
    record["status"] = "failed" if attempts >= limit else "repair"
    record["last_failure"] = str(exc)[-4000:]
    if attempts >= limit:
        lane = {"validation": "validation-repair", "ci": "CI-repair",
                "merge_conflict": "conflict-repair"}.get(repair_kind(record), "implementation")
        record["last_failure"] += f"\nThe {lane} attempt limit ({limit}) is exhausted."
    integration.phase(record, "attention" if attempts >= limit else "repair")
    print(f"attempt failed: {exc}", file=sys.stderr)


def collect_ci_metrics(config: Config, record: dict, number: str) -> None:
    data = integration.metrics(record)
    pages = gh_json(config.repo_root, ["api", "--paginate",
        f"repos/{{owner}}/{{repo}}/actions/runs?branch=agent%2Fissue-{number}&event=pull_request&per_page=100"])
    totals = {page["total_count"] for page in pages}
    rows = [row for page in pages for row in page["workflow_runs"]]
    if len(totals) != 1 or totals != {len(rows)} or len({row["id"] for row in rows}) != len(rows):
        raise ValueError("CI run inventory changed or was truncated during pagination")
    data["ci_unattributed_runs"] = sum(not row.get("pull_requests") for row in rows)
    for page in pages:
        for item in page["workflow_runs"]:
            # Do not attribute another PR's CI to this one, even if a branch
            # name is reused. Missing association remains unknown telemetry.
            if not any(row["number"] == record["pr"] for row in item.get("pull_requests", [])):
                continue
            for attempt in range(1, int(item["run_attempt"]) + 1):
                key = f"{item['id']}:{attempt}"
                if data["ci_runs"].get(key, {}).get("seconds") is not None:
                    continue
                run_data = item if attempt == item["run_attempt"] else gh_json(config.repo_root, [
                    "api", f"repos/{{owner}}/{{repo}}/actions/runs/{item['id']}/attempts/{attempt}"])
                elapsed = None
                if run_data.get("status") == "completed" and run_data.get("run_started_at") and run_data.get("updated_at"):
                    elapsed = integration.seconds(run_data["run_started_at"], run_data["updated_at"])
                data["ci_runs"][key] = {"id": item["id"], "attempt": attempt,
                                        "head_sha": run_data.get("head_sha"), "seconds": elapsed,
                                        "conclusion": run_data.get("conclusion")}
    data["ci_observed_at"] = integration.stamp()
    data.pop("ci_error", None)


def _metrics_observed_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return observed.astimezone(timezone.utc) if observed.tzinfo else None
    except ValueError:
        return None


def due_pr_metrics(state: dict, now: datetime) -> list[tuple[str, dict]]:
    """Never let permanently incomplete historical CI receipts block development.

    Live work is always eligible. Historical merged or closed PRs get at most
    two refreshes per wake, no more than once per 24 hours each, oldest first.
    A fresh status transition gets an immediate update despite recent CI polling.
    Missing CI attribution is kept visible; it is never falsely finalized.
    """
    live: list[tuple[str, dict]] = []
    merged: list[tuple[int, datetime, str, dict]] = []
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    for number, record in state["issues"].items():
        if (not record.get("pr") or not record.get("metrics")
                or record.get("metrics_finalized")):
            continue
        if record.get("status") not in {"merged", "pr_closed"}:
            live.append((number, record))
            continue
        data = record["metrics"]
        observed = _metrics_observed_at(data.get("ci_observed_at"))
        phase = _metrics_observed_at(data.get("phase_started_at"))
        attempted = _metrics_observed_at(record.get("metrics_last_attempt_at"))
        status_changed = (
            record.get("metrics_last_attempt_status") not in (None, record["status"])
            or (attempted is None and phase is not None
                and (observed is None or phase > observed))
        )
        last = attempted or observed
        if (not status_changed and last is not None
                and (now - last).total_seconds() < MERGED_METRICS_REFRESH_HOURS * 3600):
            continue
        merged.append((0 if status_changed else 1, last or epoch, number, record))
    merged.sort(key=lambda row: (row[0], row[1], int(row[2])))
    return live + [(number, record) for _, _, number, record
                   in merged[:MERGED_METRICS_PER_WAKE]]


def emit_pr_metrics(config: Config, state: dict) -> None:
    """Publish one replaceable JSON block per PR; telemetry never waives a gate."""
    integration.record_runs(state)
    now = utcnow()
    for number, record in due_pr_metrics(state, now):
        if record.get("status") in {"merged", "pr_closed"}:
            # Persist the retry clock even when GitHub publication fails. The
            # next wake may continue normal development instead of spinning.
            record["metrics_last_attempt_at"] = now.isoformat()
            record["metrics_last_attempt_status"] = record["status"]
        data = integration.metrics(record)
        try:
            collect_ci_metrics(config, record, number)
        except Exception as exc:
            data["ci_error"] = str(exc)[-1000:]
        payload = {"issue": int(number), "pr": record["pr"], "status": record["status"],
                   "trial": {"max_staged_depth": 1, "max_open_prs": integration.MAX_OPEN_PRS},
                   **integration.summary(record)}
        path = config.state_dir / "metrics" / f"pr-{record['pr']}.json"
        save_state(path, payload)
        start, end = "<!-- warcraftmap-agent-metrics -->", "<!-- /warcraftmap-agent-metrics -->"
        block = start + "\n```json\n" + json.dumps(payload, indent=2, sort_keys=True) + "\n```\n" + end
        try:
            view = gh_json(config.repo_root, ["pr", "view", str(record["pr"]), "--json", "body"])
            body = str(view.get("body") or "")
            updated = re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _: block,
                             body, flags=re.S) if start in body and end in body else body.rstrip() + "\n\n" + block
            if updated != body:
                body_path = path.with_suffix(".body.json")
                body_path.write_text(json.dumps({"body": updated}), encoding="utf-8")
                # Use the stable REST body endpoint without gh pr edit's
                # additional GraphQL metadata queries on older CLI versions.
                run(["gh", "api", "--method", "PATCH",
                     f"repos/{{owner}}/{{repo}}/pulls/{record['pr']}", "--input", str(body_path)],
                    cwd=config.repo_root, timeout=120)
            data.pop("publication_error", None)
            if (record["status"] == "merged" and not data.get("ci_error") and
                    not data.get("ci_unattributed_runs") and
                    all(row.get("seconds") is not None for row in data["ci_runs"].values())):
                record["metrics_finalized"] = True
        except Exception as exc:
            data["publication_error"] = str(exc)[-1000:]
            print(f"metrics warning for PR #{record['pr']}: {exc}", file=sys.stderr)
    save_state(config.state_dir / "state.json", state)


def main(argv: list[str] | None = None) -> int:
    global _worker_lock
    parser = argparse.ArgumentParser(description="Conservative GitHub-Issue-driven Codex worker")
    parser.add_argument("--dry-run", action="store_true", help="show the next eligible task without invoking Codex or changing GitHub")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path("~/.config/warcraftmap-agent.env").expanduser())
    args = parser.parse_args(argv)
    config = make_config(args.repo, args.config)
    config.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    # A read-only descriptor can hold flock on Linux. Children retain ownership
    # across controller crashes without receiving a writable state-directory FD.
    with os.fdopen(os.open(config.state_dir / "worker.lock", os.O_RDONLY | os.O_CREAT, 0o600), "r") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("another worker is active; exiting")
            return 0
        _worker_lock = lock
        state_path = config.state_dir / "state.json"
        state = load_state(state_path)
        integration.record_runs(state)
        state["runs"] = recent_runs(state["runs"], utcnow())
        # Audit and inspect full history on every wake, including a healthy queue
        # and cached design exhaustion. Optional work must not bypass closure.
        context = planning_context(config)
        reconcile_pr_claims(state, context["pull_requests"])
        closure = context["closure"]
        if closure.active:
            state.pop("planning_exhausted_for_blockers", None)
        closed_numbers = completed_dependency_numbers(context["issues"], context["pull_requests"])
        # PR recovery and merging must obey the same dependency/design gates
        # as implementation selection; a ready PR cannot bypass a missing rule.
        allowed_pr_issues = {int(row["number"]) for row in context["issues"]
                             if READY.match(row["title"]) and closure.permits_issue(row)
                             and issue_blocker_numbers(row) <= closed_numbers}
        if not args.dry_run and service_open_prs(config, state, allowed_pr_issues):
            # Next wake regenerates all audits on the post-merge main revision.
            save_state(state_path, state)
            emit_pr_metrics(config, state)
            return 0
        if not args.dry_run:
            emit_pr_metrics(config, state)
        promoted = promote_planned_issues(config, dry_run=args.dry_run, closure=closure)
        if args.dry_run:
            for issue in promoted:
                print(f"planned promotion: would make #{issue['number']} [agent-ready] {PLANNED.sub('', issue['title']).strip()}")
        if promoted and not args.dry_run:
            context["issues"] = list_history(config, "issue")
        open_issues = [item for item in context["issues"] if is_open(item)]
        issues = sorted((item for item in open_issues if READY.match(item["title"])),
                        key=lambda item: (item["createdAt"], item["number"]))
        # Repair the published predecessor before spending time on held work.
        if integration.staged_numbers(state):
            issues.sort(key=lambda item: 0 if state["issues"].get(str(item["number"]), {}).get("pr") else 1)
        reconcile_ready_issue_states(issues, state)
        reconcile_dependency_exhaustion(issues, state, closure, config.max_attempts)
        refresh_validation_repair_bases(config, state)
        needs_design = [item for item in open_issues if NEEDS_DESIGN.match(item["title"])]
        design_numbers = {int(item["number"]) for item in needs_design}
        # Dependencies on any open or inaccessible issue block execution, not
        # just needs-design issues. Audit prerequisites additionally gate closure.
        dependency_numbers = {number for item in issues for number in issue_blocker_numbers(item)} - closed_numbers
        selected = select_issue(
            issues, state, config.max_attempts, dependency_numbers,
            config.max_validation_repair_attempts,
            config.max_ci_repair_attempts, config.max_conflict_attempts, closure,
        )
        independent_ready_count = sum(not (issue_blocker_numbers(issue) & dependency_numbers) for issue in issues)
        refill_count = (min(QUEUE_TARGET, len(closure.actionable)) if closure.active else
                        queue_refill_count(independent_ready_count, bool(needs_design)))
        if integration.staged_numbers(state):
            refill_count = 0
            for number in integration.staged_numbers(state):
                held = state["issues"][str(number)]
                current = next((row for row in context["issues"] if row["number"] == number), None)
                if not current or not is_open(current) or not READY.match(current["title"]):
                    held["stage"]["hold_reason"] = "issue is closed, unavailable, planned or needs design; work preserved for review"
                print(f"staging slot: issue #{number}, {held['status']}, "
                      f"{held['stage'].get('hold_reason') or held.get('last_failure') or 'implementation reserved'}")
        if not closure.active and design_numbers and design_numbers == set(state.get("planning_exhausted_for_blockers", [])):
            refill_count = 0
        if args.dry_run:
            if selected:
                print(f"next task: #{selected['number']} {selected['title']} ({selected['url']})")
            elif refill_count:
                print(f"would plan up to {refill_count} {'closure repair' if closure.active else 'roadmap'} issue(s)")
            elif closure.active:
                print("release closure pending: repairs, dependencies or fresh audit evidence remain unresolved")
            elif needs_design:
                blocker = needs_design[0]
                print(f"no independent work; design blocked: #{blocker['number']} {blocker['title']} ({blocker['url']})")
            else:
                print("no eligible [agent-ready] issue")
            available, reason = budget_available(
                state["runs"],
                utcnow(),
                config.max_daily_tokens,
                config.max_weekly_tokens,
                config.max_daily_runs,
                config.max_weekly_runs,
            )
            print(reason)
            return 0
        # Never let queue replenishment pre-empt implementation work that is
        # already ready and independent of any open design blocker.
        if refill_count and selected is None:
            available, reason = budget_available(
                state["runs"], utcnow(), config.max_daily_tokens,
                config.max_weekly_tokens, config.max_daily_runs, config.max_weekly_runs,
            )
            if not available:
                save_state(state_path, state)
                print(reason)
                return 0
            run_entry = {
                "timestamp": utcnow().isoformat().replace("+00:00", "Z"),
                "tokens": None,
                "telemetry": "pending",
                "issue": None,
                "kind": "planning",
                "model": config.model,
            }
            state["runs"].append(run_entry)
            save_state(state_path, state)
            try:
                plan = invoke_planner(config, context, refill_count, run_entry)
                existing_titles = [item["title"] for item in context["issues"]]
                existing_titles.extend(item["title"] for item in context["pull_requests"])
                existing_questions = [question for item in context["issues"] if (question := decision_question(item.get("body") or ""))]
                items = prepare_plan_items(plan, existing_titles, refill_count, existing_questions, closure)
                if plan.get("outcome") == "exhausted":
                    latest = planning_context(config)["closure"]
                    if latest.revision != closure.revision or latest.active:
                        raise ValueError("closure changed during planning; exhausted cannot be accepted")
                created = create_plan_issues(config, items, closure)
                if plan.get("outcome") == "exhausted":
                    state["planning_exhausted_for_blockers"] = sorted(design_numbers)
                    print("roadmap exhausted; no further planned work remains")
                else:
                    state.pop("planning_exhausted_for_blockers", None)
                    print(f"queue replenishment created {created} issue(s)")
            except Exception as exc:
                print(f"planning failed: {exc}", file=sys.stderr)
            save_state(state_path, state)
            return 0
        selected = select_issue(
            issues, state, config.max_attempts, dependency_numbers,
            config.max_validation_repair_attempts,
            config.max_ci_repair_attempts, config.max_conflict_attempts, closure,
        )
        if not selected:
            save_state(state_path, state)
            print("release closure pending; no unblocked repair is ready" if closure.active else "no eligible [agent-ready] issue")
            return 0
        # A closed issue is insufficient while its implementing PR remains
        # unmerged. Recheck before any Codex quota is charged, even if the
        # earlier queue snapshot considered the issue eligible.
        if issue_blocker_numbers(selected) and dependency_completion_receipt(selected, closure) is None:
            print(f"issue #{selected['number']}: waiting for verified prerequisite merges")
            save_state(state_path, state)
            return 0
        record = issue_record(state, selected["number"])
        if record.get("status") == "staged":
            # A completed implementation survives crashes and quota exhaustion.
            # Integrating it does not invoke Codex; a real repair still uses the
            # existing quota and separate attempt lanes on a subsequent wake.
            worktree = Path(record["stage"]["worktree"])
            if not worktree.is_dir():
                defer_integration(config, state, selected, record, "reserved worktree is missing; recovery requires attention")
                return 0
            try:
                complete_candidate(config, state, selected, record, worktree, record["stage"]["branch"])
            except Exception as exc:
                record_attempt_failure(config, record, exc)
            save_state(state_path, state)
            emit_pr_metrics(config, state)
            return 0
        available, reason = budget_available(
            state["runs"],
            utcnow(),
            config.max_daily_tokens,
            config.max_weekly_tokens,
            config.max_daily_runs,
            config.max_weekly_runs,
        )
        if not available:
            save_state(state_path, state)
            print(reason)
            return 0
        worktree, branch = worktree_for(config, selected["number"])
        kind = repair_kind(record)
        if kind and not record.get("repair_kind"):
            record["repair_kind"] = kind
        try:
            predecessors = predecessor_snapshot(config, state, context["pull_requests"], record)
            reserve_stage(config, state, selected, record, worktree, predecessors)
            save_state(state_path, state)
            prepare_repair(config, worktree, selected["number"], record)
            # Merging main can switch lanes. Check and charge the resulting
            # budget, never the validation budget that led us to this merge.
            attempt_key, attempts, limit = attempt_budget(
                record, config.max_attempts, config.max_validation_repair_attempts,
                config.max_ci_repair_attempts, config.max_conflict_attempts,
            )
            if attempts >= limit:
                raise RuntimeError("No repair attempts remain before Codex launch.")
            record[attempt_key] = attempts + 1
            record["status"] = "working"
            integration.phase(record, "implementation")
            run_entry = {
                "id": uuid.uuid4().hex,
                "timestamp": utcnow().isoformat().replace("+00:00", "Z"),
                "tokens": None,
                "telemetry": "pending",
                "issue": selected["number"],
                "model": config.model,
            }
            state["runs"].append(run_entry)
            # Persist the lane and charge the run cap before launch, including
            # crashes/timeouts. Preparation without a launch consumes neither.
            save_state(state_path, state)
            conflicts: list[str] = []
            try:
                result = invoke_codex(config, worktree, selected, record, run_entry)
            finally:
                integration.record_runs(state)
                if record.get("repair_kind") == "merge_conflict":
                    conflicts = unmerged_paths(worktree)
                    # A timeout/blocker after resolving the merge must not
                    # strand validation behind an exhausted conflict budget.
                    resume_validation_repair(record, conflicts)
            # Persist token telemetry before validation/PR work.
            save_state(state_path, state)
            if result["outcome"] == "needs_design":
                mark_needs_design(config, selected, result["question"])
                record["status"] = "needs_design"
            elif result["outcome"] == "blocked":
                detail = (result.get("summary") or result.get("question") or "technical blocker").strip()
                # If Codex reports an unmerged declared prerequisite, do not
                # spend every initial attempt repeating that same observation.
                if (issue_blocker_numbers(selected)
                        and re.search(r"\b(?:unmerged|not merged)\b", detail, re.I)):
                    receipt = dependency_completion_receipt(selected, closure)
                    record["status"] = "waiting_dependency" if receipt is None else "failed"
                    record["last_failure"] = f"Codex implementation blocked: {detail}"
                    if receipt is not None:
                        # The dependency is already merged: this is a stale
                        # Codex/worktree assertion, not license to retry 14x.
                        record["dependency_recovery_receipt"] = json.dumps(
                            receipt, sort_keys=True, separators=(",", ":")
                        )
                    save_state(state_path, state)
                    print(f"issue #{selected['number']}: prerequisite gate unresolved; Codex paused")
                    return 0
                raise RuntimeError(f"Codex implementation blocked: {detail}")
            else:
                if conflicts:
                    raise RuntimeError(
                        "Merge conflict repair required: unmerged paths remain after Codex: "
                        + ", ".join(conflicts)
                    )
                complete_candidate(config, state, selected, record, worktree, branch)
        except Exception as exc:
            record_attempt_failure(config, record, exc)
        save_state(state_path, state)
        emit_pr_metrics(config, state)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

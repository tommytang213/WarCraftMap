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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .budget import budget_available, recent_runs, usage_summary


READY = re.compile(r"^\[agent-ready\]\s+", re.IGNORECASE)
NEEDS_DESIGN = re.compile(r"^\[needs-design\]\s+", re.IGNORECASE)
PLANNED = re.compile(r"^\[planned\]\s+", re.IGNORECASE)
PLANNED_PHASE = re.compile(r"^\[planned\]\s+Phase\s+(\d+)\s*:", re.IGNORECASE)
DEPENDENCY = re.compile(r"(?im)^\s*Depends on:\s*#(\d+)\b")
QUEUE_REFILL_THRESHOLD = 3
QUEUE_TARGET = 10


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
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"command failed ({result.returncode}): {shlex.join(args)}\n{detail}")
    return result


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 2, "runs": [], "issues": {}}

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
    elif version != 2:
        raise ValueError("unsupported worker state version")

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
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def gh_json(repo: Path, args: list[str]) -> Any:
    result = run(["gh", *args], cwd=repo)
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
) -> list[dict[str, Any]]:
    """Find reservations whose preceding phase and explicit dependencies are complete."""
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


def promote_planned_issues(config: Config, dry_run: bool = False) -> list[dict[str, Any]]:
    """Promote eligible existing issues in place and return those issues."""
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
        planned, roadmap_path(config.repo_root).read_text(encoding="utf-8"), dependency_states,
    )
    if not dry_run:
        for issue in eligible:
            title = PLANNED.sub("", issue["title"]).strip()
            run(["gh", "issue", "edit", str(issue["number"]), "--title", f"[agent-ready] {title}"], cwd=config.repo_root)
    return eligible


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
) -> list[dict[str, str]]:
    """Validate/deduplicate a planner result while preserving roadmap order."""
    if plan.get("outcome") == "exhausted":
        return []
    seen = {normalized_work_title(title) for title in existing_titles}
    seen_questions = {normalized_question(question) for question in (existing_questions or []) if question}
    prepared: list[dict[str, str]] = []
    design_seen = False
    for raw in plan.get("issues", []):
        if len(prepared) >= limit:
            break
        kind = raw.get("kind")
        clean_title = READY.sub("", NEEDS_DESIGN.sub("", PLANNED.sub("", str(raw.get("title", "")).strip()))).strip()
        key = normalized_work_title(clean_title)
        if not clean_title or not key or key in seen:
            continue
        seen.add(key)
        if kind == "needs-design":
            question = str(raw.get("question", "")).strip()
            if not question or question.count("?") != 1:
                raise ValueError("a needs-design plan item must contain one exact question")
            question_key = normalized_question(question)
            if question_key in seen_questions:
                continue
            seen_questions.add(question_key)
            design_seen = True
            prepared.append({"title": f"[needs-design] {clean_title}", "body": str(raw.get("body", "")).strip() + "\n\n## Decision required\n\n" + question, "question": question})
            continue
        if kind != "agent-ready":
            raise ValueError(f"unsupported planned issue kind: {kind!r}")
        body = str(raw.get("body", "")).strip()
        if design_seen and "independent of" not in body.casefold():
            continue
        if "acceptance criteria" not in body.casefold() or "automated validation" not in body.casefold():
            raise ValueError("agent-ready plan items require acceptance criteria and automated validation")
        prepared.append({"title": f"[agent-ready] {clean_title}", "body": body, "question": ""})
    return prepared


def planning_context(config: Config) -> dict[str, Any]:
    """Collect issue/PR history used with the authoritative repository files."""
    issues = gh_json(config.repo_root, ["issue", "list", "--state", "all", "--limit", str(config.issue_limit), "--json", "number,title,body,state,url,createdAt,closedAt"])
    prs = gh_json(config.repo_root, ["pr", "list", "--state", "all", "--limit", str(config.issue_limit), "--json", "number,title,body,state,url,createdAt,mergedAt,closedAt"])
    history = run(["git", "log", "--oneline", "--decorate", "-100"], cwd=config.repo_root).stdout
    status = run(["git", "status", "--short"], cwd=config.repo_root).stdout
    return {"issues": issues, "pull_requests": prs, "git_history": history, "git_status": status}


def planning_prompt(context: dict[str, Any], requested: int) -> str:
    return f"""Plan the next implementation-sized GitHub issues for WarCraftMap.

Read ROADMAP.md, DESIGN_LOCK.md, ARCHITECTURE.md, AGENTS.md, and the current repository before planning. Treat those files and the GitHub/repository history below as authoritative. Preserve roadmap and dependency order; choose only the next incomplete work that is actually unblocked. Do not duplicate open, completed, superseded, or PR-represented work.

Return at most {requested} items, in implementation order. Every agent-ready body must include explicit `## Acceptance criteria` and `## Automated validation` sections and must not require player QA. An open needs-design issue blocks only work that materially depends on its decision: continue planning unrelated roadmap work, and explicitly state in each such issue body why it is independent of the open decision. Never skip a real dependency or invent a design choice. When a material decision is missing, return one needs-design item with exactly one decision question, then continue only with work explicitly independent of it. Do not duplicate an unresolved decision already represented by an open needs-design issue. Do not create repeated per-region needs-design questions for geography/content scope when DESIGN_LOCK.md already provides a reusable global rule; derive region-specific boundaries, compression, historical coverage, settlements, routes, terrain, and borders from the locked rules plus historical/geographic evidence and performance constraints. Ask the player only for a genuinely new material gameplay/design choice that cannot be resolved from those authorities. If no independent planned work remains, return outcome `exhausted` and no issues. Do not edit files or interact with GitHub.

GitHub and repository history:
{json.dumps(context, sort_keys=True)}
"""


def invoke_planner(config: Config, context: dict[str, Any], requested: int, run_entry: dict[str, Any]) -> dict[str, Any]:
    schema = config.repo_root / "automation" / "codex-plan.schema.json"
    output = config.state_dir / "last-codex-plan.json"
    output.unlink(missing_ok=True)
    command = build_codex_command(config, config.repo_root, schema, output)
    process = subprocess.Popen(
        command, cwd=config.repo_root, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        start_new_session=True, env=os.environ.copy(),
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


def create_plan_issues(config: Config, items: list[dict[str, str]]) -> int:
    created = 0
    for item in items:
        current = gh_json(config.repo_root, ["issue", "list", "--state", "all", "--limit", str(config.issue_limit), "--json", "number,title,body,url,state"] )
        prs = gh_json(config.repo_root, ["pr", "list", "--state", "all", "--limit", str(config.issue_limit), "--json", "title"] )
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
        result = run(["gh", "issue", "create", "--title", item["title"], "--body", item["body"]], cwd=config.repo_root)
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
) -> dict[str, Any] | None:
    blockers = open_design_numbers or set()
    for issue in issues:
        if not READY.match(str(issue.get("title", ""))):
            continue
        if issue_blocker_numbers(issue) & blockers:
            continue
        record = state["issues"].get(str(issue["number"]), {})
        if record.get("status") in {"pr_open", "needs_design", "merged"}:
            continue
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
    output = config.state_dir / "last-codex-result.json"
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
    )
    stdout = ""
    timed_out = False
    try:
        stdout, _ = process.communicate(
            codex_prompt(issue, record.get("last_failure", ""), repair_kind=repair_kind(record)),
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
        log = (
            config.state_dir
            / "logs"
            / f"issue-{issue['number']}-attempt-{record['attempts']}.jsonl"
        )
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
    base_oid = remote_branch_oid(config.repo_root, branch)
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
    else:
        return

    if record["repair_kind"] == "merge_conflict":
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


def publish(config: Config, issue: dict[str, Any], worktree: Path, branch: str) -> int:
    status = run(["git", "status", "--porcelain"], cwd=worktree).stdout
    if status.strip():
        run(["git", "add", "-A"], cwd=worktree)
        run(["git", "commit", "-m", f"Implement issue #{issue['number']}: {READY.sub('', issue['title'])}"], cwd=worktree)
    else:
        upstream = f"origin/{default_branch(config.repo_root)}"
        ahead = run(["git", "rev-list", "--count", f"{upstream}..HEAD"], cwd=worktree).stdout.strip()
        if int(ahead or "0") < 1:
            raise RuntimeError("Codex reported completion but made no changes")
    run(["git", "push", "--set-upstream", "origin", branch], cwd=worktree)
    existing = run(
        ["gh", "pr", "list", "--head", branch, "--state", "open", "--json", "number", "--jq", ".[0].number"],
        cwd=worktree,
    ).stdout.strip()
    if existing:
        return int(existing)
    result = run(["gh", "pr", "create", "--base", default_branch(config.repo_root), "--head", branch, "--title", READY.sub("", issue["title"]), "--body", f"Closes #{issue['number']}\n\nCreated by the low-priority WarCraftMap autonomous worker after repository validation."], cwd=worktree)
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
    errors: list[str] = []
    try:
        run(["gh", "issue", "close", str(number), "--reason", "completed"], cwd=config.repo_root)
    except Exception as exc:
        errors.append(f"could not close merged issue #{number}: {exc}")
    errors.extend(cleanup_merged_issue(config, int(number)))
    if errors:
        record["cleanup_errors"] = errors
    else:
        record.pop("cleanup_errors", None)


def service_open_prs(config: Config, state: dict[str, Any]) -> bool:
    """Merge or recover one tracked open PR per worker invocation."""
    for number, record in state["issues"].items():
        pr = record.get("pr")
        if not pr:
            continue
        failed_conflict = (
            record.get("status") == "failed"
            and "unmergeable because main conflicts" in str(record.get("last_failure", ""))
        )
        if record.get("status") != "pr_open" and not failed_conflict:
            continue
        view = gh_json(config.repo_root, ["pr", "view", str(pr), "--json", "state,mergeStateStatus,mergeable,statusCheckRollup,baseRefName"])
        if view["state"] == "MERGED":
            finish_merged_issue(config, number, record)
            return True
        if view["state"] == "CLOSED":
            record["status"] = "failed"
            record["last_failure"] = f"PR #{pr} was closed without merging; manual review is required."
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
        run(build_pr_merge_command(int(pr)), cwd=config.repo_root)
        finish_merged_issue(config, number, record)
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Conservative GitHub-Issue-driven Codex worker")
    parser.add_argument("--dry-run", action="store_true", help="show the next eligible task without invoking Codex or changing GitHub")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path("~/.config/warcraftmap-agent.env").expanduser())
    args = parser.parse_args(argv)
    config = make_config(args.repo, args.config)
    config.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (config.state_dir / "worker.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("another worker is active; exiting")
            return 0
        state_path = config.state_dir / "state.json"
        state = load_state(state_path)
        state["runs"] = recent_runs(state["runs"], utcnow())
        promoted = promote_planned_issues(config, dry_run=args.dry_run)
        if args.dry_run:
            for issue in promoted:
                print(f"planned promotion: would make #{issue['number']} [agent-ready] {PLANNED.sub('', issue['title']).strip()}")
        issues = list_issues(config)
        reconcile_ready_issue_states(issues, state)
        refresh_validation_repair_bases(config, state)
        needs_design = list_needs_design_issues(config)
        design_numbers = {int(item["number"]) for item in needs_design}
        selected = select_issue(
            issues, state, config.max_attempts, design_numbers,
            config.max_validation_repair_attempts,
            config.max_ci_repair_attempts, config.max_conflict_attempts,
        )
        independent_ready_count = sum(not (issue_blocker_numbers(issue) & design_numbers) for issue in issues)
        refill_count = queue_refill_count(independent_ready_count, bool(needs_design))
        if design_numbers and design_numbers == set(state.get("planning_exhausted_for_blockers", [])):
            refill_count = 0
        if args.dry_run:
            if selected:
                print(f"next task: #{selected['number']} {selected['title']} ({selected['url']})")
            elif refill_count:
                print(f"queue low: would plan up to {refill_count} issue(s) to reach {QUEUE_TARGET}")
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
        if service_open_prs(config, state):
            save_state(state_path, state)
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
                context = planning_context(config)
                plan = invoke_planner(config, context, refill_count, run_entry)
                existing_titles = [item["title"] for item in context["issues"]]
                existing_titles.extend(item["title"] for item in context["pull_requests"])
                existing_questions = [question for item in context["issues"] if (question := decision_question(item.get("body") or ""))]
                items = prepare_plan_items(plan, existing_titles, refill_count, existing_questions)
                created = create_plan_issues(config, items)
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
            issues, state, config.max_attempts, design_numbers,
            config.max_validation_repair_attempts,
            config.max_ci_repair_attempts, config.max_conflict_attempts,
        )
        if not selected:
            save_state(state_path, state)
            print("no eligible [agent-ready] issue")
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
        record = issue_record(state, selected["number"])
        worktree, branch = worktree_for(config, selected["number"])
        kind = repair_kind(record)
        if kind and not record.get("repair_kind"):
            record["repair_kind"] = kind
        try:
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
            run_entry = {
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
                raise RuntimeError(f"Codex implementation blocked: {detail}")
            else:
                if conflicts:
                    raise RuntimeError(
                        "Merge conflict repair required: unmerged paths remain after Codex: "
                        + ", ".join(conflicts)
                    )
                try:
                    run_checks(config, worktree)
                except Exception as exc:
                    if not record.get("pr"):
                        record["repair_kind"] = "validation"
                        record["validation_failure"] = str(exc)[-4000:]
                        branch_name = default_branch(config.repo_root)
                        base_oid = remote_branch_oid(config.repo_root, branch_name)
                        if base_oid:
                            record["validation_base_oid"] = base_oid
                    raise
                existing_pr = record.get("pr")
                if existing_pr:
                    push_existing_pr_repair(worktree, selected["number"], int(existing_pr))
                    record["status"] = "pr_open"
                else:
                    record["pr"] = publish(config, selected, worktree, branch)
                    record["status"] = "pr_open"
                record.pop("last_failure", None)
                record.pop("repair_kind", None)
                record.pop("validation_failure", None)
        except Exception as exc:
            attempt_key, attempts, limit = attempt_budget(
                record, config.max_attempts, config.max_validation_repair_attempts,
                config.max_ci_repair_attempts, config.max_conflict_attempts,
            )
            record["status"] = "failed" if attempts >= limit else "repair"
            record["last_failure"] = str(exc)[-4000:]
            if attempts >= limit:
                lane = {
                    "validation": "validation-repair", "ci": "CI-repair",
                    "merge_conflict": "conflict-repair",
                }.get(repair_kind(record), "implementation")
                record["last_failure"] += f"\nThe {lane} attempt limit ({limit}) is exhausted."
            print(f"attempt failed: {exc}", file=sys.stderr)
        save_state(state_path, state)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

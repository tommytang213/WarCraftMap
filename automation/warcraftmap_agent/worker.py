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

from .budget import budget_available, recent_invocations


READY = re.compile(r"^\[agent-ready\]\s+", re.IGNORECASE)
@dataclass
class Config:
    repo_root: Path
    state_dir: Path
    model: str = "gpt-5.6-sol"
    max_daily: int = 1
    max_weekly: int = 5
    timeout_minutes: int = 45
    max_attempts: int = 3
    checks_command: str = "./automation/run_checks.sh"
    issue_limit: int = 100


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
    state = Path(values.get("WARCRAFTMAP_AGENT_STATE_DIR", "~/.local/state/warcraftmap-agent")).expanduser()
    return Config(
        repo_root=repo_root.resolve(),
        state_dir=state.resolve(),
        model=values.get("WARCRAFTMAP_AGENT_MODEL", "gpt-5.6-sol"),
        max_daily=positive_int(values, "WARCRAFTMAP_AGENT_MAX_DAILY", 1),
        max_weekly=positive_int(values, "WARCRAFTMAP_AGENT_MAX_WEEKLY", 5),
        timeout_minutes=positive_int(values, "WARCRAFTMAP_AGENT_TIMEOUT_MINUTES", 45),
        max_attempts=positive_int(values, "WARCRAFTMAP_AGENT_MAX_ATTEMPTS_PER_ISSUE", 3),
        checks_command=values.get("WARCRAFTMAP_AGENT_CHECKS_COMMAND", "./automation/run_checks.sh"),
        issue_limit=positive_int(values, "WARCRAFTMAP_AGENT_ISSUE_LIMIT", 100),
    )


def run(args: list[str], *, cwd: Path, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"command failed ({result.returncode}): {shlex.join(args)}\n{detail}")
    return result


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "invocations": [], "issues": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError("unsupported worker state version")
    data.setdefault("invocations", [])
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


def list_issues(config: Config) -> list[dict[str, Any]]:
    issues = gh_json(config.repo_root, ["issue", "list", "--state", "open", "--limit", str(config.issue_limit), "--json", "number,title,body,url,createdAt"])
    return sorted((item for item in issues if READY.match(item["title"])), key=lambda item: (item["createdAt"], item["number"]))


def select_issue(issues: list[dict[str, Any]], state: dict[str, Any], max_attempts: int) -> dict[str, Any] | None:
    for issue in issues:
        record = state["issues"].get(str(issue["number"]), {})
        if record.get("status") in {"pr_open", "needs_design", "merged"}:
            continue
        if int(record.get("attempts", 0)) >= max_attempts:
            continue
        return issue
    return None


def issue_record(state: dict[str, Any], number: int) -> dict[str, Any]:
    return state["issues"].setdefault(str(number), {"attempts": 0, "status": "queued"})


def comment(config: Config, number: int, body: str) -> None:
    run(["gh", "issue", "comment", str(number), "--body", body], cwd=config.repo_root)


def mark_needs_design(config: Config, issue: dict[str, Any], question: str) -> None:
    clean = READY.sub("", issue["title"]).strip()
    run(["gh", "issue", "edit", str(issue["number"]), "--title", f"[needs-design] {clean}"], cwd=config.repo_root)
    comment(config, issue["number"], "Autonomous work paused because a material design decision is required:\n\n" + question)


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


def codex_prompt(issue: dict[str, Any], repair_context: str) -> str:
    return f"""Implement GitHub issue #{issue['number']} in this isolated WarCraftMap worktree.

Title: {issue['title']}
Body:
{issue.get('body') or '(empty)'}

Follow AGENTS.md and the Age of Sail design documentation. Source and scenario data are authoritative. Do not ask the player to perform incremental testing. Do not commit, push, create or edit GitHub issues/PRs, install services, alter global tooling, or touch anything outside this worktree. Run relevant automated tests. Never invent a material game-design choice: return outcome \"needs_design\" with one exact question if blocked by one.

Previous failure context, if any:
{repair_context or '(none)'}

Return the required JSON result. Use outcome \"complete\" only when the implementation is ready for repository validation."""


def invoke_codex(config: Config, worktree: Path, issue: dict[str, Any], record: dict[str, Any]) -> dict[str, str]:
    schema = config.repo_root / "automation" / "codex-result.schema.json"
    output = config.state_dir / "last-codex-result.json"
    command = ["codex", "exec", "--sandbox", "workspace-write", "--approve-for-me", "--model", config.model, "--cd", str(worktree), "--output-schema", str(schema), "--output-last-message", str(output), "-"]
    env = os.environ.copy()
    process = subprocess.Popen(command, cwd=worktree, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True, env=env)
    try:
        stdout, _ = process.communicate(codex_prompt(issue, record.get("last_failure", "")), timeout=config.timeout_minutes * 60)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
        raise RuntimeError(f"Codex exceeded {config.timeout_minutes}-minute timeout")
    log = config.state_dir / "logs" / f"issue-{issue['number']}-attempt-{record['attempts']}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(stdout, encoding="utf-8")
    if process.returncode:
        raise RuntimeError(f"Codex exited {process.returncode}; see {log}")
    return json.loads(output.read_text(encoding="utf-8"))


def run_checks(config: Config, worktree: Path) -> None:
    command = shlex.split(config.checks_command)
    if not command:
        raise ValueError("WARCRAFTMAP_AGENT_CHECKS_COMMAND may not be empty")
    run(command, cwd=worktree, timeout=config.timeout_minutes * 60)


def publish(config: Config, issue: dict[str, Any], worktree: Path, branch: str) -> int:
    status = run(["git", "status", "--porcelain"], cwd=worktree).stdout
    if not status.strip():
        raise RuntimeError("Codex reported completion but made no changes")
    run(["git", "add", "-A"], cwd=worktree)
    run(["git", "commit", "-m", f"Implement issue #{issue['number']}: {READY.sub('', issue['title'])}"], cwd=worktree)
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


def service_open_prs(config: Config, state: dict[str, Any]) -> bool:
    """Merge one ready PR. Failed/pending PRs remain for a later timer run."""
    for number, record in state["issues"].items():
        pr = record.get("pr")
        if record.get("status") != "pr_open" or not pr:
            continue
        view = gh_json(config.repo_root, ["pr", "view", str(pr), "--json", "state,mergeStateStatus,statusCheckRollup"])
        if view["state"] == "MERGED":
            record["status"] = "merged"
            return True
        if view["state"] == "CLOSED":
            record["status"] = "failed"
            record["last_failure"] = f"PR #{pr} was closed without merging; manual review is required."
            return True
        checks = view.get("statusCheckRollup") or []
        failed = any(check_state(item) == "failed" for item in checks)
        pending = any(check_state(item) == "pending" for item in checks)
        if failed:
            record["status"] = "repair"
            record["last_failure"] = f"GitHub CI failed on PR #{pr}. Inspect it with gh pr checks {pr} and repair the implementation."
            return True
        if pending:
            continue
        if view["mergeStateStatus"] not in {"CLEAN", "HAS_HOOKS", "UNSTABLE"}:
            continue
        if checks:
            result = run(["gh", "pr", "checks", str(pr), "--required"], cwd=config.repo_root, check=False)
            if result.returncode != 0:
                continue
        run(["gh", "pr", "merge", str(pr), "--merge", "--delete-branch"], cwd=config.repo_root)
        record["status"] = "merged"
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
        state["invocations"] = recent_invocations(state["invocations"], utcnow())
        issues = list_issues(config)
        selected = select_issue(issues, state, config.max_attempts)
        if args.dry_run:
            if selected:
                print(f"next task: #{selected['number']} {selected['title']} ({selected['url']})")
            else:
                print("no eligible [agent-ready] issue")
            available, reason = budget_available(state["invocations"], utcnow(), config.max_daily, config.max_weekly)
            print(reason)
            return 0
        if service_open_prs(config, state):
            save_state(state_path, state)
            return 0
        selected = select_issue(issues, state, config.max_attempts)
        if not selected:
            save_state(state_path, state)
            print("no eligible [agent-ready] issue")
            return 0
        available, reason = budget_available(state["invocations"], utcnow(), config.max_daily, config.max_weekly)
        if not available:
            save_state(state_path, state)
            print(reason)
            return 0
        record = issue_record(state, selected["number"])
        worktree, branch = worktree_for(config, selected["number"])
        record["attempts"] = int(record.get("attempts", 0)) + 1
        record["status"] = "working"
        state["invocations"].append(utcnow().isoformat().replace("+00:00", "Z"))
        save_state(state_path, state)  # Charge quota before launch, including crashes/timeouts.
        try:
            result = invoke_codex(config, worktree, selected, record)
            if result["outcome"] == "needs_design":
                mark_needs_design(config, selected, result["question"])
                record["status"] = "needs_design"
            else:
                run_checks(config, worktree)
                existing_pr = record.get("pr")
                if existing_pr:
                    run(["git", "add", "-A"], cwd=worktree)
                    run(["git", "commit", "-m", f"Repair PR #{existing_pr} for issue #{selected['number']}"], cwd=worktree)
                    run(["git", "push"], cwd=worktree)
                    record["status"] = "pr_open"
                else:
                    record["pr"] = publish(config, selected, worktree, branch)
                    record["status"] = "pr_open"
                record.pop("last_failure", None)
        except Exception as exc:
            record["status"] = "failed" if record["attempts"] >= config.max_attempts else "repair"
            record["last_failure"] = str(exc)[-4000:]
            print(f"attempt failed: {exc}", file=sys.stderr)
        save_state(state_path, state)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

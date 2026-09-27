"""Conservatively fast-forward the controller checkout before worker startup."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .worker import load_env, run


def _git_path(repo: Path, name: str) -> Path:
    value = run(["git", "rev-parse", "--path-format=absolute", name], cwd=repo).stdout.strip()
    return Path(value).resolve()


def update_controller(repo: Path, configured_branch: str | None = None) -> bool:
    """Fast-forward a clean primary checkout, returning whether it was updated."""
    repo = repo.resolve()
    try:
        git_dir = _git_path(repo, "--git-dir")
        common_dir = _git_path(repo, "--git-common-dir")
        if git_dir != common_dir:
            print(f"self-update skipped: {repo} is an isolated Git worktree", file=sys.stderr)
            return False
        if run(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=repo).stdout:
            print("self-update skipped: controller checkout has local changes", file=sys.stderr)
            return False
        current = run(["git", "branch", "--show-current"], cwd=repo).stdout.strip()
        branch = configured_branch
        if not branch:
            default = run(["git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], cwd=repo, check=False)
            if default.returncode:
                print("self-update skipped: origin's default branch is unknown", file=sys.stderr)
                return False
            branch = default.stdout.strip().removeprefix("origin/")
        if not branch or current != branch:
            print(f"self-update skipped: controller is on {current or 'detached HEAD'}, expected {branch or 'a configured branch'}", file=sys.stderr)
            return False
        fetch = run(["git", "fetch", "--prune", "origin", branch], cwd=repo, check=False)
        if fetch.returncode:
            print(f"self-update skipped: fetch failed: {(fetch.stderr or fetch.stdout).strip()}", file=sys.stderr)
            return False
        remote = f"origin/{branch}"
        if run(["git", "merge-base", "--is-ancestor", "HEAD", remote], cwd=repo, check=False).returncode:
            print(f"self-update skipped: HEAD cannot fast-forward to {remote}", file=sys.stderr)
            return False
        if run(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=repo).stdout:
            print("self-update skipped: controller changed during fetch", file=sys.stderr)
            return False
        before = run(["git", "rev-parse", "HEAD"], cwd=repo).stdout.strip()
        merge = run(["git", "merge", "--ff-only", remote], cwd=repo, check=False)
        if merge.returncode:
            print(f"self-update skipped: fast-forward failed: {(merge.stderr or merge.stdout).strip()}", file=sys.stderr)
            return False
        after = run(["git", "rev-parse", "HEAD"], cwd=repo).stdout.strip()
        if before != after:
            print(f"self-update: fast-forwarded {branch} to {after[:12]}")
        return before != after
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"self-update skipped: {exc}", file=sys.stderr)
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path("~/.config/warcraftmap-agent.env").expanduser())
    args, _ = parser.parse_known_args(argv)
    try:
        branch = load_env(args.config).get("WARCRAFTMAP_AGENT_CONTROLLER_BRANCH")
    except (OSError, ValueError) as exc:
        print(f"self-update skipped: could not read configuration: {exc}", file=sys.stderr)
        return 0
    update_controller(args.repo, branch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

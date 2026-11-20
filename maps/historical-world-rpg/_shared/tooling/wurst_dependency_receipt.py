"""Log a bounded observation of Grill's installed standard library.

This receipt is diagnostic only. It is never input to build or release gates.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


MAX_TRACKED_FILES = 10000
MAX_TRACKED_BYTES = 512 * 1024 * 1024
RECEIPT_LINE = re.compile(
    r"WurstStdlib2 install receipt: status=(?:unverified reason=[a-z-]+|"
    r"observed-clean revision=[0-9a-f]{40} trackedSha256=[0-9a-f]{64} "
    r"trackedFiles=[1-9][0-9]{0,5} evidenceOnly=true)"
)


def _git(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "--no-optional-locks", "-C", str(root), *args], check=True, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, timeout=15,
    ).stdout


def _hash_file(path: Path, remaining: int) -> tuple[str, int]:
    hasher = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > remaining:
                raise ValueError("tracked-bytes-limit")
            hasher.update(chunk)
    return hasher.hexdigest(), size


def _observe(compile_root: Path) -> tuple[str, str, int]:
    """Hash sorted [relative tracked path, SHA-256 of file bytes] JSON rows."""
    dependencies = compile_root / "_build" / "dependencies"
    if not dependencies.is_dir():
        raise ValueError("dependency-absent")
    candidates = [p for p in dependencies.iterdir()
                  if p.is_dir() and not p.is_symlink() and p.name.lower() == "wurststdlib2"]
    if len(candidates) != 1:
        raise ValueError("dependency-absent-or-ambiguous")
    root = candidates[0]
    if Path(os.fsdecode(_git(root, "rev-parse", "--show-toplevel").strip())).resolve() != root.resolve():
        raise ValueError("unexpected-git-root")
    revision = _git(root, "rev-parse", "--verify", "HEAD").decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("invalid-revision")
    if _git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("working-tree-dirty")
    paths = sorted(set(filter(None, _git(root, "ls-files", "-z").split(b"\0"))))
    if not paths:
        raise ValueError("empty-tracked-tree")
    if len(paths) > MAX_TRACKED_FILES:
        raise ValueError("tracked-files-limit")
    rows = []
    remaining = MAX_TRACKED_BYTES
    for raw in paths:
        name = os.fsdecode(raw)
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("invalid-tracked-path")
        file = root / path
        if file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(root.resolve()):
            raise ValueError("unsupported-tracked-file")
        digest, size = _hash_file(file, remaining)
        remaining -= size
        rows.append([name, digest])
    if (_git(root, "rev-parse", "--verify", "HEAD").decode("ascii").strip() != revision or
            _git(root, "status", "--porcelain", "--untracked-files=all")):
        raise ValueError("dependency-changed-during-read")
    digest = hashlib.sha256(json.dumps(rows, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
    return revision, digest, len(rows)


def _emit_installed_stdlib(compile_root: Path) -> None:
    """Child process: print only fixed-format provenance or a reason code."""
    try:
        revision, digest, count = _observe(compile_root)
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError) as error:
        reason = str(error) if isinstance(error, ValueError) and re.fullmatch(r"[a-z-]+", str(error)) else "inspection-unavailable"
        print(f"WurstStdlib2 install receipt: status=unverified reason={reason}", flush=True)
        return
    print(f"WurstStdlib2 install receipt: status=observed-clean revision={revision} "
          f"trackedSha256={digest} trackedFiles={count} evidenceOnly=true", flush=True)


def log_installed_stdlib(compile_root: Path) -> None:
    """Bound diagnostic runtime and output; never make Git a required build tool."""
    try:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), str(compile_root)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=30,
        )
        line = result.stdout.strip()
        if result.returncode == 0 and RECEIPT_LINE.fullmatch(line):
            print(line, flush=True)
            return
    except Exception:
        pass
    print("WurstStdlib2 install receipt: status=unverified reason=inspection-unavailable", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(2)
    _emit_installed_stdlib(Path(sys.argv[1]))

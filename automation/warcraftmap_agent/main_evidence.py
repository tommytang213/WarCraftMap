"""One bounded, durable execution attempt per main revision/source/compiler pin.

The worker lock serializes callers. A running/failed receipt is deliberately not
retryable on every wake, including after a controller crash. Remove attempt.json
to explicitly retry a repaired validation environment. Evidence is never relabeled.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def write_receipt(path: Path, value: dict) -> None:
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            json.dump(value, output, sort_keys=True)
            output.flush()
            os.fsync(output.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def record_audits(config, revision: str, bundle: dict) -> None:
    """Retain all fresh findings alongside execution, without changing source reports.

    The snapshot records blockers as well as passes. Planning still regenerates
    on every wake; this archive is review evidence, never a saved closure flag.
    """
    root = config.state_dir / "main-execution" / revision
    root.mkdir(parents=True, exist_ok=True)
    write_receipt(root / "planning-audit.json", bundle)


def ensure(config, project: Path, revision: str, *, run, current, validate, allow_execute=True) -> dict:
    """Return only an explicitly verified location; failures use an absent path.

    ``current`` rechecks remote main, local HEAD and cleanliness. Probe calls
    additionally hash authored sources, including ignored/generated input paths.
    ``validate`` runs the complete required checks in the main checkout.
    """
    root = config.state_dir / "main-execution" / revision
    destination = root / "bundle"
    rejected = {"directory": str(root / "unavailable")}
    script = project / "tooling/planning_audit.py"

    def probe(directory=None):
        command = [sys.executable, str(script), "--source-revision", revision, "--execution-only"]
        if directory is not None:
            command += ["--evidence-directory", str(directory)]
        return json.loads(run(command, cwd=config.repo_root, timeout=300).stdout)

    def binding(value):
        return {name: value[name] for name in ("sourceIdentity", "compilerSha256")}

    def guard(expected):
        if not current() or binding(probe(root / "unavailable")) != expected:
            raise RuntimeError("main revision or authored sources changed during execution/publication")

    receipt_path = root / "attempt.json"
    attempt = None
    try:
        initial = probe(root / "unavailable")
        pinned = binding(initial)
        guard(pinned)
        if receipt_path.exists():
            saved = json.loads(receipt_path.read_text())
            if (not isinstance(saved, dict) or saved.get("revision") != revision or
                    not isinstance(saved.get("binding"), dict) or
                    saved.get("status") not in {"running", "failed", "passed"}):
                raise ValueError("malformed current-main validation receipt")
            attempt = saved
            if attempt.get("binding") == pinned:
                if attempt.get("status") != "passed":
                    return {**rejected, "error": attempt.get("error") or
                            "current-main validation interrupted before publication; explicit retry required"}
                verified = probe(destination)
                if not verified.get("valid"):
                    raise ValueError("published main evidence rejected: " + verified.get("error", "invalid bundle"))
                if verified.get("evidenceSha256") != attempt.get("evidenceSha256"):
                    raise ValueError("published main evidence differs from validation receipt")
                guard(pinned)
                return {"directory": str(destination), "reused": True}
        if not allow_execute:
            return {**rejected, "error": "current-main execution missing; validation disabled for dry run"}
        root.mkdir(parents=True, exist_ok=True)
        # Persist before starting expensive work. An interruption cannot turn a
        # partly exported bundle into closure authority on the next wake.
        attempt = {"revision": revision, "binding": pinned, "status": "running"}
        write_receipt(receipt_path, attempt)
        print(f"validating clean current main {revision} for closure", flush=True)
        validate(root / "validation.log")
        guard(pinned)
        with tempfile.TemporaryDirectory(prefix=".publication-", dir=root) as temporary:
            staged = Path(temporary) / "bundle"
            transport = config.repo_root / "maps/historical-world-rpg/_shared/tooling/execution_transport.py"
            run([sys.executable, str(transport), "stage", str(project), str(staged),
                 "--source-revision", revision], cwd=config.repo_root, timeout=300)
            verified = probe(staged)
            if not verified.get("valid") or binding(verified) != pinned:
                raise ValueError("new main execution rejected: " + verified.get("error", "source binding changed"))
            guard(pinned)
            if destination.exists():
                shutil.rmtree(destination)
            os.replace(staged, destination)
        guard(pinned)
        published = probe(destination)
        if not published.get("valid") or published.get("evidenceSha256") != verified["evidenceSha256"]:
            raise ValueError("main execution changed during publication: " + published.get("error", "bundle mismatch"))
        guard(pinned)
        attempt.update(status="passed", evidenceSha256=published["evidenceSha256"])
        write_receipt(receipt_path, attempt)
        return {"directory": str(destination), "reused": False}
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, AttributeError, subprocess.SubprocessError) as exc:
        # Never fall back to the checkout's results or a predecessor's bundle.
        error = f"current-main execution unavailable: {type(exc).__name__}: {exc}"
        if attempt is not None and receipt_path.exists():
            attempt.update(status="failed", error=error)
            write_receipt(receipt_path, attempt)
        return {**rejected, "error": error}

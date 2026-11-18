"""Local, fail-closed focused replay. Not a full gate or native acceptance.

Requires an existing offline bootstrap containing common.j, blizzard.j and
 dependencies/wurstStdlib2. No dependency installation is performed here.
Bootstrap bytes are inventoried, not asserted to have trusted provenance.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
from pathlib import Path
import re
import shutil
import subprocess

from integration_evidence import source_identity
from wurst_execution import (PINNED_COMPILER_SHA256, compiler_identity, discover,
                             input_hashes, parse_results, sha, toolchain_environment)


def require_local_tooling(project):
    if (project.parent / "_shared/tooling").resolve() != Path(__file__).resolve().parent:
        raise ValueError("project must use this runner checkout tooling")


def clean_revision(project, revision):
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("require full exact revision")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project, text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"],
                                     cwd=project, text=True)
    if head != revision or status:
        raise ValueError("checkout must be clean at requested revision")


def inventory(root):
    """Include all dependency bytes, and reject links escaping frozen inputs."""
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink in dependency inputs: {path}")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = sha(path.read_bytes())
    if not result:
        raise ValueError("empty dependency inventory")
    return result


def snapshot(root, executable, compiler):
    return {"inputs": input_hashes(root),
            "dependencies": inventory(root / "_build/dependencies"),
            "launcher": sha(executable.read_bytes()), "compiler": sha(compiler.read_bytes())}


def assemble(project, out, bootstrap):
    from package_wurst_map import load_config, generate, verify_generated, _assemble
    cfg = load_config(project / "package.json")
    generate(cfg, out / "generated")
    verify_generated(cfg, out / "generated")
    root = _assemble(cfg, out, out / "generated")
    # Normalize only the known case-sensitive dependency spelling, before freeze.
    build = root / "wurst.build"
    build.write_text(build.read_text().replace("wurstscript/WurstStdlib2", "wurstscript/wurstStdlib2"))
    inventory(bootstrap / "dependencies")
    shutil.copytree(bootstrap / "dependencies", root / "_build/dependencies")
    for name in ("common.j", "blizzard.j"):
        source = bootstrap / name
        if source.is_symlink():
            raise ValueError("bootstrap core JASS must not be a symlink")
        shutil.copyfile(source, root / "_build" / name)
    return root


def run_launcher(command, *, cwd, env, stdout, timeout):
    """Own the launcher session so timeout/cancellation also stop descendants."""
    if os.name != "posix":
        raise ValueError("focused replay requires POSIX process-group containment")
    with subprocess.Popen(command, cwd=cwd, env=env, stdout=stdout,
                          stderr=subprocess.STDOUT, start_new_session=True) as process:
        try:
            returncode = process.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            # Kill the owned group on timeout or cancellation, then re-raise
            # the original exception. Grill's JVM inherits this process group.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            raise
    return subprocess.CompletedProcess(command, returncode)


def replay(project, out, revision, packages, executable, compiler, bootstrap, timeout=600):
    # Never overwrite prior evidence. Output must be outside the source checkout.
    project, out = project.resolve(), out.resolve()
    repo = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"],
                                       cwd=project, text=True).strip()).resolve()
    if out == repo or repo in out.parents:
        raise ValueError("evidence output must be outside checkout")
    out.mkdir(parents=True, exist_ok=False)
    report = {"format": "warcraftmap_focused_replay_v1", "completed": False,
              "scope": "focused local toolchain only; not full gate, native or release acceptance",
              "bootstrapScope": "caller-supplied offline bootstrap; frozen before typecheck; no provenance assertion",
              "sourceRevision": revision, "requestedPackages": packages, "suites": [], "errors": []}
    try:
        require_local_tooling(project)
        clean_revision(project, revision)
        if (not packages or len(packages) != len(set(packages)) or
                any(p == "typecheck" or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", p) for p in packages) or timeout <= 0):
            raise ValueError("require unique package names and positive timeout")
        executable, compiler = executable.resolve(), compiler.resolve()
        if sha(compiler.read_bytes()) != PINNED_COMPILER_SHA256:
            raise ValueError("compiler differs from pinned compiler")
        report["sourceIdentity"] = source_identity(project, revision)
        root = assemble(project, out, bootstrap)
        frozen = snapshot(root, executable, compiler)
        report["frozen"] = frozen
        if frozen["compiler"] != PINNED_COMPILER_SHA256:
            raise ValueError("assembled compiler differs from pinned compiler")
        tests = discover(root)
        expected = {p: [t for t in tests if t["id"].startswith(f"wurst/{p}.wurst:")] for p in packages}
        if any(not rows for rows in expected.values()):
            raise ValueError("requested package has no discovered tests")
        report["expected"] = expected

        def unchanged():
            clean_revision(project, revision)
            if source_identity(project, revision) != report["sourceIdentity"] or snapshot(root, executable, compiler) != frozen:
                raise ValueError("source, compiler, launcher, input or dependency drift")

        unchanged()  # Includes drift during generation/bootstrap assembly.
        env = toolchain_environment()
        # No Docker claim: the actual compiler is checked both before and in logs.
        env.pop("WURST_IMAGE", None)
        for package in [None, *packages]:
            name = package or "typecheck"
            command = [str(executable), "test", package] if package else [str(executable), "typecheck"]
            entry = {"package": name, "command": command, "returnCode": None, "issues": []}
            report["suites"].append(entry)
            try:
                with (out / f"{name}.log").open("w") as log:
                    result = run_launcher(command, cwd=root, env=env, stdout=log, timeout=timeout)
                entry["returnCode"] = result.returncode
            except subprocess.TimeoutExpired:
                entry["issues"].append("process timeout")
                raise ValueError(f"{name}: process timeout")
            text = (out / f"{name}.log").read_text(errors="replace")
            entry["compiler"] = compiler_identity(text)
            entry["compiler"]["executionImage"] = None
            # A log pointing at another identical compiler is still pinned; its
            # digest must agree with our preflight/frozen compiler.
            if entry["compiler"]["sha256"] != frozen["compiler"]:
                raise ValueError("reported compiler differs from frozen compiler")
            if package:
                entry["tests"], entry["issues"] = parse_results(text, expected[package])
            elif "Typecheck succeeded" not in text:
                entry["issues"].append("missing successful typecheck marker")
            unchanged()
            if result.returncode or entry["issues"]:
                raise ValueError(f"{name}: failed focused execution")
        unchanged()
        report["completed"] = True
    except Exception as error:
        report["errors"].append(f"{type(error).__name__}: {error}")
    finally:
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["completed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("project", "out", "executable", "compiler", "bootstrap"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--package", action="append", required=True, dest="packages")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    return replay(**vars(args))


if __name__ == "__main__":
    raise SystemExit(main())

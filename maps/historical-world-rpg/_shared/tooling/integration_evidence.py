"""Revision-bound source identities and executed production-entry coverage.

Probes are inserted only into the disposable interpreter assembly, never the
shipping map. A probe declaration is not coverage: a passing test must emit it
between its Running/OK records in the pinned compiler transcript.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def source_identity(project: Path, revision: str) -> dict:
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("evidence requires a full source revision")
    # Reports are outputs, not inputs to execution. Include tests, generators,
    # shared production code and configuration so dirty worktrees cannot reuse
    # evidence solely because HEAD has not changed.
    roots = [project / name for name in ("map", "scenario", "wurst", "wurst-bootstrap", "tooling", "tests")]
    roots += [project.parent / "_shared"]
    files = [p for root in roots for p in root.rglob("*") if p.is_file()
             and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}]
    files += [p for p in project.iterdir() if p.is_file() and p.suffix in {".json", ".build", ".args"}]
    inputs = {Path(os.path.relpath(p, project)).as_posix(): digest(p.read_bytes())
              for p in sorted(set(files))}
    return {"sourceRevision": revision, "sourceTreeSha256": digest(canonical(inputs))}


def load_contract(project: Path) -> dict:
    config = json.loads((project / "package.json").read_text())
    if not isinstance(config, dict):
        raise ValueError("execution package configuration must be a JSON object")
    relative = config.get("executionCoverage")
    if relative is None:
        return {"probes": {}, "systems": {}}
    if not isinstance(relative, str) or not relative:
        raise ValueError("execution coverage requires a relative contract path")
    path = (project / relative).resolve()
    path.relative_to(project.resolve())
    contract = json.loads(path.read_text())
    if not isinstance(contract, dict) or contract.get("format") != "warcraftmap_execution_coverage_v1":
        raise ValueError("unsupported execution coverage contract")
    probes = contract.get("probes")
    systems = contract.get("systems")
    if not isinstance(probes, dict) or not isinstance(systems, dict):
        raise ValueError("execution probes and systems must be JSON objects")
    for name, spec in probes.items():
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            raise ValueError("invalid production probe ID")
        if (not isinstance(spec, dict) or not isinstance(spec.get("path"), str) or
                not isinstance(spec.get("signature"), str)):
            raise ValueError("production probe requires a path and function signature")
        path = Path(spec["path"])
        if (path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != "wurst" or
                path.suffix != ".wurst" or path.name.endswith("Tests.wurst")):
            raise ValueError("probe must target a production Wurst file")
        if not re.match(r"(?:public |override )*function \w+\(", spec["signature"]):
            raise ValueError("probe must target a complete function declaration")
    for system, required in systems.items():
        if (not isinstance(required, list) or not required or
                any(not isinstance(name, str) for name in required) or
                len(required) != len(set(required)) or set(required) - probes.keys()):
            raise ValueError(f"{system}: invalid production probe requirements")
    return contract


def instrument(text: str, probes: dict) -> str:
    # Ignore comment bodies without changing line offsets. A matching comment
    # or interface declaration must never become an executable probe.
    code = re.sub(r"//[^\n]*|/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m[0]), text, flags=re.S)
    inserts = []
    for name, spec in probes.items():
        matches = list(re.finditer(r"^([\t ]*)" + re.escape(spec["signature"]) + r"[\t ]*\n", code, re.M))
        if len(matches) != 1:
            raise ValueError(f"{name}: production declaration is absent or ambiguous")
        match = matches[0]
        body = next((line for line in code[match.end():].splitlines() if line.strip()), "")
        indent = re.match(r"[\t ]*", body)[0]
        if len(indent.expandtabs(4)) <= len(match[1].expandtabs(4)):
            raise ValueError(f"{name}: production declaration has no body")
        inserts.append((match.end(), indent + 'print("WCM_PROBE:' + name + '")\n'))
    for offset, statement in sorted(inserts, reverse=True):
        text = text[:offset] + statement + text[offset:]
    return text


def instrument_tree(root: Path, contract: dict) -> dict[Path, bytes]:
    originals = {}
    try:
        if any("WCM_PROBE:" in path.read_text() for path in (root / "wurst").rglob("*.wurst")):
            raise ValueError("reserved execution probe marker appears in uninstrumented source")
        for relative in sorted({spec["path"] for spec in contract["probes"].values()}):
            path = root / relative
            originals[path] = path.read_bytes()
            probes = {name: spec for name, spec in contract["probes"].items() if spec["path"] == relative}
            path.write_text(instrument(originals[path].decode(), probes))
    except Exception:
        for path, data in originals.items():
            path.write_bytes(data)
        raise
    return originals


def observed_probes(log: str, tests: list[dict], contract: dict) -> dict:
    runs = list(re.finditer(r"^Running (.+\.wurst):(\d+) - (\w+)\.\.\s*$", log, re.M))
    observed = {}
    for index, run in enumerate(runs):
        matches = [test for test in tests if test["status"] == "pass"
                   and test["id"].endswith(":" + run[3])
                   and (run[1] == test["id"].rsplit(":", 1)[0]
                        or run[1].endswith("/" + test["id"].rsplit(":", 1)[0]))]
        if len(matches) != 1:
            continue
        body = log[run.end():runs[index + 1].start() if index + 1 < len(runs) else len(log)]
        # Only hits emitted before this test's successful completion count.
        body = re.split(r"^\s*OK!\s*$", body, maxsplit=1, flags=re.M)[0]
        hits = sorted(set(re.findall(r"^WCM_PROBE:([a-z][a-z0-9_]*)\s*$", body, re.M)))
        if set(hits) - contract["probes"].keys():
            raise ValueError("transcript contains an unknown production probe")
        if hits:
            observed[matches[0]["id"]] = hits
    return observed


def verify_execution_coverage(report: dict, log: bytes, project: Path, revision: str) -> dict:
    from wurst_execution import verify_evidence, discover
    verify_evidence(report, log, revision)
    if report.get("executionStatus") != "completed":
        raise ValueError("required integration executionStatus is not completed")
    identity = source_identity(project, revision)
    if report.get("sourceIdentity") != identity:
        raise ValueError("execution evidence has a stale or missing source identity")
    contract = load_contract(project)
    coverage = report.get("productionCoverage", {})
    if not isinstance(coverage, dict) or coverage.get("contractSha256") != digest(canonical(contract)):
        raise ValueError("missing or stale production coverage contract")
    if report.get("expected") != discover(project):
        raise ValueError("execution discovery does not match current source tests")
    # Bind observed probe IDs to the instrumented production code actually
    # supplied to the interpreter, not to caller-declared coverage metadata.
    for source in sorted((project / "wurst").rglob("*.wurst")):
        relative = source.relative_to(project).as_posix()
        if "WCM_PROBE:" in source.read_text():
            raise ValueError("reserved execution probe marker appears in uninstrumented source")
        probes = {name: spec for name, spec in contract["probes"].items() if spec["path"] == relative}
        expected = digest(instrument(source.read_text(), probes).encode() if probes else source.read_bytes())
        if report.get("inputs", {}).get(relative) != expected:
            raise ValueError(f"production probe input mismatch: {relative}")
    for source in sorted((project.parent / "_shared/wurst").glob("*.wurst")):
        if report["inputs"].get("wurst/" + source.name) != digest(source.read_bytes()):
            raise ValueError(f"shared production input mismatch: {source.name}")
    # Grill rewrites wurst.build during dependency installation (YAML ordering
    # and dependency URL capitalization). The source identity binds the authored
    # config; the runner separately hashes the normalized interpreter input.
    if (project / "wurst.build").is_file() and "wurst.build" not in report["inputs"]:
        raise ValueError("compiler configuration input is missing: wurst.build")
    arguments = project / "wurst_run.args"
    if arguments.is_file() and report["inputs"].get(arguments.name) != digest(arguments.read_bytes()):
        raise ValueError("compiler configuration mismatch: wurst_run.args")
    observed = observed_probes(log.decode(), report["tests"], contract)
    if coverage.get("tests") != observed:
        raise ValueError("declared production coverage differs from executed transcript")
    return {system: sorted(test for test, hits in observed.items() if set(required) <= set(hits))
            for system, required in contract["systems"].items()}

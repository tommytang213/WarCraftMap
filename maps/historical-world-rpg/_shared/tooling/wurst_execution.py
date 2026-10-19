"""Fail-closed execution gate for the pinned Wurst interpreter.

Grill's exit status alone is insufficient: match every discovered source test
to a terminal result, the compiler summary and the completion marker. Keep the
raw transcript and input hashes even when execution fails.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

PINNED_IMAGE = "frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a"
PINNED_COMPILER_SHA256 = "1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145"
PINNED_COMPILER_VERSION = "1.9.0.0-nightly-1-gedd2e5e74"
FORMAT = "warcraftmap_wurst_execution_v1"
# The interpreter retains Wurst heap objects across tests in one process. Keep
# catalogue-heavy integration fixtures away from the accumulated full-suite heap.
# This bounds lifetime, not the per-test timeout or the discovered test set.
TESTS_PER_PROCESS = 100


class WurstExecutionError(RuntimeError):
    pass


def toolchain_environment() -> dict[str, str]:
    """Give the full generated suite enough heap without changing host settings.

    The complete catalogue suite saturated a 6 GiB heap and spent minutes in
    full GC, causing the unchanged 20-second test deadlines to expire. Reserve
    8 GiB for this process. Prepend the limit so an explicit caller -Xmx in
    JAVA_TOOL_OPTIONS still takes precedence. Grill's compiler child inherits it.
    """
    env = os.environ.copy()
    env["JAVA_TOOL_OPTIONS"] = ("-Xmx8g " + env.get("JAVA_TOOL_OPTIONS", "")).strip()
    return env


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def source_revision(project: Path, explicit: str | None = None) -> str:
    value = explicit or os.environ.get("SOURCE_REVISION")
    if not value:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project,
                                capture_output=True, text=True)
        value = result.stdout.strip() if result.returncode == 0 else ""
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise WurstExecutionError("execution evidence requires a full source revision (SOURCE_REVISION)")
    return value


def discover(compile_root: Path, *, allow_empty: bool = False,
             sources: dict[str, Path] | None = None) -> list[dict]:
    tests = []
    if sources is None:
        sources = {path.relative_to(compile_root).as_posix(): path
                   for path in (compile_root / "wurst").rglob("*.wurst")}
    # Preserve newlines while removing comments, strings and rawcode literals.
    ignored = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)
    for relative, path in sorted(sources.items()):
        code = ignored.sub(lambda m: re.sub(r"[^\n]", " ", m[0]), path.read_text())
        matches = list(re.finditer(r"@test\s+function\s+(\w+)\s*\(", code))
        if len(matches) != len(re.findall(r"@test\b", code)):
            raise WurstExecutionError(f"unrecognized test declaration in {path.name}")
        for match in matches:
            tests.append({"id": relative + ":" + match[1],
                          "line": code[:match.start()].count("\n") + 1})
    ids = [row["id"] for row in tests]
    if (not tests and not allow_empty) or len(ids) != len(set(ids)):
        raise WurstExecutionError("Wurst test discovery is empty or contains duplicate tests")
    return tests


def parse_results(log: str, expected: list[dict]) -> tuple[list[dict], list[str]]:
    issues = []
    if not expected:
        issues.append("zero discovered tests")
    starts = list(re.finditer(r"^Running tests\s*$", log, re.M))
    finishes = list(re.finditer(r"^Finished running tests\s*$", log, re.M))
    summaries = list(re.finditer(r"^Tests succeeded: (\d+)/(\d+)\s*$", log, re.M))
    if len(starts) != 1 or len(finishes) != 1 or len(summaries) != 1:
        issues.append("missing or repeated suite start, summary or completion")
    elif not starts[0].end() < summaries[0].start() < finishes[0].start():
        issues.append("suite markers are out of order")
    runs = list(re.finditer(r"^Running (.+\.wurst):(\d+) - (\w+)\.\.\s*$", log, re.M))
    rows = []
    for index, run in enumerate(runs):
        end = runs[index + 1].start() if index + 1 < len(runs) else (summaries[0].start() if summaries else len(log))
        body = log[run.end():end]
        matches = [test for test in expected
                   if test["id"].endswith(":" + run[3]) and
                   (run[1] == test["id"].rsplit(":", 1)[0] or
                    run[1].endswith("/" + test["id"].rsplit(":", 1)[0]))]
        test_id = matches[0]["id"] if len(matches) == 1 else run[1] + ":" + run[3]
        status = "incomplete"
        if "FAILED assertion" in body:
            status = "assertion_failed"
        elif re.search(r"interpreter|Exception|No builtin function", body, re.I):
            status = "interpreter_error"
        elif len(re.findall(r"^\s*OK!\s*$", body, re.M)) == 1:
            status = "pass"
        rows.append({"id": test_id, "line": int(run[2]), "status": status})
        if len(matches) != 1 or int(run[2]) != matches[0]["line"]:
            issues.append(f"unexpected test or source line: {test_id}")
        if starts and finishes and not starts[0].end() <= run.start() < finishes[0].start():
            issues.append(f"test outside suite: {test_id}")
    if sorted(row["id"] for row in rows) != sorted(row["id"] for row in expected):
        issues.append("executed tests differ from discovered tests")
    if any(row["status"] != "pass" for row in rows):
        issues.append("non-passing or incomplete individual results")
    if summaries and (int(summaries[0][1]) != len(expected) or int(summaries[0][2]) != len(expected)):
        issues.append("summary does not match complete passing discovery")
    if re.search(r"FAILED assertion|Tests have failed|Exception|cannot be used from the Wurst interpreter|No builtin function|bug in the interpreter|^Error(?: in File|:)", log, re.M):
        issues.append("assertion, compiler or interpreter error in transcript")
    return rows, issues


def input_hashes(compile_root: Path) -> dict[str, str]:
    files = list((compile_root / "wurst").rglob("*.wurst"))
    files += [compile_root / name for name in ("wurst.build", "wurst_run.args", "_build/common.j", "_build/blizzard.j")]
    files += list((compile_root / ".wurst").rglob("*.wurst"))
    return {path.relative_to(compile_root).as_posix(): sha(path.read_bytes())
            for path in sorted(files) if path.is_file()}


def select_tests(text: str, names: set[str]) -> str:
    """Remove only unselected annotations; preserve code, indentation and lines."""
    ignored = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)
    code = ignored.sub(lambda m: re.sub(r"[^\n]", " ", m[0]), text)
    offsets = []
    for match in re.finditer(r"@test\s+function\s+(\w+)\s*\(", code):
        if match[1] not in names:
            end = match.start() + len("@test")
            while end < len(text) and text[end] in " \t":
                end += 1
            offsets.append((match.start(), end))
    for start, end in reversed(offsets):
        text = text[:start] + text[end:]
    return text


def parse_execution(log: str, expected: list[dict], shards: list[dict] | None = None,
                    inputs: dict | None = None) -> tuple[list[dict], list[str]]:
    """Validate each raw process transcript and the exact partition of discovery."""
    if shards is None:
        return parse_results(log, expected)
    if not isinstance(shards, list) or not shards:
        raise WurstExecutionError("malformed Wurst execution shards")
    rows, issues, covered = [], [], []
    offset = 0
    by_id = {test["id"]: test for test in expected}
    for shard in shards:
        if (not isinstance(shard, dict) or type(shard.get("logStart")) is not int or
                type(shard.get("logEnd")) is not int or shard["logStart"] != offset or
                not offset < shard["logEnd"] <= len(log) or
                not isinstance(shard.get("testIds"), list) or not shard["testIds"] or
                any(not isinstance(t, str) or t not in by_id for t in shard["testIds"]) or
                type(shard.get("returnCode")) is not int or
                not isinstance(shard.get("inputOverrides"), dict)):
            raise WurstExecutionError("malformed Wurst execution shard")
        overrides = shard["inputOverrides"]
        if (inputs is None or any(name not in inputs or not name.startswith("wurst/") or
                not name.endswith(".wurst") or not isinstance(value, str) or
                not re.fullmatch(r"[0-9a-f]{64}", value) for name, value in overrides.items()) or
                shard.get("inputSetSha256") != sha(canonical({**inputs, **overrides}))):
            raise WurstExecutionError("mismatched Wurst shard inputs")
        transcript = log[offset:shard["logEnd"]]
        if shard.get("logSha256") != sha(transcript.encode()):
            raise WurstExecutionError("mismatched Wurst shard transcript")
        actual, errors = parse_results(transcript, [by_id[t] for t in shard["testIds"]])
        rows.extend(actual)
        issues.extend(errors)
        if shard["returnCode"]:
            issues.append(f"grill test exited {shard['returnCode']}")
        covered.extend(shard["testIds"])
        offset = shard["logEnd"]
    if offset != len(log) or sorted(covered) != sorted(by_id):
        issues.append("execution shards differ from complete discovery or transcript")
    return rows, issues


def compiler_identity(log: str) -> dict:
    grill = re.search(r"Grill ([\w.-]+)", log)
    jar = re.search(r"detectedCompilerJar=(.+?) exists=true", log)
    if not grill or not jar or not Path(jar[1]).is_file():
        raise WurstExecutionError("compiler identity is absent from execution")
    compiler_sha = sha(Path(jar[1]).read_bytes())
    if compiler_sha != PINNED_COMPILER_SHA256:
        raise WurstExecutionError("execution used a compiler different from the pinned toolchain")
    return {"sha256": compiler_sha, "grillVersion": grill[1],
            "expectedImage": PINNED_IMAGE, "executionImage": os.environ.get("WURST_IMAGE"),
            "version": PINNED_COMPILER_VERSION}


def execute_tests(compile_root: Path, executable: str, evidence_dir: Path,
                  revision: str | None = None, *, project: Path | None = None) -> dict:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    log_path = evidence_dir / "execution.log"
    report_path = evidence_dir / "results.json"
    report = {"format": FORMAT, "status": "fail", "sourceRevision": "",
              "expected": [], "tests": [], "errors": [], "command": [Path(executable).name, "test"],
              "executionStatus": "not_run"}
    log = ""
    originals = {}
    test_sources = {}
    try:
        report["sourceRevision"] = source_revision(compile_root, revision)
        if project is not None:
            from integration_evidence import (source_identity, load_contract, instrument_tree,
                                              observed_probes)
            report["sourceIdentity"] = source_identity(project, report["sourceRevision"])
            contract = load_contract(project)
            originals = instrument_tree(compile_root, contract)
        report["expected"] = discover(compile_root)
        inputs = input_hashes(compile_root)
        report["inputs"] = inputs
        report["inputSetSha256"] = sha(canonical(inputs))
        expected = report["expected"]
        batches = [expected[i:i + TESTS_PER_PROCESS] for i in range(0, len(expected), TESTS_PER_PROCESS)]
        sharded = len(batches) > 1
        if sharded:
            report["shards"] = []
            test_paths = {compile_root / test["id"].rsplit(":", 1)[0] for test in expected}
            test_sources = {path: path.read_bytes() for path in test_paths}
        report["returnCode"] = 0
        for number, batch in enumerate(batches, 1):
            if sharded:
                for path, original in test_sources.items():
                    names = {t["id"].rsplit(":", 1)[1] for t in batch
                             if compile_root / t["id"].rsplit(":", 1)[0] == path}
                    path.write_text(select_tests(original.decode(), names))
                if discover(compile_root) != batch:
                    raise WurstExecutionError("test selection differs from discovered shard")
            selected_inputs = input_hashes(compile_root)
            result = subprocess.run([executable, "test"], cwd=compile_root,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                    env=toolchain_environment())
            start = len(log)
            log += result.stdout
            if sharded:
                report["shards"].append({"testIds": [t["id"] for t in batch],
                    "logStart": start, "logEnd": len(log), "logSha256": sha(result.stdout.encode()),
                    "returnCode": result.returncode,
                    "inputOverrides": {k: v for k, v in selected_inputs.items() if inputs.get(k) != v},
                    "inputSetSha256": sha(canonical(selected_inputs))})
            report["returnCode"] = report["returnCode"] or result.returncode
            identity = compiler_identity(result.stdout)
            if "compiler" in report and report["compiler"] != identity:
                raise WurstExecutionError("compiler identity changed between execution shards")
            report["compiler"] = identity
            if input_hashes(compile_root) != selected_inputs:
                raise WurstExecutionError("compiler inputs changed during execution")
            if sharded:
                rows, _ = parse_results(result.stdout, batch)
                passed = sum(row["status"] == "pass" for row in rows)
                print(f"Wurst execution batch {number}/{len(batches)}: {passed}/{len(batch)} passed", flush=True)
        for path, original in test_sources.items():
            path.write_bytes(original)
        report["executionStatus"] = "completed"
        rows, issues = parse_execution(log, expected, report.get("shards"), inputs)
        report["tests"] = rows
        report["errors"].extend(issues)
        if report["returnCode"] and not report.get("shards"):
            report["errors"].append(f"grill test exited {report['returnCode']}")
        if input_hashes(compile_root) != inputs:
            raise WurstExecutionError("compiler inputs changed during execution")
        if project is not None:
            if source_identity(project, report["sourceRevision"]) != report["sourceIdentity"]:
                raise WurstExecutionError("authoritative sources changed during execution")
            report["productionCoverage"] = {
                "contractSha256": sha(canonical(contract)),
                "tests": observed_probes(log, rows, contract),
            }
    except (OSError, ValueError, WurstExecutionError) as error:
        report["errors"].append(str(error))
    finally:
        for path, original in test_sources.items():
            path.write_bytes(original)
        for path, original in originals.items():
            path.write_bytes(original)
    report["logSha256"] = sha(log.encode())
    report["discovered"] = len(report["expected"])
    report["succeeded"] = sum(row["status"] == "pass" for row in report["tests"])
    report["status"] = "pass" if not report["errors"] else "fail"
    log_path.write_text(log, encoding="utf-8")
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wurst execution: {report['succeeded']}/{report['discovered']} passed; evidence: {report_path}")
    if report["status"] != "pass":
        # CI builds in disposable containers. Surface the actual failed test
        # and interpreter diagnostic before their private evidence is removed.
        # Keep the transcript/evidence and fail-closed result unchanged.
        if log:
            print(log, file=sys.stderr, end="" if log.endswith("\n") else "\n")
        raise WurstExecutionError("; ".join(report["errors"]) + f" (see {log_path})")
    return report


def verify_evidence(report: dict, log: bytes, revision: str) -> None:
    """Recheck packaged evidence before upload; a saved 'pass' flag is not enough."""
    if not isinstance(report, dict):
        raise WurstExecutionError("Wurst execution evidence must be a JSON object")
    expected = report.get("expected", [])
    inputs = report.get("inputs", {})
    compiler = report.get("compiler")
    if "shards" in report and not isinstance(report["shards"], list):
        raise WurstExecutionError("malformed Wurst execution shards")
    if (not isinstance(expected, list) or not expected or
            any(not isinstance(row, dict) or not isinstance(row.get("id"), str) or
                not row["id"] or type(row.get("line")) is not int or row["line"] < 1
                for row in expected) or
            len({row["id"] for row in expected}) != len(expected) or
            not isinstance(inputs, dict) or not inputs or
            any(not isinstance(name, str) or not isinstance(value, str) or
                not re.fullmatch(r"[0-9a-f]{64}", value) for name, value in inputs.items()) or
            not isinstance(compiler, dict) or not isinstance(log, bytes) or
            not isinstance(revision, str)):
        raise WurstExecutionError("malformed Wurst execution evidence")
    try:
        rows, issues = parse_execution(log.decode("utf-8"), expected, report.get("shards"), inputs)
    except UnicodeDecodeError as error:
        raise WurstExecutionError("invalid Wurst execution transcript encoding") from error
    if (report.get("format") != FORMAT or report.get("status") != "pass" or
            report.get("executionStatus") != "completed" or
            report.get("errors") != [] or report.get("returnCode") != 0 or
            report.get("sourceRevision") != revision or not re.fullmatch(r"[0-9a-f]{40}", revision) or
            report.get("logSha256") != sha(log) or not inputs or
            report.get("inputSetSha256") != sha(canonical(inputs)) or
            compiler.get("sha256") != PINNED_COMPILER_SHA256 or
            report.get("discovered") != len(expected) or report.get("succeeded") != len(expected) or
            report.get("tests") != rows or issues):
        raise WurstExecutionError("missing, failed, incomplete or mismatched Wurst execution evidence")

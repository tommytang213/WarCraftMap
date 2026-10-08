#!/usr/bin/env python3
"""Bind the merged autosave, recovery and help receipts to a diagnostic W3N.

Run after the pinned campaign build. The full report retains all unrelated
publication blockers; passing this scoped check never authorizes a release.
"""
import argparse
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT / "tooling"), str(PROJECT.parent / "_shared/tooling")]
import requirement_traceability_audit as scenario
import requirement_traceability as trace
import runtime_acceptance as runtime
from integration_evidence import source_identity
from wurst_execution import source_revision

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--artifact", type=Path,
                    default=PROJECT / "_build/release/AgeOfSailWorldCampaign.w3n")
parser.add_argument("--execution-dir", type=Path, default=PROJECT / "_build/wurst-tests")
parser.add_argument("--output-dir", type=Path, default=PROJECT / "_build/issue-413-repair")
parser.add_argument("--source-revision")
args = parser.parse_args()

scopes = {
    "autosave": {"REQ-0184.01", "REQ-0187.01"},
    "recovery": {"REQ-0185.01", "REQ-0186.01", "REQ-0190.01"},
    "help": {"REQ-0203.01", "REQ-0204.01", "REQ-0205.01", "REQ-0205.02",
             "REQ-0206.01", "REQ-0207.01"},
}
required = set().union(*scopes.values())
revision = source_revision(PROJECT, args.source_revision)
execution = trace.load(args.execution_dir / "results.json")
transcript = (args.execution_dir / "execution.log").read_bytes()
report = scenario.build_report(args.artifact, execution, transcript, revision)
scenario.write_report(report, args.output_dir / "requirement-traceability")
assert not report["executionErrors"], report["executionErrors"]
rows = [row for row in report["requirements"] if row["id"] in required]
assert {row["id"] for row in rows} == required
assert all(row["status"] == "pass" for row in rows), [
    (row["id"], row["blockerClasses"]) for row in rows]
assert not report["candidateReady"] and report["blockerCount"] > 0
acceptance = runtime.audit_acceptance(execution=execution, execution_log=transcript,
                                     revision=revision, campaign=args.artifact)
for level in ("runtimeIntegration", "builtArtifact"):
    assert acceptance["evidenceLevels"][level]["status"] == "pass", acceptance["evidenceLevels"][level]
receipts = [json.loads(line.removeprefix("TRACEABILITY "))
            for line in transcript.decode().splitlines() if line.startswith("TRACEABILITY ")]
receipts = [row for row in receipts if row["requirement"] in required]
assert len(receipts) == 4 * len(required)
assert {(row["requirement"], row["case"]) for row in receipts} == {
    (requirement, case) for requirement in required
    for case in ("success", "failure", "stale", "replay")}
result = {
    **source_identity(PROJECT, revision),
    "status": "pass",
    "scopes": {key: sorted(value) for key, value in scopes.items()},
    "requirements": [{key: row[key] for key in ("id", "status", "blockerClasses")}
                     for row in rows],
    "artifactSha256": report["artifact"]["sha256"],
    "artifactBytes": args.artifact.stat().st_size,
    "candidateReady": report["candidateReady"],
    "remainingBlockerCount": report["blockerCount"],
    "remainingBlockerClasses": report["blockerClasses"],
    "pinnedTestsPassed": execution["succeeded"],
    "compilerSha256": execution["compiler"]["sha256"],
    "transcriptSha256": execution["logSha256"],
    "inputSetSha256": execution["inputSetSha256"],
    "receipts": receipts,
}
(args.output_dir / "scoped-evidence.json").write_bytes(trace.canonical(result))
(args.output_dir / "runtime-acceptance.json").write_bytes(trace.canonical(acceptance))
print(json.dumps({key: result[key] for key in (
    "status", "scopes", "artifactSha256", "pinnedTestsPassed", "remainingBlockerCount")}, indent=2))

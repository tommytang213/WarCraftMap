#!/usr/bin/env python3
"""Verify recovery and merged help evidence against the rebuilt diagnostic W3N.

Run after package_campaign.py. This retains the complete traceability report
and keeps publication blocked while verifying the two integrated issue scopes.
"""
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "tooling"))
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
import requirement_traceability_audit as scenario
import requirement_traceability as trace
import runtime_acceptance as runtime
from integration_evidence import source_identity
from wurst_execution import source_revision

recovery_ids = {"REQ-0185.01", "REQ-0186.01", "REQ-0190.01"}
help_ids = {"REQ-0203.01", "REQ-0204.01", "REQ-0205.01", "REQ-0205.02",
            "REQ-0206.01", "REQ-0207.01"}
revision = source_revision(PROJECT)
artifact = PROJECT / "_build/release/AgeOfSailWorldCampaign.w3n"
execution = trace.load(PROJECT / "_build/wurst-tests/results.json")
transcript = (PROJECT / "_build/wurst-tests/execution.log").read_bytes()
report = scenario.audit_final(artifact, execution, transcript, revision)
assert not report["executionErrors"], report["executionErrors"]
rows = [row for row in report["requirements"] if row["id"] in recovery_ids | help_ids]
assert {row["id"] for row in rows} == recovery_ids | help_ids
assert all(row["status"] == "pass" for row in rows), [
    (row["id"], row["blockerClasses"]) for row in rows]
assert not report["candidateReady"] and report["blockerCount"] > 0
acceptance = runtime.audit_acceptance(execution=execution, execution_log=transcript,
                                     revision=revision, campaign=artifact)
for level in ("runtimeIntegration", "builtArtifact"):
    assert acceptance["evidenceLevels"][level]["status"] == "pass", acceptance["evidenceLevels"][level]
receipts = [json.loads(line.removeprefix("TRACEABILITY "))
            for line in transcript.decode().splitlines() if line.startswith("TRACEABILITY ")]
receipts = [row for row in receipts if row["requirement"] in recovery_ids | help_ids]
assert len(receipts) == 36
assert {(row["requirement"], row["case"]) for row in receipts} == {
    (requirement, case) for requirement in recovery_ids | help_ids
    for case in ("success", "failure", "stale", "replay")}
result = {
    **source_identity(PROJECT, revision),
    "status": "pass",
    "recoveryScope": sorted(recovery_ids),
    "mergedHelpScope": sorted(help_ids),
    "artifactSha256": report["artifact"]["sha256"],
    "artifactBytes": artifact.stat().st_size,
    "scopedBlockers": [],
    "candidateReady": report["candidateReady"],
    "remainingBlockerCount": report["blockerCount"],
    "remainingBlockerClasses": report["blockerClasses"],
    "pinnedTestsPassed": execution["succeeded"],
    "compilerSha256": execution["compiler"]["sha256"],
    "transcriptSha256": execution["logSha256"],
    "inputSetSha256": execution["inputSetSha256"],
    "receipts": receipts,
}
(PROJECT / "_build/release/issue-412-repair-scoped-evidence.json").write_bytes(trace.canonical(result))
(PROJECT / "_build/release/issue-412-repair-runtime-acceptance.json").write_bytes(trace.canonical(acceptance))
print(json.dumps({key: result[key] for key in (
    "status", "recoveryScope", "mergedHelpScope", "artifactSha256",
    "pinnedTestsPassed", "remainingBlockerCount")}, indent=2))

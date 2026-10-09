#!/usr/bin/env python3
"""Verify scoped remote authorization against executed tests and packaged maps."""
import argparse
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT / "tooling"), str(PROJECT.parent / "_shared/tooling")]
import requirement_traceability_audit as scenario
import requirement_traceability as trace
from integration_evidence import source_identity
from wurst_execution import source_revision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--execution-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision")
    args = parser.parse_args()
    revision = source_revision(PROJECT, args.source_revision)
    execution = trace.load(args.execution_dir / "results.json")
    transcript = (args.execution_dir / "execution.log").read_bytes()
    report = scenario.build_report(args.artifact, execution, transcript, revision)
    scenario.write_report(report, args.output_dir / "requirement-traceability")
    assert not report["executionErrors"], report["executionErrors"]
    required = {"REQ-0296.01", "REQ-0305.01"}
    rows = {row["id"]: row for row in report["requirements"]}
    assert all(rows[ident]["status"] == "pass" for ident in required), [
        (ident, rows[ident]["blockerClasses"]) for ident in sorted(required)]
    receipts = [json.loads(line.removeprefix("TRACEABILITY "))
                for line in transcript.decode().splitlines() if line.startswith("TRACEABILITY ")]
    receipts = [row for row in receipts if row["requirement"] in required]
    assert len(receipts) == 8
    assert {(row["requirement"], row["case"]) for row in receipts} == {
        (ident, case) for ident in required for case in ("success", "failure", "stale", "replay")}
    # Authorization evidence cannot close physical command transport or replace
    # a native client launch. Retain both the precise downstream obligations and
    # the broader publication gate instead of certifying the whole feature.
    downstream = ("REQ-0300.01", "ROAD-0062.01")
    assert all(rows[ident]["status"] == "fail" for ident in downstream)
    assert not report["candidateReady"] and report["blockerCount"] > 0
    result = {
        **source_identity(PROJECT, revision), "status": "pass",
        "scope": "campaign-authority remote command eligibility and knowledge filtering",
        "artifactSha256": report["artifact"]["sha256"],
        "executionLogSha256": execution["logSha256"],
        "requirements": [{"id": ident, "status": rows[ident]["status"]} for ident in sorted(required)],
        "receipts": len(receipts), "candidateReady": False,
        "remainingPublicationBlockers": report["blockerCount"],
        "downstreamObligations": list(downstream),
        "realClientExecuted": False,
        "releaseStatus": "blocked_pending_remote_transport_and_native_launch",
    }
    (args.output_dir / "scoped-evidence.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("PASS: scoped remote authorization; physical command transport and native launch remain blocked")


if __name__ == "__main__":
    main()

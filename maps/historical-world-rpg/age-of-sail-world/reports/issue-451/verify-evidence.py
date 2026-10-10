#!/usr/bin/env python3
"""Verify remote physical command execution against the same-revision campaign."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT / "tooling"), str(PROJECT.parent / "_shared/tooling")]
import requirement_traceability_audit as scenario
import requirement_traceability as trace
from integration_evidence import source_identity
from warcraft_campaign import MpqReader
from wurst_execution import source_revision

REQUIREMENTS = {"REQ-0297.01", "REQ-0297.02", "REQ-0298.01", "REQ-0299.01",
                "REQ-0300.01", "REQ-0300.02", "REQ-0301.01", "REQ-0301.02",
                "REQ-0302.01", "REQ-0303.01", "ROAD-0062.01"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--execution-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision")
    args = parser.parse_args()
    revision = source_revision(PROJECT, args.source_revision)
    identity = source_identity(PROJECT, revision)
    execution = trace.load(args.execution_dir / "results.json")
    transcript = (args.execution_dir / "execution.log").read_bytes()
    report = scenario.build_report(args.artifact, execution, transcript, revision)
    scenario.write_report(report, args.output_dir / "requirement-traceability")
    assert not report["executionErrors"], report["executionErrors"]
    rows = {row["id"]: row for row in report["requirements"]}
    assert all(rows[key]["status"] == "pass" for key in REQUIREMENTS), [
        (key, rows[key]["blockerClasses"]) for key in sorted(REQUIREMENTS)]
    assert not report["candidateReady"] and report["blockerCount"] > 0
    # Transport preserves abstract authority, but does not certify the broader
    # inactive simulation feature or native client execution.
    assert rows["REQ-0302.02"]["status"] == "fail"
    archive = MpqReader(args.artifact)
    chapters = trace.load(PROJECT / "physical-maps.json")["physicalMaps"]
    destinations = {row["id"]: row["packagePath"] for row in chapters if not row.get("bootstrap")}
    checked = []
    with tempfile.TemporaryDirectory(dir=args.output_dir) as temporary:
        for physical in chapters:
            if physical.get("bootstrap"):
                continue
            path = Path(temporary) / (physical["id"] + ".w3x")
            path.write_bytes(archive.read(physical["packagePath"]))
            nested = MpqReader(path)
            assert json.loads(nested.read("runtime/build-identity.json")) == identity
            script = nested.read("war3map.lua").decode()
            for destination in destinations.values():
                assert destination.replace("\\", "\\\\") in script, (physical["id"], destination)
            for marker in ("command_request", "command_context", "commandContext",
                           "Command acknowledgement was interrupted", "ChangeLevel"):
                assert marker in script, (physical["id"], marker)
            checked.append({"mapId": physical["id"], "packagePath": physical["packagePath"]})
    receipts = [json.loads(line.removeprefix("TRACEABILITY "))
                for line in transcript.decode().splitlines() if line.startswith("TRACEABILITY ")]
    receipts = [row for row in receipts if row["requirement"] in REQUIREMENTS]
    assert len(receipts) == len(REQUIREMENTS) * 4
    assert {(row["requirement"], row["case"]) for row in receipts} == {
        (key, case) for key in REQUIREMENTS for case in ("success", "failure", "stale", "replay")}
    result = {**identity, "status": "pass", "requirements": sorted(REQUIREMENTS),
              "artifactSha256": report["artifact"]["sha256"],
              "executionLogSha256": execution["logSha256"], "chapters": checked,
              "receipts": len(receipts), "campaignSchemaVersions": list(range(1, 10)),
              "remainingPublicationBlockers": report["blockerCount"], "candidateReady": False,
              "remainingSimulationObligation": "REQ-0302.02", "realClientExecuted": False,
              "releaseStatus": "blocked_pending_real_forsaken_kingdom_launch_smoke"}
    (args.output_dir / "scoped-evidence.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("PASS: physical command handoff, destination orders and return; simulation/native launch gates retained")


if __name__ == "__main__":
    main()

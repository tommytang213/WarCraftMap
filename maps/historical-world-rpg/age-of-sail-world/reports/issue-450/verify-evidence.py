#!/usr/bin/env python3
"""Bind combat-earned XP receipts to the same-source diagnostic campaign."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT / "tooling"), str(PROJECT.parent / "_shared/tooling"),
               str(PROJECT.parent / "_shared/engine")]
import requirement_traceability_audit as scenario
import requirement_traceability as trace
from integration_evidence import source_identity, verify_execution_coverage
from military_tradition import MilitaryTraditionRuntime, RecordingTraditionAdapter
from warcraft_campaign import MpqReader
from wurst_execution import source_revision

REQUIREMENTS = ("ROAD-0052.01", "REQ-0154.01", "REQ-0164.01")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--execution-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-revision")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    revision = source_revision(PROJECT, args.source_revision)
    identity = source_identity(PROJECT, revision)
    execution = trace.load(args.execution_dir / "results.json")
    transcript = (args.execution_dir / "execution.log").read_bytes()
    coverage = verify_execution_coverage(execution, transcript, PROJECT, revision)
    assert coverage["military_tradition"]
    report = scenario.build_report(args.artifact, execution, transcript, revision)
    scenario.write_report(report, args.output_dir / "requirement-traceability")
    assert not report["executionErrors"], report["executionErrors"]
    rows = {row["id"]: row for row in report["requirements"]}
    for requirement in REQUIREMENTS:
        assert rows[requirement]["status"] == "pass", rows[requirement]
    # Earned XP does not claim other adapters, live coefficients or milestones.
    pending = ["REQ-0154.02", "REQ-0155.01", "REQ-0157.01", "REQ-0158.01",
               "REQ-0159.01", "REQ-0161.01", "REQ-0162.01", "REQ-0163.02"]
    assert all(rows[item]["status"] != "pass" for item in pending)
    assert not report["candidateReady"] and report["blockerCount"] > 0
    definitions = trace.load(PROJECT / "scenario/military-traditions.json")
    archive = MpqReader(args.artifact)
    checked = []
    with tempfile.TemporaryDirectory(dir=args.output_dir) as temporary:
        for physical in trace.load(PROJECT / "physical-maps.json")["physicalMaps"]:
            if physical.get("bootstrap"):
                continue
            path = Path(temporary) / (physical["id"] + ".w3x")
            path.write_bytes(archive.read(physical["packagePath"]))
            nested = MpqReader(path)
            assert json.loads(nested.read("runtime/build-identity.json")) == identity
            runtime = json.loads(nested.read("runtime/scenario-runtime.json"))
            assert runtime["militaryTraditions"] == definitions
            # The traceability audit checks real compiled call expressions for
            # onDeath -> commitCombatLoss, excluding strings and declarations.
            checked.append(physical["id"])
    receipts = [json.loads(line.removeprefix("TRACEABILITY "))
                for line in transcript.decode().splitlines() if line.startswith("TRACEABILITY ")]
    receipts = [row for row in receipts if row["requirement"] in REQUIREMENTS]
    for requirement in REQUIREMENTS:
        assert {row["case"] for row in receipts if row["requirement"] == requirement} == {"success", "failure", "stale", "replay"}
    assert len(receipts) == 12
    vectors = [json.loads(line.removeprefix("TRADITION_ORACLE "))
               for line in transcript.decode().splitlines() if line.startswith("TRADITION_ORACLE ")]
    assert vectors
    for vector in vectors:
        oracle_definitions = json.loads(json.dumps(definitions))
        source = next(row for row in oracle_definitions["experienceSources"] if row["id"] == "enemy_kill")
        source.update(weightNumerator=vector["numerator"], weightDenominator=vector["denominator"])
        oracle = MilitaryTraditionRuntime(oracle_definitions, RecordingTraditionAdapter())
        oracle.change_unit("english_guard_formation", controller_id="player")
        earned = oracle.award([dict(sourceId="enemy_kill", unitId="english_guard_formation",
                                   enemyControllerId="france", amount=vector["amount"])])
        assert earned == vector["earned"]
    result = {**identity, "status": "pass", "requirements": list(REQUIREMENTS),
              "scope": "earned enemy-kill experience and persistence only",
              "artifactSha256": report["artifact"]["sha256"],
              "executionLogSha256": execution["logSha256"], "maps": checked,
              "productionJourneys": coverage["military_tradition"],
              "receipts": len(receipts), "weightedOracleVectors": vectors,
              "militarySchemaVersion": 7, "headlessTraditionSchemaVersion": 2,
              "campaignSchemaVersions": list(range(1, 9)), "remainingObligations": pending,
              "remainingPublicationBlockers": report["blockerCount"], "candidateReady": False,
              "realClientExecuted": False, "releaseCandidate": False,
              "releaseStatus": "blocked_pending_real_forsaken_kingdom_launch_smoke"}
    (args.output_dir / "scoped-evidence.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("PASS: same-source native callback execution, weighted oracle and diagnostic campaign; native launch remains open")


if __name__ == "__main__":
    main()

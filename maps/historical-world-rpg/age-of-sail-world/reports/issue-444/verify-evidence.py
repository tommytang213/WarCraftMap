#!/usr/bin/env python3
"""Bind recruited-hero lifecycle execution to the exact diagnostic campaign."""
import argparse
import json
import re
from pathlib import Path
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT / "tooling"), str(PROJECT.parent / "_shared/tooling")]
import requirement_traceability_audit as scenario
import requirement_traceability as trace
from hero_progression_catalog import load_catalog
from integration_evidence import source_identity
from warcraft_campaign import MpqReader
from wurst_execution import source_revision


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
    assert rows["REQ-0096.01"]["status"] == "pass", rows["REQ-0096.01"]["blockerClasses"]
    assert not report["candidateReady"] and report["blockerCount"] > 0
    catalog, _ = load_catalog()
    duration = catalog["defeatRecovery"]["recoveryDays"]
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
            assert runtime["heroRecoveryDays"] == duration
            script = nested.read("war3map.lua").decode()
            for marker in ("Condition: wounded", "campaign days remaining", "Condition: ready",
                           "recoveryDay", "incapacitated", "rememberDefeatedLocation", "subscribeDays"):
                assert marker in script, (physical["id"], marker)
            # The pinned optimizer inlines defeatHero/advanceRecovery. Check
            # real assignments, never their names in stack-trace strings.
            fragments = trace.compiled_fragments({"script": script})
            for pattern in (r'RpgHero_incapacitated_storage\w*\[[^\]]+\]\s*=\s*true\b',
                            r'RpgHero_incapacitated_storage\w*\[[^\]]+\]\s*=\s*false\b',
                            r'RpgHero_recoveryDay_storage\w*\[[^\]]+\]\s*=\s*\([^\n]+\+[^\n]+\)',
                            r'RpgHero_recoveryDay_storage\w*\[[^\]]+\]\s*=\s*0\b'):
                assert any(re.match(pattern, fragment) for fragment in fragments), (physical["id"], pattern)
            # This generated assignment indexes through runtime.heroes (nested
            # brackets); inspect masked Lua so quoted diagnostics cannot match.
            policy = r'(?m)^\s*HeroRoster_recoveryDays_storage\w*\[[^\n]+\]\s*=\s*' + str(duration) + r'\b'
            assert re.search(policy, trace.lua_code_mask(script)), physical["id"]
            checked.append(physical["id"])
    receipts = [json.loads(line.removeprefix("TRACEABILITY "))
                for line in transcript.decode().splitlines() if line.startswith("TRACEABILITY ")]
    receipts = [row for row in receipts if row["requirement"] == "REQ-0096.01"]
    assert {row["case"] for row in receipts} == {"success", "failure", "stale", "replay"}
    assert len(receipts) == 4
    result = {**identity, "status": "pass", "requirement": "REQ-0096.01",
              "scope": "recruited-hero defeat, campaign-time recovery and incapacitated-party persistence",
              "artifactSha256": report["artifact"]["sha256"],
              "executionLogSha256": execution["logSha256"], "maps": checked,
              "receipts": len(receipts), "recoveryDays": duration, "rpgSchemaVersion": 5,
              "partyLocationVersion": 1, "campaignSchemaVersions": list(range(1, 9)),
              "remainingPublicationBlockers": report["blockerCount"], "candidateReady": False,
              "realClientExecuted": False, "releaseCandidate": False,
              "releaseStatus": "blocked_pending_real_forsaken_kingdom_launch_smoke"}
    (args.output_dir / "scoped-evidence.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("PASS: same-revision hero defeat/recovery execution and diagnostic campaign; native launch remains open")


if __name__ == "__main__":
    main()

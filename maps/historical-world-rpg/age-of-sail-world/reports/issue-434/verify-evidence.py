#!/usr/bin/env python3
"""Check first-recruitment evidence against the same-revision diagnostic W3N."""
import argparse
import json
from pathlib import Path
import re
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT / "tooling"), str(PROJECT.parent / "_shared/tooling")]
import requirement_traceability_audit as scenario
import requirement_traceability as trace
from hero_progression_catalog import load_catalog
from hero_starting_profiles import starting_definitions, rank_text
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
    required = rows["REQ-0093.01"]
    assert required["status"] == "pass", required["blockerClasses"]
    downstream = ["ROAD-0135.01", "REQ-0091.01", "REQ-0092.01", "REQ-0094.02"]
    assert all(rows[ident]["status"] == "fail" for ident in downstream)
    assert not report["candidateReady"] and report["blockerCount"] > 0
    catalog, _ = load_catalog()
    world = trace.load(PROJECT / "scenario/world/world.json")
    expected = starting_definitions(world, catalog)
    physical_maps = trace.load(PROJECT / "physical-maps.json")["physicalMaps"]
    archive = MpqReader(args.artifact)
    checked = []
    compiled_starts = {}
    with tempfile.TemporaryDirectory(dir=args.output_dir) as temporary:
        for physical in physical_maps:
            if physical.get("bootstrap"):
                continue
            path = Path(temporary) / (physical["id"] + ".w3x")
            path.write_bytes(archive.read(physical["packagePath"]))
            nested = MpqReader(path)
            assert json.loads(nested.read("runtime/build-identity.json")) == identity
            runtime = json.loads(nested.read("runtime/scenario-runtime.json"))
            assert runtime["heroStartingDefinitions"] == expected
            script = nested.read("war3map.lua").decode()
            # State, inspection, migration and registered calls must survive
            # compilation; the traceability audit separately checks live calls.
            for marker in ("skillRanks", "masteryRanks", "startingProfile", "Personal tree: ",
                           "That character's starting progression is invalid."):
                assert marker in script, (physical["id"], marker)
            # The pinned optimizer inlines constructors. Verify actual literal
            # starting fields after each generated hero identity, excluding
            # declarations, comments and strings containing source-like text.
            found = {}
            ident = None
            fragments = trace.compiled_fragments({"script": script})
            for fragment in fragments:
                match = re.fullmatch(r'RpgHero_id_storage\[[^\]]+\]\s*=\s*("[^"]+")\s*', fragment)
                if match:
                    ident = json.loads(match[1])
                    assert ident not in found, (physical["id"], ident)
                    found[ident] = {}
                match = re.fullmatch(r'HeroStartingProfile_(level|skills|masteries|personalTreeId)_storage\[[^\]]+\]\s*=\s*("[^"]*"|\d+)\s*', fragment)
                if match and ident is not None:
                    assert match[1] not in found[ident], (physical["id"], ident, match[1])
                    found[ident][match[1]] = json.loads(match[2])
            expected_fields = {ident: {"level": profile["level"], "skills": rank_text(profile["skills"]),
                                      "masteries": rank_text(profile["masteries"]),
                                      "personalTreeId": profile["personalTreeId"]}
                               for ident, profile in expected["profiles"].items()}
            assert found == expected_fields, (physical["id"], found)
            for state, definition in (("level", "level"), ("skillRanks", "skills"),
                                      ("masteryRanks", "masteries"), ("signatureProgressionId", "personalTreeId")):
                mutation = r'RpgHero_' + state + r'_storage\[[^\]]+\]\s*=\s*HeroStartingProfile_' + definition + r'_storage\['
                assert any(re.match(mutation, fragment) for fragment in fragments), (physical["id"], state)
            compiled_starts[physical["id"]] = len(found)
            checked.append(physical["id"])
    receipts = [json.loads(line.removeprefix("TRACEABILITY "))
                for line in transcript.decode().splitlines() if line.startswith("TRACEABILITY ")]
    receipts = [row for row in receipts if row["requirement"] == "REQ-0093.01"]
    assert {row["case"] for row in receipts} == {"success", "failure", "stale", "replay"}
    assert len(receipts) == 4
    result = {**identity, "status": "pass", "scope": "existing composed starting profiles at live first recruitment",
              "requirement": "REQ-0093.01", "artifactSha256": report["artifact"]["sha256"],
              "executionLogSha256": execution["logSha256"], "profilesPerRegionalMap": len(expected["profiles"]),
              "maps": checked, "receipts": len(receipts), "rpgSchemaVersion": 4,
              "compiledStartingDefinitions": compiled_starts,
              "legacyRpgSchemas": [1, 2, 3], "retainedObligations": downstream,
              "remainingPublicationBlockers": report["blockerCount"], "candidateReady": False,
              "realClientExecuted": False, "releaseCandidate": False,
              "releaseStatus": "blocked_pending_real_forsaken_kingdom_launch_smoke"}
    (args.output_dir / "scoped-evidence.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("PASS: starting-profile registration/state in the same-revision diagnostic; broader progression and native launch remain open")


if __name__ == "__main__":
    main()

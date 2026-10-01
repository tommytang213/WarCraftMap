#!/usr/bin/env python3
"""Validate and report Phase 8 quest, character, and treasure coverage."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/phase8-content-coverage.json"


def build():
    quests = json.loads((ROOT / "scenario/campaign-quests.json").read_text())
    treasure = json.loads((ROOT / "scenario/treasures/age-of-sail.json").read_text())
    regions = quests["coverageTargets"]["majorRegions"]
    by_region = defaultdict(Counter)
    characters = Counter()
    for quest in quests["quests"]:
        by_region[quest["region"]][quest["chainKind"]] += 1
        for stage in quest["stages"]:
            for objective in stage["objectives"]:
                for kind, ident in objective["refs"]:
                    if kind == "character": characters[ident] += 1
    treasure_region = Counter()
    treasure_kind = Counter()
    candidate_region = {x["id"]: x["regionId"] for x in treasure["candidateLocations"]}
    for item in treasure["treasures"]:
        treasure_kind[item["kind"]] += 1
        for region in {candidate_region[x] for x in item["candidateLocationIds"]}:
            treasure_region[region] += 1
        assert item["clueIds"] and item["guardIds"] and item["hazardIds"] and item["encounterIds"]
    for region in regions:
        assert by_region[region]["regional"] >= 2
        assert treasure_region[region] >= 3
    assert sum(characters.values()) >= 7 and treasure_kind["unique"] >= 6 and treasure_kind["generic"] >= 7
    return {
        "schemaVersion": 1,
        "quests": {"total": len(quests["quests"]), "byType": dict(sorted(Counter(q["chainKind"] for q in quests["quests"]).items())), "byRegionAndType": {r: dict(sorted(by_region[r].items())) for r in sorted(by_region)}},
        "characters": {"withQuestObjectives": dict(sorted(characters.items()))},
        "treasures": {"total": len(treasure["treasures"]), "byKind": dict(sorted(treasure_kind.items())), "byRegion": dict(sorted(treasure_region.items()))},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--write", action="store_true"); args = parser.parse_args()
    report = build()
    if args.write:
        REPORT.parent.mkdir(exist_ok=True); REPORT.write_text(json.dumps(report, indent=2) + "\n")
    elif not REPORT.exists() or json.loads(REPORT.read_text()) != report:
        raise SystemExit("Phase 8 content report is stale; run tooling/phase8_content_coverage.py --write")
    print(f"validated {report['quests']['total']} quests and {report['treasures']['total']} treasures")

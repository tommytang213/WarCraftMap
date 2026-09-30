import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))

from diplomacy import DiplomacyRuntime, DiplomacySaveAdapter
from polity import PolityRuntime
from province import ProvinceRuntime
from southeast_asia_politics import PoliticsError, project, validate
from timeline_simulation import TimelineHarness


class SoutheastAsiaPoliticsTests(unittest.TestCase):
    def setUp(self):
        self.source_path = ROOT / "scenario/politics/southeast-asia-1450.json"
        self.data = json.loads(self.source_path.read_text())
        self.world = json.loads((ROOT / "scenario/world/world.json").read_text())

    def test_projection_hierarchy_coverage_evidence_and_stable_ids(self):
        result = validate()
        self.assertEqual((27, 28, 1, 0), (
            len(result["polities"]),
            sum(len(polity["provinces"]) for polity in result["polities"]),
            len(result["sovereigntyRelationships"]),
            len(result["activeConflicts"]),
        ))
        self.assertEqual(self.world, project(copy.deepcopy(result), copy.deepcopy(self.world)))
        holdings = {row["territory"]["id"]: row for row in self.world["territorialHoldings"]}
        toungoo = holdings["toungoo"]
        self.assertEqual(
            ("toungoo_principality", "toungoo_principality", "toungoo_principality", "ava_kingdom", 70, 10),
            (toungoo["legalOwner"]["id"], toungoo["controllerPolityId"], toungoo["governingPolityId"],
             toungoo["sovereignPolityId"], toungoo["autonomyPercent"], toungoo["overlordTaxRatePercent"]),
        )
        preserved = {name for polity in result["polities"] for name in polity.get("preservedEntities", [])}
        self.assertTrue({"Tondo", "Demak", "Jailolo", "Nakhon Si Thammarat"} <= preserved)
        self.assertEqual(len({p["id"] for p in result["polities"]}), len(result["polities"]))

    def test_overlap_cycle_grant_participants_geography_evidence_and_modern_borders_rejected(self):
        candidates = []
        overlap = copy.deepcopy(self.data)
        overlap["polities"][1]["provinces"].append(copy.deepcopy(overlap["polities"][0]["provinces"][0]))
        candidates.append((overlap, "overlaps"))
        cycle = copy.deepcopy(self.data)
        cycle["sovereigntyRelationships"].append({"id":"ava_toungoo_cycle","kind":"vassal","subjectPolityId":"ava_kingdom","overlordPolityId":"toungoo_principality","taxRatePercent":1,"obligations":["service"]})
        candidates.append((cycle, "cycle"))
        grant = copy.deepcopy(self.data)
        grant["sovereigntyRelationships"][0]["taxRatePercent"] = 101
        candidates.append((grant, "impossible grant"))
        participant = copy.deepcopy(self.data)
        participant["diplomaticRelations"][0]["secondPolityId"] = "missing"
        candidates.append((participant, "invalid participants"))
        geography = copy.deepcopy(self.data)
        geography["polities"][0]["geographicFeatureIds"] = ["modern_border"]
        candidates.append((geography, "invalid geography"))
        evidence = copy.deepcopy(self.data)
        evidence["polities"][0]["evidenceIds"] = ["missing"]
        candidates.append((evidence, "invalid historical evidence"))
        modern = copy.deepcopy(self.data)
        modern["polities"][0]["provinces"][0]["name"] = "Modern Country Border"
        candidates.append((modern, "modern-border-only"))
        with tempfile.TemporaryDirectory() as tmp:
            for index, (candidate, pattern) in enumerate(candidates):
                path = Path(tmp) / f"candidate-{index}.json"
                path.write_text(json.dumps(candidate))
                with self.subTest(pattern=pattern), self.assertRaisesRegex(PoliticsError, pattern):
                    validate(path, require_projection=False)

    def test_deterministic_load_save_checkpoint_and_long_timeline_diplomacy_invariants(self):
        polities = PolityRuntime(self.world)
        provinces = ProvinceRuntime(self.world, polities)
        first = DiplomacyRuntime(polities, provinces, initial_conflicts=self.data["activeConflicts"])
        second = DiplomacyRuntime(polities, provinces, initial_conflicts=self.data["activeConflicts"])
        self.assertEqual(first.snapshot(), second.snapshot())
        self.assertEqual("neutral", first.relation("majapahit_empire", "sunda_kingdom"))
        rivalry = self.data["diplomaticRelations"][0]
        self.assertEqual(("ternate_sultanate", "tidore_sultanate", "rivalry"),
                         (rivalry["firstPolityId"], rivalry["secondPolityId"], rivalry["kind"]))
        saved = DiplomacySaveAdapter(first, {"calendar":{"day":1}}).capture_world()
        restored = DiplomacyRuntime(polities, provinces)
        restored.restore(saved["diplomacyState"])
        self.assertEqual(first.snapshot(), restored.snapshot())
        initial = {"diplomacyState": first.snapshot(), "provinceState": provinces.snapshot()}

        def configure(harness):
            def invariant(state, _context):
                runtime = DiplomacyRuntime(polities, provinces)
                runtime.restore(state["diplomacyState"])
                self.assertEqual("neutral", runtime.relation("majapahit_empire", "sunda_kingdom"))
                self.assertEqual(set(initial["provinceState"]), set(state["provinceState"]))
                state["diplomacyState"] = runtime.snapshot()
            harness.register_step("military", "southeast_asia_political_invariants", invariant)

        full = TimelineHarness(seed=1450, start_time=0, state=copy.deepcopy(initial))
        configure(full)
        expected = full.run(end_time=1000, step_size=25)
        split = TimelineHarness(seed=1450, start_time=0, state=copy.deepcopy(initial))
        configure(split)
        split.run(end_time=500, step_size=25)
        resumed = TimelineHarness.from_checkpoint(split.checkpoint())
        configure(resumed)
        actual = resumed.run(end_time=1000, step_size=25)
        self.assertEqual(expected["stateHash"], actual["stateHash"])


if __name__ == "__main__":
    unittest.main()

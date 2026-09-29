import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))
from middle_east_india_politics import PoliticsError, project, validate
from diplomacy import DiplomacyRuntime, DiplomacySaveAdapter
from polity import PolityRuntime
from province import ProvinceRuntime
from timeline_simulation import TimelineHarness


class MiddleEastIndiaPoliticsTests(unittest.TestCase):
    def setUp(self):
        self.source_path = ROOT / "scenario/politics/middle-east-india-1450.json"
        self.data = json.loads(self.source_path.read_text())
        self.world = json.loads((ROOT / "scenario/world/world.json").read_text())

    def test_baseline_projection_titles_hierarchy_and_geography_validate(self):
        result = validate()
        self.assertEqual((37, 40, 2, 1), (len(result["polities"]), sum(len(p["provinces"]) for p in result["polities"]), len(result["sovereigntyRelationships"]), len(result["activeConflicts"])))
        self.assertEqual(self.world, project(copy.deepcopy(result), copy.deepcopy(self.world)))
        holdings = {h["territory"]["id"]: h for h in self.world["territorialHoldings"]}
        hejaz = holdings["hejaz"]
        dimensions = (hejaz["legalOwner"]["id"], hejaz["controllerPolityId"], hejaz["sovereignPolityId"], hejaz["autonomyPercent"], hejaz["overlordTaxRatePercent"])
        self.assertEqual(("sharifate_mecca", "sharifate_mecca", "mamluk_sultanate", 70, 10), dimensions)
        self.assertTrue({"Kingdom of Mewar", "Ahom Kingdom", "Garha-Katanga"} <= {name for p in result["polities"] for name in p.get("preservedEntities", [])})

    def test_invalid_overlap_cycle_grant_participant_and_geography_are_rejected(self):
        candidates = []
        overlap = copy.deepcopy(self.data); overlap["polities"][1]["provinces"].append(copy.deepcopy(overlap["polities"][0]["provinces"][0])); candidates.append((overlap, "overlaps"))
        cycle = copy.deepcopy(self.data); cycle["sovereigntyRelationships"].append({"id":"mamluk_mecca_cycle","kind":"vassal","subjectPolityId":"mamluk_sultanate","overlordPolityId":"sharifate_mecca","taxRatePercent":1,"obligations":["service"]}); candidates.append((cycle, "cycle"))
        grant = copy.deepcopy(self.data); grant["sovereigntyRelationships"][0]["taxRatePercent"] = 101; candidates.append((grant, "impossible grant"))
        conflict = copy.deepcopy(self.data); conflict["activeConflicts"][0]["defenderPolityIds"] = ["missing"]; candidates.append((conflict, "invalid participants"))
        geography = copy.deepcopy(self.data); geography["polities"][0]["geographicFeatureIds"] = ["modern_border"]; candidates.append((geography, "invalid geography"))
        with tempfile.TemporaryDirectory() as tmp:
            for index, (candidate, pattern) in enumerate(candidates):
                path = Path(tmp) / f"candidate-{index}.json"; path.write_text(json.dumps(candidate))
                with self.subTest(pattern=pattern), self.assertRaisesRegex(PoliticsError, pattern):
                    validate(path, require_projection=False)

    def test_deterministic_load_persistence_checkpoint_resume_and_long_timeline(self):
        polities = PolityRuntime(self.world); provinces = ProvinceRuntime(self.world, polities)
        first = DiplomacyRuntime(polities, provinces, initial_conflicts=self.data["activeConflicts"])
        second = DiplomacyRuntime(polities, provinces, initial_conflicts=self.data["activeConflicts"])
        self.assertEqual(first.snapshot(), second.snapshot()); self.assertEqual("war", first.relation("qara_qoyunlu", "aq_qoyunlu"))
        saved = DiplomacySaveAdapter(first, {"calendar":{"day":1}}).capture_world()
        restored = DiplomacyRuntime(polities, provinces); restored.restore(saved["diplomacyState"]); self.assertEqual(first.snapshot(), restored.snapshot())
        initial = {"diplomacyState": first.snapshot(), "provinceState": provinces.snapshot()}
        def configure(harness):
            def invariant(state, _context):
                runtime = DiplomacyRuntime(polities, provinces); runtime.restore(state["diplomacyState"])
                self.assertEqual("war", runtime.relation("qara_qoyunlu", "aq_qoyunlu")); state["diplomacyState"] = runtime.snapshot()
            harness.register_step("military", "mei_political_invariants", invariant)
        full = TimelineHarness(seed=1450, start_time=0, state=copy.deepcopy(initial)); configure(full); expected = full.run(end_time=1000, step_size=25)
        split = TimelineHarness(seed=1450, start_time=0, state=copy.deepcopy(initial)); configure(split); split.run(end_time=500, step_size=25); checkpoint = split.checkpoint()
        resumed = TimelineHarness.from_checkpoint(checkpoint); configure(resumed); actual = resumed.run(end_time=1000, step_size=25)
        self.assertEqual(expected["stateHash"], actual["stateHash"])


if __name__ == "__main__": unittest.main()

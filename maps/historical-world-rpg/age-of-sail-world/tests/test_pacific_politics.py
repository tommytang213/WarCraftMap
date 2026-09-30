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
from pacific_politics import PoliticsError, project, validate
from polity import PolityRuntime
from province import ProvinceRuntime
from timeline_simulation import TimelineHarness


class PacificPoliticsTests(unittest.TestCase):
    def setUp(self):
        self.source = ROOT / "scenario/politics/pacific-1450.json"
        self.data = json.loads(self.source.read_text())
        self.world = json.loads((ROOT / "scenario/world/world.json").read_text())

    def test_projection_coverage_centers_structures_and_stable_ids(self):
        result = validate()
        self.assertEqual((24, 24, 0), (len(result["polities"]),
                         sum(len(p["provinces"]) for p in result["polities"]),
                         len(result["activeConflicts"])))
        self.assertEqual(self.world, project(copy.deepcopy(result), copy.deepcopy(self.world)))
        self.assertEqual(6, len({p["regionalInstanceId"] for p in result["polities"]}))
        self.assertTrue({"kingdom", "paramount_chiefdom", "chiefdoms", "confederated", "decentralized"}
                        <= {p["structure"] for p in result["polities"]})
        self.assertTrue(all(p.get("capitalSettlementId") for p in result["polities"]))
        distributed = {"chiefdoms", "confederated", "decentralized"}
        self.assertTrue(all(p.get("capitalException") for p in result["polities"]
                            if p["structure"] in distributed))
        preserved = {name for p in result["polities"] for name in p["preservedEntities"]}
        self.assertTrue({"Manu‘a", "Raiatea sacred center", "Torres Strait islanders",
                         "Ngāi Tahu", "Ni‘ihau chiefs"} <= preserved)
        polity_ids = [p["id"] for p in result["polities"]]
        province_ids = [v["id"] for p in result["polities"] for v in p["provinces"]]
        self.assertEqual(len(polity_ids), len(set(polity_ids)))
        self.assertEqual(len(province_ids), len(set(province_ids)))

    def test_overlap_cycle_grant_participant_geography_evidence_coverage_and_modern_border_rejected(self):
        cases = []
        overlap = copy.deepcopy(self.data)
        overlap["polities"][1]["provinces"].append(copy.deepcopy(overlap["polities"][0]["provinces"][0]))
        cases.append((overlap, "overlaps"))
        cycle = copy.deepcopy(self.data)
        cycle["sovereigntyRelationships"] = [
            {"id":"a_to_b","kind":"tributary","subjectPolityId":"hawaii_chiefdom","overlordPolityId":"maui_chiefdom","taxRatePercent":5,"obligations":["tribute"]},
            {"id":"b_to_a","kind":"tributary","subjectPolityId":"maui_chiefdom","overlordPolityId":"hawaii_chiefdom","taxRatePercent":5,"obligations":["tribute"]}]
        cases.append((cycle, "cycle"))
        grant = copy.deepcopy(self.data)
        grant["sovereigntyRelationships"] = [{"id":"bad_grant","kind":"tributary","subjectPolityId":"hawaii_chiefdom","overlordPolityId":"maui_chiefdom","taxRatePercent":101,"obligations":["tribute"]}]
        cases.append((grant, "impossible grant"))
        participant = copy.deepcopy(self.data); participant["diplomaticRelations"][0]["secondPolityId"] = "missing"
        cases.append((participant, "invalid participants"))
        geography = copy.deepcopy(self.data); geography["polities"][0]["geographicFeatureIds"] = ["missing"]
        cases.append((geography, "invalid geography"))
        evidence = copy.deepcopy(self.data); evidence["polities"][0]["evidenceIds"] = ["missing"]
        cases.append((evidence, "invalid historical evidence"))
        coverage = copy.deepcopy(self.data)
        coverage["polities"] = [p for p in coverage["polities"] if p["regionalInstanceId"] != "pacific_new_zealand"]
        cases.append((coverage, "missing authoritative coverage"))
        modern = copy.deepcopy(self.data); modern["polities"][0]["provinces"][0]["name"] = "Modern National Border"
        cases.append((modern, "modern-border-only"))
        with tempfile.TemporaryDirectory() as tmp:
            for index, (candidate, pattern) in enumerate(cases):
                path = Path(tmp) / f"candidate-{index}.json"; path.write_text(json.dumps(candidate))
                with self.subTest(pattern=pattern), self.assertRaisesRegex(PoliticsError, pattern):
                    validate(path, require_projection=False)

    def test_deterministic_persistence_checkpoint_and_long_timeline_invariants(self):
        polities = PolityRuntime(self.world); provinces = ProvinceRuntime(self.world, polities)
        first = DiplomacyRuntime(polities, provinces, initial_conflicts=self.data["activeConflicts"])
        second = DiplomacyRuntime(polities, provinces, initial_conflicts=self.data["activeConflicts"])
        self.assertEqual(first.snapshot(), second.snapshot())
        self.assertEqual("neutral", first.relation("tui_tonga_empire", "samoan_chiefly_districts"))
        saved = DiplomacySaveAdapter(first, {"calendar":{"day":1}}).capture_world()
        restored = DiplomacyRuntime(polities, provinces); restored.restore(saved["diplomacyState"])
        self.assertEqual(first.snapshot(), restored.snapshot())
        initial = {"diplomacyState": first.snapshot(), "provinceState": provinces.snapshot()}

        def configure(harness):
            def invariant(state, _context):
                runtime = DiplomacyRuntime(polities, provinces); runtime.restore(state["diplomacyState"])
                self.assertEqual("neutral", runtime.relation("tui_tonga_empire", "samoan_chiefly_districts"))
                self.assertEqual(set(initial["provinceState"]), set(state["provinceState"]))
                state["diplomacyState"] = runtime.snapshot()
            harness.register_step("military", "pacific_political_invariants", invariant)

        full = TimelineHarness(seed=1450, start_time=0, state=copy.deepcopy(initial)); configure(full)
        expected = full.run(end_time=1000, step_size=25)
        split = TimelineHarness(seed=1450, start_time=0, state=copy.deepcopy(initial)); configure(split)
        split.run(end_time=500, step_size=25)
        resumed = TimelineHarness.from_checkpoint(split.checkpoint()); configure(resumed)
        actual = resumed.run(end_time=1000, step_size=25)
        self.assertEqual(expected["stateHash"], actual["stateHash"])


if __name__ == "__main__":
    unittest.main()

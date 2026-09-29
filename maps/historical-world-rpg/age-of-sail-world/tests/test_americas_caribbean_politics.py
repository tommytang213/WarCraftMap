import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))

from americas_caribbean_politics import PoliticsError, project, validate
from diplomacy import DiplomacyRuntime, DiplomacySaveAdapter
from polity import PolityRuntime
from province import ProvinceRuntime
from timeline_simulation import TimelineHarness


class AmericasCaribbeanPoliticsTests(unittest.TestCase):
    def setUp(self):
        self.source_path = ROOT / "scenario/politics/americas-caribbean-1450.json"
        self.data = json.loads(self.source_path.read_text())
        self.world = json.loads((ROOT / "scenario/world/world.json").read_text())

    def test_projection_coverage_titles_evidence_capitals_and_stable_ids(self):
        result = validate()
        self.assertEqual((32, 33, 0, 1), (
            len(result["polities"]), sum(len(p["provinces"]) for p in result["polities"]),
            len(result["sovereigntyRelationships"]), len(result["activeConflicts"])))
        self.assertEqual(self.world, project(copy.deepcopy(result), copy.deepcopy(self.world)))
        instances = {p["regionalInstanceId"] for p in result["polities"]}
        self.assertTrue({"americas_north_atlantic", "americas_north_pacific", "americas_mexico_central",
                         "americas_caribbean_islands", "americas_north_south", "americas_amazon_brazil",
                         "americas_andes_southern_cone"} <= instances)
        preserved = {name for p in result["polities"] for name in p.get("preservedEntities", [])}
        self.assertTrue({"Mohawk nation", "Tlingit clans", "Tlatelolco", "Maní", "Marién",
                         "Chanka communities", "Tapajós chiefdoms", "Huilliche communities"} <= preserved)
        polity_ids = [p["id"] for p in result["polities"]]
        province_ids = [v["id"] for p in result["polities"] for v in p["provinces"]]
        self.assertEqual(len(polity_ids), len(set(polity_ids)))
        self.assertEqual(len(province_ids), len(set(province_ids)))
        for polity in result["polities"]:
            self.assertTrue(polity.get("capitalSettlementId"))
            if polity.get("structure") in {"confederated", "decentralized"}:
                self.assertTrue(polity.get("capitalException"))

    def test_invalid_overlap_cycle_grant_conflict_geography_evidence_coverage_and_modern_border(self):
        candidates = []
        overlap = copy.deepcopy(self.data)
        overlap["polities"][1]["provinces"].append(copy.deepcopy(overlap["polities"][0]["provinces"][0]))
        candidates.append((overlap, "overlaps"))
        cycle = copy.deepcopy(self.data)
        cycle["sovereigntyRelationships"] = [
            {"id":"a_to_b","kind":"vassal","subjectPolityId":"acolhua_texcoco","overlordPolityId":"mexica_tenochtitlan","taxRatePercent":5,"obligations":["service"]},
            {"id":"b_to_a","kind":"vassal","subjectPolityId":"mexica_tenochtitlan","overlordPolityId":"acolhua_texcoco","taxRatePercent":5,"obligations":["service"]}]
        candidates.append((cycle, "cycle"))
        grant = copy.deepcopy(self.data)
        grant["sovereigntyRelationships"] = [{"id":"bad_grant","kind":"tributary","subjectPolityId":"acolhua_texcoco","overlordPolityId":"mexica_tenochtitlan","taxRatePercent":101,"obligations":["tribute"]}]
        candidates.append((grant, "impossible grant"))
        participant = copy.deepcopy(self.data); participant["activeConflicts"][0]["defenderPolityIds"] = ["missing"]
        candidates.append((participant, "invalid participants"))
        geography = copy.deepcopy(self.data); geography["polities"][0]["geographicFeatureIds"] = ["missing"]
        candidates.append((geography, "invalid geography"))
        evidence = copy.deepcopy(self.data); evidence["polities"][0]["evidenceIds"] = ["missing"]
        candidates.append((evidence, "invalid historical evidence"))
        coverage = copy.deepcopy(self.data)
        removed = {p["id"] for p in coverage["polities"] if p["regionalInstanceId"] == "americas_north_south"}
        coverage["polities"] = [p for p in coverage["polities"] if p["regionalInstanceId"] != "americas_north_south"]
        coverage["diplomaticRelations"] = [r for r in coverage["diplomaticRelations"]
                                            if r["firstPolityId"] not in removed and r["secondPolityId"] not in removed]
        candidates.append((coverage, "missing authoritative coverage"))
        modern = copy.deepcopy(self.data); modern["polities"][0]["provinces"][0]["name"] = "Modern National Border"
        candidates.append((modern, "modern-border-only"))
        with tempfile.TemporaryDirectory() as tmp:
            for index, (candidate, pattern) in enumerate(candidates):
                path = Path(tmp) / f"candidate-{index}.json"; path.write_text(json.dumps(candidate))
                with self.subTest(pattern=pattern), self.assertRaisesRegex(PoliticsError, pattern):
                    validate(path, require_projection=False)

    def test_deterministic_diplomacy_persistence_checkpoint_and_long_timeline(self):
        polities = PolityRuntime(self.world); provinces = ProvinceRuntime(self.world, polities)
        first = DiplomacyRuntime(polities, provinces, initial_conflicts=self.data["activeConflicts"])
        second = DiplomacyRuntime(polities, provinces, initial_conflicts=self.data["activeConflicts"])
        self.assertEqual(first.snapshot(), second.snapshot())
        self.assertEqual("war", first.relation("mexica_tenochtitlan", "chalco_confederation"))
        saved = DiplomacySaveAdapter(first, {"calendar":{"day":1}}).capture_world()
        restored = DiplomacyRuntime(polities, provinces); restored.restore(saved["diplomacyState"])
        self.assertEqual(first.snapshot(), restored.snapshot())
        initial = {"diplomacyState": first.snapshot(), "provinceState": provinces.snapshot()}

        def configure(harness):
            def invariant(state, _context):
                runtime = DiplomacyRuntime(polities, provinces); runtime.restore(state["diplomacyState"])
                self.assertEqual("war", runtime.relation("mexica_tenochtitlan", "chalco_confederation"))
                self.assertEqual(set(initial["provinceState"]), set(state["provinceState"]))
                state["diplomacyState"] = runtime.snapshot()
            harness.register_step("military", "americas_political_invariants", invariant)

        full = TimelineHarness(seed=1450, start_time=0, state=copy.deepcopy(initial)); configure(full)
        expected = full.run(end_time=500, step_size=25)
        split = TimelineHarness(seed=1450, start_time=0, state=copy.deepcopy(initial)); configure(split)
        split.run(end_time=250, step_size=25)
        resumed = TimelineHarness.from_checkpoint(split.checkpoint()); configure(resumed)
        actual = resumed.run(end_time=500, step_size=25)
        self.assertEqual(expected["stateHash"], actual["stateHash"])


if __name__ == "__main__":
    unittest.main()

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
from east_asia_politics import PoliticsError, project, validate
from polity import PolityRuntime
from province import ProvinceRuntime
from timeline_simulation import TimelineHarness


class EastAsiaPoliticsTests(unittest.TestCase):
    def setUp(self):
        self.source_path = ROOT / "scenario/politics/east-asia-1450.json"
        self.data = json.loads(self.source_path.read_text())
        self.world = json.loads((ROOT / "scenario/world/world.json").read_text())

    def test_projection_hierarchy_coverage_titles_evidence_and_stable_ids(self):
        result = validate()
        self.assertEqual((16, 29, 5, 1), (
            len(result["polities"]),
            sum(len(polity["provinces"]) for polity in result["polities"]),
            len(result["sovereigntyRelationships"]),
            len(result["activeConflicts"]),
        ))
        self.assertEqual(self.world, project(copy.deepcopy(result), copy.deepcopy(self.world)))
        holdings = {row["territory"]["id"]: row for row in self.world["territorialHoldings"]}
        joseon = holdings["joseon_central_provinces"]
        self.assertEqual(
            ("joseon_kingdom", "joseon_kingdom", "joseon_kingdom", "ming_empire", 70, 4),
            (joseon["legalOwner"]["id"], joseon["controllerPolityId"], joseon["governingPolityId"],
             joseon["sovereignPolityId"], joseon["autonomyPercent"], joseon["overlordTaxRatePercent"]),
        )
        preserved = {name for polity in result["polities"] for name in polity.get("preservedEntities", [])}
        self.assertTrue({"Hosokawa clan", "Guge Kingdom", "Nivkh communities", "Siraya communities"} <= preserved)
        polity_ids = [polity["id"] for polity in result["polities"]]
        province_ids = [province["id"] for polity in result["polities"] for province in polity["provinces"]]
        self.assertEqual(len(polity_ids), len(set(polity_ids)))
        self.assertEqual(len(province_ids), len(set(province_ids)))
        exceptions = {polity["id"] for polity in result["polities"] if polity.get("capitalException")}
        self.assertEqual({"oirat_confederation", "northern_yuan_khanate", "jianzhou_jurchen", "haixi_jurchen",
                          "wild_jurchen_confederacies", "taiwan_indigenous_domains", "ainu_moshir",
                          "sakhalin_communities"}, exceptions)

    def test_overlap_cycle_grant_participants_geography_evidence_and_modern_borders_rejected(self):
        candidates = []
        overlap = copy.deepcopy(self.data)
        overlap["polities"][1]["provinces"].append(copy.deepcopy(overlap["polities"][0]["provinces"][0]))
        candidates.append((overlap, "overlaps"))
        cycle = copy.deepcopy(self.data)
        cycle["sovereigntyRelationships"].append({"id":"joseon_ming_cycle","kind":"vassal","subjectPolityId":"ming_empire","overlordPolityId":"joseon_kingdom","taxRatePercent":1,"obligations":["service"]})
        candidates.append((cycle, "cycle"))
        grant = copy.deepcopy(self.data)
        grant["sovereigntyRelationships"][0]["taxRatePercent"] = 101
        candidates.append((grant, "impossible grant"))
        participant = copy.deepcopy(self.data)
        participant["activeConflicts"][0]["defenderPolityIds"] = ["missing"]
        candidates.append((participant, "invalid participants"))
        geography = copy.deepcopy(self.data)
        geography["polities"][0]["geographicFeatureIds"] = ["modern_border"]
        candidates.append((geography, "invalid geography"))
        evidence = copy.deepcopy(self.data)
        evidence["polities"][0]["evidenceIds"] = ["missing"]
        candidates.append((evidence, "invalid historical evidence"))
        modern = copy.deepcopy(self.data)
        modern["polities"][0]["provinces"][0]["name"] = "Modern National Border"
        candidates.append((modern, "modern-border-only"))
        with tempfile.TemporaryDirectory() as tmp:
            for index, (candidate, pattern) in enumerate(candidates):
                path = Path(tmp) / f"candidate-{index}.json"
                path.write_text(json.dumps(candidate))
                with self.subTest(pattern=pattern), self.assertRaisesRegex(PoliticsError, pattern):
                    validate(path, require_projection=False)

    def test_deterministic_persistence_checkpoint_resume_and_long_timeline_invariants(self):
        polities = PolityRuntime(self.world)
        provinces = ProvinceRuntime(self.world, polities)
        first = DiplomacyRuntime(polities, provinces, initial_conflicts=self.data["activeConflicts"])
        second = DiplomacyRuntime(polities, provinces, initial_conflicts=self.data["activeConflicts"])
        self.assertEqual(first.snapshot(), second.snapshot())
        self.assertEqual("war", first.relation("oirat_confederation", "ming_empire"))
        saved = DiplomacySaveAdapter(first, {"calendar":{"day":1}}).capture_world()
        restored = DiplomacyRuntime(polities, provinces)
        restored.restore(saved["diplomacyState"])
        self.assertEqual(first.snapshot(), restored.snapshot())
        initial = {"diplomacyState": first.snapshot(), "provinceState": provinces.snapshot()}

        def configure(harness):
            def invariant(state, _context):
                runtime = DiplomacyRuntime(polities, provinces)
                runtime.restore(state["diplomacyState"])
                self.assertEqual("war", runtime.relation("oirat_confederation", "ming_empire"))
                self.assertEqual(set(initial["provinceState"]), set(state["provinceState"]))
                state["diplomacyState"] = runtime.snapshot()
            harness.register_step("military", "east_asia_political_invariants", invariant)

        full = TimelineHarness(seed=1450, start_time=0, state=copy.deepcopy(initial))
        configure(full)
        expected = full.run(end_time=2000, step_size=25)
        split = TimelineHarness(seed=1450, start_time=0, state=copy.deepcopy(initial))
        configure(split)
        split.run(end_time=1000, step_size=25)
        resumed = TimelineHarness.from_checkpoint(split.checkpoint())
        configure(resumed)
        actual = resumed.run(end_time=2000, step_size=25)
        self.assertEqual(expected["stateHash"], actual["stateHash"])


if __name__ == "__main__":
    unittest.main()

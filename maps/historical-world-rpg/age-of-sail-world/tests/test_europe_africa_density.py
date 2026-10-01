import copy, json, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tooling"))
from europe_africa_density import audit, markdown

class EuropeAfricaDensityTests(unittest.TestCase):
    def test_deterministic_density_report_and_global_roadmap_stays_open(self):
        report=audit()
        self.assertEqual(report,audit())
        self.assertFalse(report["globalRoadmapComplete"])
        self.assertEqual(156,report["regions"]["europe"]["settlementCount"])
        self.assertEqual(86,report["regions"]["africa"]["settlementCount"])
        self.assertIn("byPolityImportance",report["regions"]["europe"])
        self.assertEqual(markdown(report),(ROOT/"reports/europe-africa-settlement-density.md").read_text())

    def test_every_record_has_release_density_authority(self):
        for region in ("europe","africa"):
            source=json.loads((ROOT/f"scenario/settlements/{region}-1450.json").read_text())
            evidence={x["id"] for x in source["historicalEvidence"]}
            for row in source["settlements"]:
                self.assertTrue(set(row["historicalEvidenceIds"])<=evidence)
                self.assertEqual("1450-01-01",row["controlContext"]["date"])
                self.assertIn(row["physicalMapId"],{"europe_west","europe_central_east","africa"})
                self.assertEqual("abstract",next(x for x in json.loads((ROOT/"scenario/world/world.json").read_text())["settlements"] if x["id"]==row["id"])["activation"]["runtimeState"])

if __name__=="__main__": unittest.main()

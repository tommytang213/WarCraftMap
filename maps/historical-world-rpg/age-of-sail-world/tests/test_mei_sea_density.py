import json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"tooling"))
from mei_sea_density import audit, markdown

class MiddleEastIndiaSoutheastAsiaDensityTests(unittest.TestCase):
 def test_release_density_report_is_deterministic_and_roadmap_stays_open(self):
  report=audit(); self.assertEqual(report,audit()); self.assertFalse(report["globalRoadmapComplete"])
  self.assertEqual(155,report["regions"]["middle_east_india"]["settlementCount"]); self.assertEqual(85,report["regions"]["southeast_asia"]["settlementCount"])
  self.assertEqual(markdown(report),(ROOT/"reports/middle-east-india-southeast-asia-settlement-density.md").read_text())
 def test_projection_preserves_abstract_activation_and_administration_contracts(self):
  world=json.loads((ROOT/"scenario/world/world.json").read_text()); projected={x["id"]:x for x in world["settlements"]}
  for region in ("middle-east-india","southeast-asia"):
   source=json.loads((ROOT/f"scenario/settlements/{region}-1450.json").read_text())
   for row in source["settlements"]:
    item=projected[row["id"]]; self.assertEqual("abstract",item["activation"]["runtimeState"]); self.assertTrue(item["capturable"]); self.assertTrue(item["cityCoreId"]); self.assertTrue(item["defenseLayoutId"])
if __name__=="__main__": unittest.main()

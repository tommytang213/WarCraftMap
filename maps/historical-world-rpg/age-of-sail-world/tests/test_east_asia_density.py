import copy, json, sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"tooling"))
from east_asia_density import audit, markdown

class EastAsiaDensityTests(unittest.TestCase):
 def test_release_density_and_reports_are_deterministic(self):
  report=audit(); self.assertEqual("complete",report["status"]); self.assertFalse(report["globalRoadmapComplete"])
  self.assertGreaterEqual(report["settlementCount"],110); self.assertGreaterEqual(report["portCount"],30)
  self.assertEqual(report,json.loads((ROOT/"reports/east-asia-settlement-density.json").read_text()))
  self.assertEqual(markdown(report),(ROOT/"reports/east-asia-settlement-density.md").read_text())
 def test_required_coverage_dimensions(self):
  report=audit()
  self.assertIn("administrative_seat",report["byRole"]); self.assertIn("production_center",report["byRole"])
  self.assertIn("grand_canal_and_yellow_river",report["byHistoricalNetwork"])
  self.assertEqual("authoritative_abstract_until_regional_activation",report["budgets"]["runtimePolicy"])

if __name__=="__main__": unittest.main()

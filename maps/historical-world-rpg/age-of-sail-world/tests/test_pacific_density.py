import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"tooling"))
from pacific_density import audit,markdown
class PacificDensityTests(unittest.TestCase):
 def test_report_is_deterministic_and_global_item_stays_open(self):
  report=audit(); self.assertFalse(report["globalRoadmapComplete"]); self.assertEqual(report,json.loads((ROOT/"reports/pacific-settlement-density.json").read_text())); self.assertEqual(markdown(report),(ROOT/"reports/pacific-settlement-density.md").read_text())
 def test_release_coverage_and_runtime_budgets(self):
  r=audit(); self.assertEqual(24,r["abstractCommunityCount"]); self.assertGreaterEqual(r["bySettlementRole"]["political_center"],24); self.assertLessEqual(max(r["byIslandGroup"].values()),10)
if __name__=="__main__": unittest.main()

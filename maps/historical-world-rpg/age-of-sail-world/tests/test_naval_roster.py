import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"tooling"))
from validate_naval_roster import validate
class NavalRosterTests(unittest.TestCase):
    def test_phase8_coverage_fleets_integrations_and_budgets(self):
        report=validate(); self.assertGreaterEqual(report["counts"]["navalArchetypes"],40); self.assertEqual(6,len(report["fleets"])); self.assertTrue(report["exceptions"]); self.assertEqual(0,report["counts"]["addedImports"])
if __name__=="__main__": unittest.main()

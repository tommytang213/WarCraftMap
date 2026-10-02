import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tooling"))
import progression_coverage

class ProgressionCoverageTests(unittest.TestCase):
 def test_report_covers_release_dimensions_and_is_current(self):
  actual=progression_coverage.build()
  saved=json.loads((ROOT/"reports/progression-coverage.json").read_text())
  self.assertEqual(saved,actual)
  self.assertGreaterEqual(actual["counts"]["crossTreeNodes"],40)
  self.assertGreaterEqual(actual["counts"]["maximumPrerequisiteDepth"],8)
  self.assertTrue(all(value for value in actual["byEra"].values()))
  self.assertEqual({"ability","building","modifier","policy","unit"},set(actual["byUnlockCategory"]))
  self.assertGreaterEqual(len(actual["byOriginRegion"]),4)

if __name__=="__main__": unittest.main()

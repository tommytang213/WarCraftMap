import copy, json, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"tooling"))
from americas_caribbean_density import DensityError, audit, markdown
from americas_caribbean_content import AmericasContentError, validate

class AmericasCaribbeanDensityTests(unittest.TestCase):
 def test_locked_density_coverage_and_report(self):
  report=audit(); self.assertEqual(155,report["settlementCount"]); self.assertFalse(report["globalRoadmapComplete"]); self.assertEqual(set(report["bySubregion"]),set(report["byPhysicalMap"])); self.assertGreaterEqual(len(report["byPolity"]),32); self.assertEqual(markdown(report),(ROOT/"reports/americas-caribbean-settlement-density.md").read_text())
 def test_all_start_available_and_bounded(self):
  report=audit(); self.assertEqual({"available_1450":155},report["byEraAvailability"]); self.assertLessEqual(max(report["byPhysicalMap"].values()),report["budgets"]["physicalMapMaximum"])
 def test_anachronistic_and_unsupported_records_rejected(self):
  source=json.loads((ROOT/"scenario/settlements/americas-caribbean-1450.json").read_text())
  for mutation,message in ((lambda x:x.update(availability={"from":"1607-05-14","to":None}),"anachronistic"),(lambda x:x.update(historicalEvidenceIds=["missing"]),"invalid evidence")):
   bad=copy.deepcopy(source); mutation(bad["settlements"][0])
   with tempfile.TemporaryDirectory() as d:
    p=Path(d)/"bad.json"; p.write_text(json.dumps(bad))
    with self.assertRaisesRegex(AmericasContentError,message): validate(p)
if __name__=="__main__": unittest.main()

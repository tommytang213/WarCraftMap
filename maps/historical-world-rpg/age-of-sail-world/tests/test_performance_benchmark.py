import copy,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"_shared/engine"));import performance_benchmark as b
CONFIG=Path(__file__).resolve().parents[1]/"scenario/benchmarks/performance.json"
class BenchmarkTests(unittest.TestCase):
 def setUp(self):self.profile=b.load_configuration(CONFIG)[1]["representative_development"]
 def test_configuration_and_deterministic_fixture(self):
  a=b.generate_fixture(self.profile);self.assertEqual(b.canonical(a),b.canonical(b.generate_fixture(self.profile)));self.assertNotIn(b"handle",b.canonical(a).lower());self.assertEqual(self.profile.workload["localRepresentations"],len(a["localWarcraftRepresentations"]))
 def test_transient_handles_rejected(self):
  f=b.generate_fixture(self.profile);f["authoritativeState"]["unitHandle"]=1
  with self.assertRaisesRegex(b.CorrectnessError,"transient"):b.validate_snapshot(f)
 def test_pass_and_over_budget_without_sleep(self):
  calls=[]
  def measured(f,p):calls.append(1);return {m:1 for m in b.METRICS}
  passing=copy.copy(self.profile);object.__setattr__(passing,"thresholds",{m:2 for m in b.METRICS});r=b.run(passing,{"revision":"test"},measured);self.assertTrue(r["passed"]);self.assertEqual(passing.warmups+passing.repeats,len(calls));self.assertEqual(1,r["fixtureVersion"])
  failing=copy.copy(passing);object.__setattr__(failing,"thresholds",{m:.5 for m in b.METRICS});r=b.run(failing,{},measured);self.assertEqual("performance_budget_failure",r["status"]);self.assertIn("exceeds budget",r["failures"][0]["message"])
 def test_correctness_failure_is_distinct(self):
  r=b.run(self.profile,{},lambda f,p:(_ for _ in ()).throw(b.CorrectnessError("broken invariant")));self.assertEqual("correctness_failure",r["status"]);self.assertEqual("correctness",r["failures"][0]["kind"])
if __name__=="__main__":unittest.main()

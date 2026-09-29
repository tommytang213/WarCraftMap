import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"_shared/engine"));import large_world_stress as stress
CONFIG=PROJECT/"scenario/benchmarks/large-world.json";CLI=PROJECT/"tooling/run_large_world_stress.py"
class LargeWorldStressTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.profiles=stress.load_profiles(CONFIG)[1];cls.profile=cls.profiles["small_correctness"]
 def test_generation_is_deterministic_and_complete(self):
  a=stress.generate_fixture(self.profile);b=stress.generate_fixture(self.profile);self.assertEqual(stress.fixture_hash(a),stress.fixture_hash(b));self.assertEqual(set(stress.ENTITY_KINDS),set(a["entities"]));self.assertEqual(dict(self.profile.counts),{k:len(v) for k,v in a["entities"].items()})
 def test_repeated_and_checkpoint_resumed_results_are_identical(self):
  initial=stress.generate_fixture(self.profile);full=copy.deepcopy(initial);stress.advance(full,self.profile.duration,self.profile.step_size,self.profile.representation_limit);repeat=copy.deepcopy(initial);stress.advance(repeat,self.profile.duration,self.profile.step_size,self.profile.representation_limit);split=copy.deepcopy(initial);stress.advance(split,self.profile.checkpoint_at,self.profile.step_size,self.profile.representation_limit);resumed=stress.resume(json.loads(stress.benchmark.canonical(stress.checkpoint(split))));stress.advance(resumed,self.profile.duration,self.profile.duration-self.profile.checkpoint_at,self.profile.representation_limit);self.assertEqual(stress.fixture_hash(full),stress.fixture_hash(repeat));self.assertEqual(stress.fixture_hash(full),stress.fixture_hash(resumed))
 def test_simultaneous_work_conservation_and_accelerated_jump(self):
  f=stress.generate_fixture(self.profile);currency=sum(x["currency"] for x in f["entities"]["markets"]);stress.advance(f,self.profile.duration,self.profile.duration,self.profile.representation_limit);self.assertEqual(len(f["scheduledWork"]),f["processedWork"]);self.assertEqual(currency,sum(x["currency"] for x in f["entities"]["markets"]));self.assertTrue(all(x["processed"] for x in f["scheduledWork"]))
 def test_inactive_regions_stay_abstract_as_world_scales(self):
  small=stress.generate_fixture(self.profile);large_profile=self.profiles["maximum_reasonable_world"];large=stress.generate_fixture(large_profile);self.assertLessEqual(len(stress.active_representations(small,self.profile.representation_limit)),self.profile.representation_limit);self.assertLessEqual(len(stress.active_representations(large,large_profile.representation_limit)),large_profile.representation_limit);self.assertGreater(sum(large_profile.counts.values()),sum(self.profile.counts.values())*20);self.assertNotIn(b"handle",stress.benchmark.canonical(large).lower())
 def test_malformed_references_and_invariants_name_stable_ids(self):
  cases=[];missing=stress.generate_fixture(self.profile);missing["entities"]["armies"][0]["ownerId"]="polity_missing";cases.append((missing,"reference","army_000000"));conservation=stress.generate_fixture(self.profile);conservation["entities"]["markets"][0]["stock"]+=1;cases.append((conservation,"conservation","markets"));scheduling=stress.generate_fixture(self.profile);scheduling["scheduledWork"][0]["targetId"]="polity_missing";cases.append((scheduling,"scheduling","scheduled_000000"))
  for fixture,invariant,entity_id in cases:
   with self.assertRaises(stress.InvariantFailure) as caught:stress.validate_fixture(fixture)
   self.assertEqual(invariant,caught.exception.diagnostic["invariant"]);self.assertEqual(entity_id,caught.exception.diagnostic["entityId"])
  checkpoint=stress.checkpoint(stress.generate_fixture(self.profile));checkpoint["state"]["time"]=1
  with self.assertRaisesRegex(stress.StressError,"hash mismatch"):stress.resume(checkpoint)
 def test_small_profile_budgets_and_machine_summary(self):
  result=stress.run_profile(self.profile);self.assertTrue(result["passed"],result["failures"]);self.assertEqual(stress.SUMMARY_FORMAT,result["format"]);self.assertLessEqual(len(result["failures"]),3)
  with tempfile.TemporaryDirectory() as temporary:
   output=Path(temporary)/"summary.json";completed=subprocess.run([sys.executable,str(CLI),"--summary-out",str(output)],text=True,capture_output=True,check=False);self.assertEqual(0,completed.returncode,completed.stderr or completed.stdout);self.assertEqual(json.loads(completed.stdout),json.loads(output.read_text()))
if __name__=="__main__":unittest.main()

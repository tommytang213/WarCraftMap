import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"));import final_performance_budget as b
CONFIG=ROOT/"scenario/benchmarks/final-budgets.json"; REPORTS=ROOT/"scenario/benchmarks/reports/final-measurements.json"
class FinalBudgetTests(unittest.TestCase):
 def setUp(self): self.config=b.load(CONFIG);self.reports=json.loads(REPORTS.read_text())
 def test_all_final_measurements_pass_both_profiles_and_output_is_stable(self):
  for profile in ("development","minimum_target"):
   result=b.compare(self.config,profile,self.reports);self.assertTrue(result["passed"]);self.assertEqual(b.canonical(result),b.canonical(b.compare(self.config,profile,self.reports)))
 def test_exact_boundary_passes(self):
  reports=copy.deepcopy(self.reports)
  for wid,w in self.config["workloads"].items():
   for key,rule in w["budgets"]["development"].items():reports[wid]["measurements"][key]=rule["limit"]
  self.assertTrue(b.compare(self.config,"development",reports)["passed"])
 def test_variance_size_timing_and_correctness_diagnostics_are_distinct(self):
  reports=copy.deepcopy(self.reports);reports["full_world_soak"]["timingCoefficientOfVariation"]["simulation_step_ms"]=.36
  reports["campaign_build"]["measurements"]["archive_bytes"]=67108865
  reports["transition_persistence"]["measurements"]["map_transition_ms"]=121
  reports["local_battle"]["correctnessFailures"]=[{"subsystem":"orders","map":"maximum_mixed","message":"fixture mismatch"}]
  result=b.compare(self.config,"development",reports);self.assertEqual({"variance","deterministic_size_limit","timing_regression","correctness"},{x["kind"] for x in result["failures"]})
  self.assertTrue(all(x.get("workload") and x.get("subsystem") for x in result["failures"]));self.assertIn("maximum_mixed",{x.get("map") for x in result["failures"]})
 def test_schema_rejects_keys_units_relationships_and_stale_measurements(self):
  broken=copy.deepcopy(self.config);broken["workloads"]["local_battle"]["budgets"]["development"]["orders_issued"]["unit"]="seconds"
  with self.assertRaises(b.BudgetConfigurationError):
   from tempfile import NamedTemporaryFile
   with NamedTemporaryFile("w+",suffix=".json") as f: json.dump(broken,f);f.flush();b.load(f.name)
  reports=copy.deepcopy(self.reports);reports["local_battle"]["measurements"]["unknown_metric"]=1
  result=b.compare(self.config,"development",reports)
  self.assertIn("measurement keys",result["failures"][0]["message"])
 def test_bounded_and_extended_profiles_share_one_versioned_configuration(self):
  self.assertEqual(1,self.config["budgetVersion"]);self.assertEqual(set(self.config["workloads"]),set(self.reports))
 def test_phase6_archive_and_audio_limits_remain_enforced(self):
  audit=json.loads((ROOT/"scenario/assets/phase6-audit.json").read_text())["budgets"]
  audio=json.loads((ROOT/"scenario/audio/manifest.json").read_text())["budgets"]
  rules=self.config["workloads"]["campaign_build"]["budgets"]
  for profile in ("development","minimum_target"):
   self.assertEqual(audit["maximumCampaignArchiveBytes"],rules[profile]["archive_bytes"]["limit"])
   self.assertEqual(audit["maximumImportedAssetBytes"],rules[profile]["imported_audio_bytes"]["limit"])
   self.assertEqual(audio["maximumDecodedBytes"],rules[profile]["decoded_audio_bytes"]["limit"])
   self.assertEqual(audit["maximumAudioChannels"],rules[profile]["active_audio_channels"]["limit"])
if __name__=="__main__":unittest.main()

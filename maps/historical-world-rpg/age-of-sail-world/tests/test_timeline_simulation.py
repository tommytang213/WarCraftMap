import copy, importlib.util, json, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CATEGORY=ROOT.parent
sys.path.insert(0,str(CATEGORY/"_shared"/"engine"))
from timeline_simulation import Diagnostic, FixtureError, SimulationFailure, SYSTEM_ORDER, TimelineHarness

CLI=ROOT/"tooling"/"simulate_timeline.py"
FIXTURES=Path(__file__).parent/"fixtures"/"timeline"
spec=importlib.util.spec_from_file_location("simulate_timeline",CLI)
command=importlib.util.module_from_spec(spec); spec.loader.exec_module(command)

class TimelineSimulationTests(unittest.TestCase):
    def fixture(self,name="short.json"):
        data=command.read(FIXTURES/name); digest=command.validate(data); return data,digest
    def harness(self,data,digest,seed=None):
        h=TimelineHarness(seed=data["seed"] if seed is None else seed,start_time=data["timeline"]["start"],state=data["initialState"],fixture_hash=digest); command.configure(h,data); return h
    def test_short_fixture_is_reproducible_and_events_are_ordered(self):
        data,digest=self.fixture(); one=self.harness(data,digest); two=self.harness(data,digest)
        a=one.run(end_time=12,step_size=2); b=two.run(end_time=12,step_size=2)
        self.assertEqual(a["stateHash"],b["stateHash"]); self.assertEqual(136,a["state"]["treasury"])
        self.assertEqual(["early","first","later"],[x["id"] for x in a["state"]["events"]])
    def test_fixed_seed_random_streams_differ_only_by_seed(self):
        def run(seed):
            h=TimelineHarness(seed=seed,start_time=0,state={"values":[]})
            h.register_step("world","random_sample",lambda state,ctx:state["values"].append(ctx.random_int("entity","growth",0,2**31)))
            return h.run(end_time=10,step_size=1)["state"]
        self.assertEqual(run(7),run(7)); self.assertNotEqual(run(7),run(8))
    def test_all_hooks_execute_in_stable_order(self):
        h=TimelineHarness(seed=0,start_time=0,state={"order":[]})
        for system in reversed(SYSTEM_ORDER): h.register_step(system,"record",lambda state,ctx:state["order"].append(ctx.system))
        self.assertEqual(list(SYSTEM_ORDER),h.run(end_time=1,step_size=1)["state"]["order"])
    def test_checkpoint_resume_equals_uninterrupted_and_has_no_handles(self):
        data,digest=self.fixture(); full=self.harness(data,digest).run(end_time=12,step_size=2)
        partial=self.harness(data,digest); partial.run(end_time=6,step_size=2); checkpoint=partial.checkpoint()
        self.assertNotIn("handle",json.dumps(checkpoint).lower())
        resumed=TimelineHarness.from_checkpoint(checkpoint,digest); command.configure(resumed,data)
        self.assertEqual(full["stateHash"],resumed.run(end_time=12,step_size=2)["stateHash"])
    def test_first_invariant_failure_names_time_system_and_entity(self):
        h=TimelineHarness(seed=0,start_time=0,state={"cash":1})
        h.register_step("economy","loss",lambda state,ctx:state.__setitem__("cash",state["cash"]-2))
        def check(state,ctx):
            return Diagnostic(ctx.time,ctx.system,"polity_one","cash_non_negative","cash failed") if state["cash"]<0 else None
        h.register_invariant("cash_non_negative",check)
        with self.assertRaises(SimulationFailure) as caught: h.run(end_time=5,step_size=1)
        self.assertEqual({"time":1,"system":"economy","entityId":"polity_one"},{k:caught.exception.diagnostic.to_dict()[k] for k in ("time","system","entityId")})
    def test_malformed_fixture_and_transient_state_are_rejected(self):
        data,_=self.fixture(); data["timeline"]["step"]=0
        with self.assertRaisesRegex(FixtureError,"positive"): command.validate(data)
        data,_=self.fixture(); data["initialState"]["unitHandle"]=123
        with self.assertRaisesRegex(FixtureError,"transient Warcraft handle"): command.validate(data)
    def test_multi_century_soak_is_bounded(self):
        data,digest=self.fixture("soak.json"); result=self.harness(data,digest).run(end_time=1820,step_size=1)
        self.assertEqual(370,result["steps"]); self.assertEqual(1037000,result["state"]["population"]); self.assertEqual(4,len(result["state"]["events"]))
    def test_cli_emits_json_and_resumed_comparison(self):
        with tempfile.TemporaryDirectory() as temporary:
            checkpoint=Path(temporary)/"checkpoint.json"
            first=subprocess.run([sys.executable,str(CLI),str(FIXTURES/"short.json"),"--end","6","--checkpoint-at","6","--checkpoint-out",str(checkpoint)],text=True,capture_output=True,check=False)
            self.assertEqual(0,first.returncode,first.stderr)
            resumed=subprocess.run([sys.executable,str(CLI),str(FIXTURES/"short.json"),"--resume",str(checkpoint),"--compare-uninterrupted"],text=True,capture_output=True,check=False)
            self.assertEqual(0,resumed.returncode,resumed.stderr); self.assertTrue(json.loads(resumed.stdout)["resumeEquivalent"])

if __name__=="__main__": unittest.main()

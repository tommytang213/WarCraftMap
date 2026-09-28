import copy, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "_shared" / "engine"))
import campaign_save as save
from autosave_scheduler import RollingAutosaveScheduler

class Harness:
    def __init__(self):
        self.storage=save.MemorySaveStorage(); self.safe=True
        self.world={"turn":0}; self.players={"one":{"gold":1}}
        self.manager=save.CampaignSaveManager(
            build_version="test", scenario_id="fixture", scenario_version="1",
            storage=self.storage, capture_state=lambda:(self.world,self.players),
            validate_state=lambda w,p:None, reconstruct_runtime=lambda w,p:None,
            activate_state=lambda w,p,r:setattr(self,"world",w), is_save_safe=lambda:self.safe)

class AutosaveSchedulerTests(unittest.TestCase):
    def test_all_fifteen_slots_wrap_and_equivalent_runs(self):
        def run():
            h=Harness(); s=RollingAutosaveScheduler(h.manager,5,now=10)
            return [s.tick(15+i*5,f"t{i}").slot_id for i in range(16)],s.metadata(90)
        expected=[f"autosave_{i:02d}" for i in range(1,16)]+["autosave_01"]
        self.assertEqual(expected,run()[0]); self.assertEqual(run(),run())

    def test_configurable_positive_interval(self):
        h=Harness(); s=RollingAutosaveScheduler(h.manager,7.5,now=2)
        self.assertIsNone(s.tick(9.49,"early")); self.assertEqual("saved",s.tick(9.5,"due").status)
        self.assertEqual(17.0,s.next_due)
        for invalid in (0,-1,True):
            with self.assertRaisesRegex(ValueError,"positive"): RollingAutosaveScheduler(h.manager,invalid)

    def test_unsafe_deferral_retries_intended_slot(self):
        h=Harness(); s=RollingAutosaveScheduler(h.manager,10); h.safe=False
        self.assertEqual("deferred",s.tick(10,"original").status); self.assertEqual(1,s.next_slot)
        h.safe=True
        self.assertEqual("autosave_01",s.tick(11,"ignored").slot_id); self.assertEqual(2,s.next_slot)

    def test_failure_retains_prior_slot_and_cursor(self):
        h=Harness(); s=RollingAutosaveScheduler(h.manager,1); s.tick(1,"first")
        previous=h.storage.read("autosave_01"); s.next_slot=1; s.next_due=2
        h.world["turn"]=2; h.storage.fail_next_write=True; result=s.tick(2,"failed")
        self.assertEqual("failed",result.status); self.assertIn("transactional write failed",result.diagnostic)
        self.assertEqual(previous,h.storage.read("autosave_01")); self.assertEqual(1,s.next_slot)

    def test_overlapping_requests_are_coalesced(self):
        h=Harness(); s=RollingAutosaveScheduler(h.manager,1); capture=h.manager.capture_state; nested=[]
        def reentrant_capture():
            nested.append(s.request(1,"nested")); return capture()
        h.manager.capture_state=reentrant_capture
        self.assertEqual("saved",s.request(1,"outer").status)
        self.assertEqual("coalesced",nested[0].status); self.assertEqual(2,s.next_slot)
        self.assertIsNone(h.storage.read("autosave_02"))

    def test_other_checkpoints_do_not_consume_rolling_slots(self):
        h=Harness(); s=RollingAutosaveScheduler(h.manager,5)
        for slot in (save.SaveSlot("manual",1),save.SaveSlot("session_start"),save.SaveSlot("major_milestone")):
            h.manager.save(slot,"checkpoint")
        self.assertEqual(1,s.next_slot); self.assertEqual("autosave_01",s.tick(5,"auto").slot_id)

    def test_boundary_round_trip_restore_and_migration(self):
        h=Harness(); s=RollingAutosaveScheduler(h.manager,20,now=100)
        s.next_slot=15; s.next_due=105
        self.assertEqual("autosave_15",s.tick(105,"boundary").slot_id)
        metadata=s.metadata(110); restored=RollingAutosaveScheduler(h.manager,20,now=999)
        restored.resume_after_load(copy.deepcopy(metadata),now=200)
        self.assertEqual((1,215),(restored.next_slot,restored.next_due))
        restored.resume_after_load({"version":0,"lastCompletedSlot":15,"secondsUntilDue":3},now=50)
        self.assertEqual((1,53),(restored.next_slot,restored.next_due))
        restored.resume_after_load(None,now=70)
        self.assertEqual((1,90),(restored.next_slot,restored.next_due))

if __name__=="__main__": unittest.main()

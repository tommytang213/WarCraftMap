import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from diplomacy import DiplomacyError,DiplomacyRuntime,DiplomacySaveAdapter,EVENT_CONSUMERS
from polity import PolityRuntime
from province import ProvinceRuntime
from settlement import RecordingSettlementAdapter,SettlementRuntime
from timeline_simulation import TimelineHarness

class DiplomacyTests(unittest.TestCase):
 def setUp(self):
  self.world=json.loads((ROOT/"scenario/world/world.json").read_text())
  self.polities=PolityRuntime(self.world);self.provinces=ProvinceRuntime(self.world,self.polities)
  self.settlements=SettlementRuntime(self.world,RecordingSettlementAdapter())
  self.runtime=DiplomacyRuntime(self.polities,self.provinces,self.settlements)
 def test_war_occupation_and_explicit_peace_keep_ownership_separate(self):
  self.runtime.declare_war("channel_war","england","france")
  self.runtime.record_occupation("channel_war","province","kent","france")
  self.assertEqual(("england","france",True),(self.provinces.require("kent").legal_owner_polity_id,self.provinces.require("kent").controller_polity_id,self.provinces.require("kent").occupied))
  self.runtime.conclude_peace("channel_war",territorial_outcomes=[{"entityKind":"province","entityId":"kent","legalOwnerPolityId":"france","controllerPolityId":"france"}])
  self.assertEqual(("france","france",False),(self.provinces.require("kent").legal_owner_polity_id,self.provinces.require("kent").controller_polity_id,self.provinces.require("kent").occupied))
  self.assertEqual("neutral",self.runtime.relation("england","france"));self.assertEqual(1,len(self.runtime.peace_records));self.assertEqual((),self.runtime.occupations())
  self.assertEqual([1,2,3],[e.sequence for e in self.runtime.events]);self.assertTrue(all(tuple(e.to_dict()["consumers"])==EVENT_CONSUMERS for e in self.runtime.events))
 def test_invalid_and_duplicate_transitions_are_atomic(self):
  before=self.runtime.snapshot();province_before=self.provinces.snapshot()
  with self.assertRaises(DiplomacyError):self.runtime.declare_war("bad","england","missing")
  self.assertEqual(before,self.runtime.snapshot());self.assertEqual(province_before,self.provinces.snapshot())
  self.runtime.declare_war("channel_war","england","france");at_war=self.runtime.snapshot()
  with self.assertRaises(DiplomacyError):self.runtime.declare_war("duplicate_pair","england","france")
  with self.assertRaises(DiplomacyError):self.runtime.record_occupation("channel_war","province","kent","england")
  with self.assertRaises(DiplomacyError):self.runtime.conclude_peace("channel_war",territorial_outcomes=[{"entityKind":"province","entityId":"kent","legalOwnerPolityId":"missing","controllerPolityId":"france"}])
  self.assertEqual(at_war,self.runtime.snapshot());self.assertEqual(province_before,self.provinces.snapshot())
  self.runtime.record_occupation("channel_war","province","kent","france");occupied=self.runtime.snapshot();occupied_province=self.provinces.snapshot()
  with self.assertRaisesRegex(DiplomacyError,"explicitly resolve"):self.runtime.conclude_peace("channel_war")
  self.assertEqual(occupied,self.runtime.snapshot());self.assertEqual(occupied_province,self.provinces.snapshot())
 def test_contradictory_snapshot_rejected_without_mutation(self):
  self.runtime.declare_war("channel_war","england","france");good=self.runtime.snapshot();bad=copy.deepcopy(good);bad["conflicts"][0]["removedParticipants"]=["england"]
  with self.assertRaisesRegex(DiplomacyError,"contradictory"):self.runtime.restore(bad)
  self.assertEqual(good,self.runtime.snapshot())
 def test_save_migration_round_trip_and_checkpoint_resume(self):
  self.runtime.declare_war("channel_war","england","france");self.runtime.record_occupation("channel_war","province","kent","france")
  adapter=DiplomacySaveAdapter(self.runtime,{"calendar":{"day":1}});saved=adapter.capture_world();legacy={"calendar":{"day":1}}
  self.assertNotIn("diplomacyState",legacy);self.assertIn("diplomacyState",adapter.migrate_legacy_world(legacy))
  restored=DiplomacyRuntime(self.polities,self.provinces,self.settlements);restored.restore(saved["diplomacyState"]);self.assertEqual(self.runtime.snapshot(),restored.snapshot())
  initial={"diplomacyState":DiplomacyRuntime(self.polities,self.provinces,self.settlements).snapshot()}
  def configure(h):
   def step(state,ctx):
    r=DiplomacyRuntime(self.polities);r.restore(state["diplomacyState"])
    if ctx.time==1:r.declare_war("channel_war","england","france")
    if ctx.time==3:r.conclude_peace("channel_war")
    state["diplomacyState"]=r.snapshot()
   h.register_step("military","diplomacy_transitions",step)
  full=TimelineHarness(seed=5,start_time=0,state=initial);configure(full);expected=full.run(end_time=4,step_size=1)
  partial=TimelineHarness(seed=5,start_time=0,state=initial);configure(partial);partial.run(end_time=2,step_size=1);resumed=TimelineHarness.from_checkpoint(partial.checkpoint());configure(resumed)
  self.assertEqual(expected["stateHash"],resumed.run(end_time=4,step_size=1)["stateHash"])

if __name__=="__main__":unittest.main()

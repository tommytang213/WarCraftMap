import copy, json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
import campaign_save
from quest_event import QuestEventError,QuestEventRuntime,QuestEventSaveAdapter

def definitions():
 return {"quests":[
  {"id":"voyage","initialStageId":"port","stages":[{"id":"port","objectiveIds":["visit"],"nextStageIds":["sea"]},{"id":"sea","objectiveIds":[],"nextStageIds":[]}],"objectives":[{"id":"visit","conditionId":"flag_set","entityRefs":[]}],"prerequisites":[],"outcomes":[{"id":"reward","kind":"scenario_outcome","outcomeId":"grant_reward","entityRefs":[]}]},
  {"id":"sequel","initialStageId":"start","stages":[{"id":"start","objectiveIds":[],"nextStageIds":[]}],"objectives":[],"prerequisites":[{"kind":"quest_completed","id":"voyage"}],"outcomes":[]}],
 "events":[
  {"id":"one_shot","repeatable":False,"triggers":[{"id":"clock","conditionId":"always","entityRefs":[]}],"prerequisites":[],"outcomes":[]},
  {"id":"payday","repeatable":True,"triggers":[{"id":"clock","conditionId":"always","entityRefs":[]}],"prerequisites":[],"outcomes":[{"id":"pay","kind":"scenario_outcome","outcomeId":"pay","entityRefs":[]}]}],
 "discoveries":[{"id":"island","conditionId":"flag_set","entityRefs":[],"prerequisites":[],"outcomes":[]}]}

class Extensions:
 def evaluate_condition(self,cid,refs,snapshot,context): return cid=="always" or context.get("flag",False)
 def apply_outcomes(self,outcomes,snapshot,context):
  candidate=copy.deepcopy(snapshot); external=candidate["externalState"]
  for outcome in outcomes:
   if context.get("invalid"): raise QuestEventError("invalid referenced operation")
   external["money"]=external.get("money",0)+(10 if outcome["outcomeId"]=="grant_reward" else 1)
   external.setdefault("technologies",[]).append(outcome["outcomeId"])
  return candidate

class QuestEventRuntimeTests(unittest.TestCase):
 def setUp(self): self.runtime=QuestEventRuntime(definitions(),extensions=Extensions(),authoritative_state={"money":0,"technologies":[]})
 def test_lifecycle_objectives_prerequisites_failure_and_cancellation(self):
  with self.assertRaisesRegex(QuestEventError,"prerequisites"): self.runtime.activate_quest("sequel")
  self.runtime.activate_quest("voyage"); self.runtime.evaluate_objectives(context={"flag":True}); self.runtime.advance_quest("voyage","sea"); self.runtime.complete_quest("voyage")
  self.assertEqual(10,self.runtime.snapshot()["externalState"]["money"]); self.runtime.activate_quest("sequel"); self.runtime.cancel_quest("sequel")
  other=QuestEventRuntime(definitions(),extensions=Extensions()); other.activate_quest("voyage"); other.fail_quest("voyage")
  with self.assertRaises(QuestEventError): other.complete_quest("voyage")
 def test_invalid_transitions_inactive_entities_and_atomic_rewards(self):
  before=self.runtime.snapshot()
  with self.assertRaises(QuestEventError): self.runtime.advance_quest("voyage","sea")
  self.assertEqual(before,self.runtime.snapshot()); self.runtime.activate_quest("voyage")
  with self.assertRaisesRegex(QuestEventError,"incomplete"): self.runtime.advance_quest("voyage","sea")
  self.runtime.set_objective_complete("voyage","visit"); self.runtime.advance_quest("voyage","sea"); before=self.runtime.snapshot()
  with self.assertRaisesRegex(QuestEventError,"invalid referenced"): self.runtime.complete_quest("voyage",context={"invalid":True})
  self.assertEqual(before,self.runtime.snapshot())
 def test_simultaneous_order_one_shot_repeatable_and_large_jump(self):
  for eid,key,priority,time in (("payday","p3",2,300),("one_shot","o2",0,100),("payday","p1",0,100),("one_shot","o1",1,100),("payday","p2",0,200)):
   self.runtime.enqueue_trigger(eid,"clock",due_time=time,priority=priority,occurrence_key=key)
  events=self.runtime.process_until(10000); occurred=[(x.entity_id,x.detail.get("occurrenceKey")) for x in events if x.kind=="event_occurred"]
  self.assertEqual([("one_shot","o2"),("payday","p1"),("payday","p2"),("payday","p3")],occurred)
  self.assertEqual(3,self.runtime.snapshot()["events"][1]["occurrences"])
  self.assertTrue(any(x.kind=="event_deduplicated" for x in events))
 def test_discovery_survives_representation_loss_save_load_exactly_once(self):
  self.runtime.discover("island",context={"flag":True}); made=self.runtime.snapshot()
  views=self.runtime.reconstruct_runtime(lambda kind,ident,state:object()); self.assertIn("discovery:island",views)
  self.assertTrue(self.runtime.lose_runtime_representation("discovery","island")); self.assertEqual(made,self.runtime.snapshot())
  adapter=QuestEventSaveAdapter(self.runtime,{"calendar":{"year":1500}}); storage=campaign_save.MemorySaveStorage(); players={"main":{}}
  manager=campaign_save.CampaignSaveManager(build_version="1",scenario_id="test",scenario_version="1",storage=storage,capture_state=lambda:(adapter.capture_world(),players),validate_state=lambda w,p:adapter.validate_world(w),reconstruct_runtime=lambda w,p:adapter.reconstruct(w),activate_state=lambda w,p,r:adapter.activate(w,r),is_save_safe=lambda:True)
  slot=campaign_save.SaveSlot("manual",1); manager.save(slot,"now"); self.runtime.restore(QuestEventRuntime(definitions(),extensions=Extensions()).snapshot()); manager.load(slot)
  self.assertEqual(made,self.runtime.snapshot()); self.runtime.discover("island",context={"flag":True}); self.assertEqual(made,self.runtime.snapshot())
  self.assertNotIn("handle",json.dumps(made).lower())
 def test_checkpoint_resume_and_bounded_failure_are_deterministic(self):
  for n in range(300): self.runtime.enqueue_trigger("payday","clock",due_time=n,occurrence_key=f"r{n}")
  self.runtime.process_until(149); checkpoint=self.runtime.snapshot(); self.runtime.process_until(1000); expected=self.runtime.snapshot()
  resumed=QuestEventRuntime(definitions(),extensions=Extensions()); resumed.restore(checkpoint); resumed.process_until(1000); self.assertEqual(expected,resumed.snapshot())
  bounded=QuestEventRuntime(definitions(),extensions=Extensions(),max_transitions=2)
  for n in range(3): bounded.enqueue_trigger("payday","clock",due_time=n,occurrence_key=f"b{n}")
  before=bounded.snapshot()
  with self.assertRaisesRegex(QuestEventError,"bounded limit 2"): bounded.process_until(9)
  self.assertEqual(before,bounded.snapshot())
 def test_malformed_restore_is_atomic(self):
  before=self.runtime.snapshot(); bad=copy.deepcopy(before); bad["pendingTriggers"]=[{"eventId":"missing","triggerId":"x","key":"x"}]
  with self.assertRaises(QuestEventError): self.runtime.restore(bad)
  self.assertEqual(before,self.runtime.snapshot())

if __name__=="__main__": unittest.main()

import copy, importlib.util, json, sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from local_quest import LocalQuestError, LocalQuestRuntime, LocalQuestSaveAdapter, WORLD_STATE_KEY
SPEC=importlib.util.spec_from_file_location("local_quest_coverage",ROOT/"tooling/local_quest_coverage.py")
COVERAGE=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(COVERAGE)
SOURCE=json.loads((ROOT/"scenario/local-random-quests.json").read_text())
WORLD=json.loads((ROOT/"scenario/world/world.json").read_text())

class LocalQuestTests(unittest.TestCase):
 def setUp(self):
  self.delivered=[]
  self.runtime=LocalQuestRuntime(SOURCE,WORLD["settlements"],campaign_seed="test_seed",reward_adapter=lambda rewards,context:self.delivered.extend(copy.deepcopy(rewards)))
 def test_complete_catalogue_allocation_and_density_gate(self):
  report=COVERAGE.build(); self.assertEqual("pass",report["status"]); self.assertGreaterEqual(report["catalogue"]["families"],15)
  self.assertGreaterEqual(report["catalogue"]["variants"],60); self.assertEqual(len(WORLD["settlements"]),report["allocation"]["settlements"])
  self.assertTrue(all(self.runtime.board(x["id"]) for x in WORLD["settlements"]))
 def test_same_seed_revisit_and_reload_never_reroll(self):
  before=self.runtime.snapshot(); settlement=WORLD["settlements"][0]["id"]
  self.assertEqual(self.runtime.board(settlement),self.runtime.board(settlement))
  replacement=LocalQuestRuntime(SOURCE,WORLD["settlements"],campaign_seed="test_seed")
  LocalQuestSaveAdapter(replacement).restore(LocalQuestSaveAdapter(self.runtime).capture_world({}))
  self.assertEqual(before,replacement.snapshot())
  self.assertEqual(before,LocalQuestRuntime(SOURCE,WORLD["settlements"],campaign_seed="test_seed").snapshot())
  self.assertNotEqual(before,LocalQuestRuntime(SOURCE,WORLD["settlements"],campaign_seed="other_seed").snapshot())
 def test_explicit_terminal_cooldown_is_only_refill_path(self):
  offer=self.runtime.snapshot()["offers"][0]; self.runtime.accept(offer["id"]); self.runtime.resolve(offer["id"],"failed")
  board=self.runtime.board(offer["settlementId"]); self.runtime.advance_day(1); self.assertEqual(board,self.runtime.board(offer["settlementId"]))
  old=next(x for x in self.runtime.snapshot()["offers"] if x["id"]==offer["id"]); self.runtime.advance_day(old["refillDay"])
  self.assertTrue(any(x["slot"]==offer["slot"] and x["cycle"]==1 for x in self.runtime.board(offer["settlementId"])))
  self.runtime.advance_day(old["refillDay"]+1)  # an already-refilled terminal record stays inert
 def test_reward_atomicity_exactly_once_and_anti_farming(self):
  offer=self.runtime.snapshot()["offers"][0]; self.runtime.accept(offer["id"]); self.runtime.resolve(offer["id"],"completed")
  self.assertTrue(self.delivered); checkpoint=self.runtime.snapshot()
  with self.assertRaises(LocalQuestError): self.runtime.resolve(offer["id"],"completed")
  self.assertEqual(checkpoint,self.runtime.snapshot())
 def test_rejected_reward_rolls_back_and_category_stays_distinct(self):
  def reject(rewards,context): raise RuntimeError("adapter rejected atomic batch")
  runtime=LocalQuestRuntime(SOURCE,WORLD["settlements"],campaign_seed="reject",reward_adapter=reject)
  offer=runtime.snapshot()["offers"][0]; runtime.accept(offer["id"]); checkpoint=runtime.snapshot()
  with self.assertRaisesRegex(RuntimeError,"atomic"): runtime.resolve(offer["id"],"completed")
  self.assertEqual(checkpoint,runtime.snapshot()); self.assertTrue(all(x["category"]=="settlement_local_random" for x in runtime.journal_entries()))
 def test_changed_control_blocked_route_and_unavailable_actor_use_authored_policy(self):
  offer=self.runtime.snapshot()["offers"][0]; self.runtime.accept(offer["id"])
  # Context cannot silently complete or mutate an objective; resolution remains explicit.
  self.assertEqual("active",next(x for x in self.runtime.snapshot()["offers"] if x["id"]==offer["id"])["status"])
  family=next(x for x in SOURCE["families"] if x["id"]==offer["familyId"]); variant=next(x for x in family["variants"] if x["id"]==offer["variantId"])
  self.assertTrue(variant["alternate"] and variant["failure"]); self.assertEqual("show_authored_alternate",variant["guidance"]["blockedRoutePolicy"])

if __name__=="__main__": unittest.main()

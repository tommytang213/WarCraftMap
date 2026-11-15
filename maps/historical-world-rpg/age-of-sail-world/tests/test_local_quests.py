import copy, importlib.util, json, sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from local_quest import LocalQuestError, LocalQuestRuntime, LocalQuestSaveAdapter, WORLD_STATE_KEY
SPEC=importlib.util.spec_from_file_location("local_quest_coverage",ROOT/"tooling/local_quest_coverage.py")
COVERAGE=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(COVERAGE)
SOURCE=json.loads((ROOT/"scenario/local-random-quests.json").read_text())
WORLD=json.loads((ROOT/"scenario/world/world.json").read_text())

class DurableRewardLedger:
 def __init__(self):
  # Test double only: the retained object models an external durable ledger.
  self.commits={}
  self.delivery_attempts=0
  self.fail_after_commit=False
 def deliver_once(self,transaction_id,rewards,context):
  self.delivery_attempts+=1
  copied=copy.deepcopy(list(rewards))
  previous=self.commits.get(transaction_id)
  if previous is not None and previous!=copied: raise AssertionError("transaction replay changed rewards")
  if previous is None: self.commits[transaction_id]=copied
  if self.fail_after_commit:
   self.fail_after_commit=False
   raise RuntimeError("ack lost after durable commit")
  return {"transactionId":transaction_id,"committed":True}

class LocalQuestTests(unittest.TestCase):
 def setUp(self):
  self.ledger=DurableRewardLedger()
  self.delivered=self.ledger.commits
  self.verified_completion_ids=set()
  self.runtime=LocalQuestRuntime(SOURCE,WORLD["settlements"],campaign_seed="test_seed",reward_adapter=self.ledger,completion_verifier=lambda claim:claim["instanceId"] in self.verified_completion_ids)
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
  offer=self.runtime.snapshot()["offers"][0]; self.runtime.accept(offer["id"]); self.verified_completion_ids.add(offer["id"]); self.runtime.resolve(offer["id"],"completed")
  self.assertTrue(self.delivered); checkpoint=self.runtime.snapshot()
  with self.assertRaises(LocalQuestError): self.runtime.resolve(offer["id"],"completed")
  self.assertEqual(checkpoint,self.runtime.snapshot())
 def test_lost_commit_ack_and_pending_save_retry_does_not_duplicate_award(self):
  offer=self.runtime.snapshot()["offers"][0]; self.runtime.accept(offer["id"])
  self.verified_completion_ids.add(offer["id"])
  pending=self.runtime.snapshot()
  self.ledger.fail_after_commit=True
  with self.assertRaisesRegex(RuntimeError,"ack lost after durable commit"):
   self.runtime.resolve(offer["id"],"completed")
  self.assertEqual(pending,self.runtime.snapshot())
  self.assertEqual(1,len(self.ledger.commits))
  restored=LocalQuestRuntime(SOURCE,WORLD["settlements"],campaign_seed="test_seed",state=pending,
      reward_adapter=self.ledger,completion_verifier=lambda claim:claim["instanceId"] in self.verified_completion_ids)
  restored.resolve(offer["id"],"completed")
  self.assertEqual(1,len(self.ledger.commits))
  self.assertEqual(2,self.ledger.delivery_attempts)
  self.assertEqual("completed",next(x["status"] for x in restored.snapshot()["offers"] if x["id"]==offer["id"]))
  self.assertEqual(1,len(restored.snapshot()["deliveredRewardKeys"]))
 def test_legacy_callable_and_invalid_receipt_must_fail_closed(self):
  class BogusLedger:
   def deliver_once(self,transaction_id,rewards,context):
    return {"transactionId":"wrong","committed":True}
  for adapter,expected in ((lambda rewards,context:None,"durable idempotent reward adapter"),
                           (BogusLedger(),"matching durable commit receipt")):
   with self.subTest(expected=expected):
    runtime=LocalQuestRuntime(SOURCE,WORLD["settlements"],campaign_seed="receipt_guard",
        reward_adapter=adapter,completion_verifier=lambda claim:True)
    offer=runtime.snapshot()["offers"][0]; runtime.accept(offer["id"])
    checkpoint=runtime.snapshot()
    with self.assertRaisesRegex(LocalQuestError,expected): runtime.resolve(offer["id"],"completed")
    self.assertEqual(checkpoint,runtime.snapshot())

 def test_unverified_completion_cannot_claim_rewards_or_trust_caller_context(self):
  ledger=DurableRewardLedger(); delivered=ledger.commits
  runtime=LocalQuestRuntime(SOURCE,WORLD["settlements"],campaign_seed="proof_guard",
      reward_adapter=ledger)
  offer=runtime.snapshot()["offers"][0]; runtime.accept(offer["id"]); before=runtime.snapshot()
  forged={"objectivesMet":True,"verified":True,"instanceId":offer["id"]}
  with self.assertRaisesRegex(LocalQuestError,"authoritative completion verifier"):
   runtime.resolve(offer["id"],"completed",context=forged)
  self.assertEqual(before,runtime.snapshot()); self.assertEqual({},delivered)
  runtime.completion_verifier=lambda claim:{"verified":True}
  with self.assertRaisesRegex(LocalQuestError,"authoritative objective completion receipts"):
   runtime.resolve(offer["id"],"completed",context=forged)
  self.assertEqual(before,runtime.snapshot()); self.assertEqual({},delivered)
  receipts=set(); seen=[]
  def verify(claim):
   seen.append(copy.deepcopy(claim))
   key=(claim["instanceId"],claim["familyId"],claim["variantId"],claim["acceptedDay"])
   return key in receipts
  runtime.completion_verifier=verify
  with self.assertRaisesRegex(LocalQuestError,"authoritative objective completion receipts"):
   runtime.resolve(offer["id"],"completed",context=forged)
  self.assertEqual(before,runtime.snapshot()); self.assertEqual({},delivered)
  receipts.add((offer["id"],offer["familyId"],offer["variantId"],before["day"]))
  runtime.resolve(offer["id"],"completed")
  self.assertTrue(delivered)
  self.assertEqual("completed",next(o for o in runtime.snapshot()["offers"] if o["id"]==offer["id"])["status"])
  self.assertEqual(offer["id"],seen[-1]["instanceId"])
  self.assertIn("objectives",seen[-1])
  with self.assertRaises(LocalQuestError): runtime.resolve(offer["id"],"completed")
 def test_missing_reward_adapter_cannot_complete_even_after_proof(self):
  runtime=LocalQuestRuntime(SOURCE,WORLD["settlements"],campaign_seed="no_award",
      completion_verifier=lambda claim:True)
  offer=runtime.snapshot()["offers"][0]; runtime.accept(offer["id"]); before=runtime.snapshot()
  with self.assertRaisesRegex(LocalQuestError,"durable idempotent reward adapter"):
   runtime.resolve(offer["id"],"completed")
  self.assertEqual(before,runtime.snapshot())
 def test_pending_save_restores_without_bypassing_proof_guard(self):
  runtime=LocalQuestRuntime(SOURCE,WORLD["settlements"],campaign_seed="persist_proof")
  offer=runtime.snapshot()["offers"][0]; runtime.accept(offer["id"])
  world=LocalQuestSaveAdapter(runtime).capture_world({"otherState":"preserved"})
  restored=LocalQuestRuntime(SOURCE,WORLD["settlements"],campaign_seed="persist_proof")
  LocalQuestSaveAdapter(restored).restore(world)
  self.assertEqual(runtime.snapshot(),restored.snapshot())
  with self.assertRaisesRegex(LocalQuestError,"authoritative completion verifier"):
   restored.resolve(offer["id"],"completed",context={"verified":True})
  self.assertEqual(runtime.snapshot(),restored.snapshot())

 def test_rejected_reward_rolls_back_and_category_stays_distinct(self):
  class RejectingLedger:
   def deliver_once(self,transaction_id,rewards,context): raise RuntimeError("adapter rejected atomic batch")
  verified_ids=set()
  runtime=LocalQuestRuntime(SOURCE,WORLD["settlements"],campaign_seed="reject",reward_adapter=RejectingLedger(),completion_verifier=lambda claim:claim["instanceId"] in verified_ids)
  offer=runtime.snapshot()["offers"][0]; runtime.accept(offer["id"]); verified_ids.add(offer["id"]); checkpoint=runtime.snapshot()
  with self.assertRaisesRegex(RuntimeError,"atomic"): runtime.resolve(offer["id"],"completed")
  self.assertEqual(checkpoint,runtime.snapshot()); self.assertTrue(all(x["category"]=="settlement_local_random" for x in runtime.journal_entries()))
 def test_changed_control_blocked_route_and_unavailable_actor_use_authored_policy(self):
  offer=self.runtime.snapshot()["offers"][0]; self.runtime.accept(offer["id"])
  # Context cannot silently complete or mutate an objective; resolution remains explicit.
  self.assertEqual("active",next(x for x in self.runtime.snapshot()["offers"] if x["id"]==offer["id"])["status"])
  family=next(x for x in SOURCE["families"] if x["id"]==offer["familyId"]); variant=next(x for x in family["variants"] if x["id"]==offer["variantId"])
  self.assertTrue(variant["alternate"] and variant["failure"]); self.assertEqual("show_authored_alternate",variant["guidance"]["blockedRoutePolicy"])

if __name__=="__main__": unittest.main()

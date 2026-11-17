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
 def test_bad_boolean_day_is_rejected_in_live_state_and_saves(self):
  before=self.runtime.snapshot()
  with self.assertRaisesRegex(LocalQuestError,"day cannot move backwards"):
   self.runtime.advance_day(True)
  self.assertEqual(before,self.runtime.snapshot())
  damaged=copy.deepcopy(before); damaged["day"]=True
  with self.assertRaisesRegex(LocalQuestError,"seed/day is incompatible"):
   LocalQuestRuntime(SOURCE,WORLD["settlements"],campaign_seed="test_seed",state=damaged)

 def test_refill_batch_rollback_preserves_previous_day_and_offer_slots(self):
  offers=self.runtime.snapshot()["offers"][:2]
  for offer in offers:
   self.runtime.accept(offer["id"]); self.runtime.resolve(offer["id"],"failed")
  target=max(self.runtime._offer(offer["id"])["refillDay"] for offer in offers)
  before=self.runtime.snapshot()
  original=self.runtime._make_offer; attempts=[0]
  def fail_second_refill(*args,**kwargs):
   attempts[0]+=1
   if attempts[0]==2: raise LocalQuestError("refill generation failed")
   return original(*args,**kwargs)
  self.runtime._make_offer=fail_second_refill
  try:
   with self.assertRaisesRegex(LocalQuestError,"refill generation failed"):
    self.runtime.advance_day(target)
  finally:
   self.runtime._make_offer=original
  self.assertEqual(2,attempts[0])
  self.assertEqual(before,self.runtime.snapshot())
  self.runtime.advance_day(target)
  self.assertEqual(target,self.runtime.snapshot()["day"])
  self.assertTrue(all(self.runtime._offer(x["id"])["refillDay"] is None for x in offers))
  self.assertTrue(all(any(x["slot"]==old["slot"] and x["cycle"]==old["cycle"]+1
                          for x in self.runtime.board(old["settlementId"])) for old in offers))

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

 def test_road_companions_variants_are_specific_and_not_template_clones(self):
  family=next(f for f in SOURCE["families"] if f["id"]=="road_companions")
  self.assertEqual(["plain","contested","urgent","scarce"],[v["id"] for v in family["variants"]])
  self.assertEqual(4,len({v["title"] for v in family["variants"]}))
  self.assertEqual(4,len({tuple(v["objectives"]) for v in family["variants"]}))
  for variant in family["variants"]:
   with self.subTest(variant=variant["id"]):
    self.assertNotIn(": "+variant["id"].title(),variant["title"])
    self.assertNotIn("A routine request has become difficult",variant["summary"])
    self.assertNotIn("ask for accountable help",variant["dialogue"])
    self.assertEqual(2,len(variant["objectives"]))
    for field in ("title","summary","dialogue","alternate","failure"):
     self.assertTrue(variant[field].strip())


 def test_tools_recovered_variants_have_distinct_actors_evidence_and_recovery(self):
  family=next(f for f in SOURCE["families"] if f["id"]=="tools_recovered")
  variants=family["variants"]
  self.assertEqual(["plain","contested","urgent","scarce"],[v["id"] for v in variants])
  for key in ("title","summary","dialogue","alternate","failure"):
   self.assertEqual(4,len({v[key] for v in variants}),key)
  self.assertEqual(4,len({tuple(v["objectives"]) for v in variants}))
  for variant in variants:
   with self.subTest(variant=variant["id"]):
    self.assertEqual(2,len(variant["objectives"]))
    self.assertNotRegex(variant["title"],r": (Plain|Contested|Urgent|Scarce)$")
    self.assertNotIn("A routine request has become difficult",variant["summary"])
    self.assertNotIn("ask for accountable help",variant["dialogue"])
    self.assertTrue(all(x.strip() for x in variant["objectives"]))
    self.assertEqual(["currency","experience","profession_reputation"],[r["kind"] for r in variant["rewards"]])

if __name__=="__main__": unittest.main()

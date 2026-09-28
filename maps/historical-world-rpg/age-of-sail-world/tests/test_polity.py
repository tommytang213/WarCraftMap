import copy, json, sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
import campaign_save
from polity import PolityError, PolityRuntime, PolitySaveAdapter

WORLD_PATH=ROOT/"scenario"/"world"/"world.json"

class PolityRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.source=json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        self.original=copy.deepcopy(self.source)
        self.runtime=PolityRuntime(self.source)
    def test_deterministic_initialization_lookup_and_order(self):
        self.assertEqual(63,len(self.runtime.ids())); self.assertIn("england",self.runtime.ids()); self.assertIn("france",self.runtime.ids())
        england=self.runtime.require("england")
        self.assertEqual(("greater_london","kent","english_midlands","northern_england"),england.definition.province_ids)
        self.assertEqual(("Kingdom of England","king","london"),(england.definition.name,england.definition.sovereign_tier,england.definition.capital_settlement_id))
        self.assertIsNone(self.runtime.lookup("missing"))
    def test_activation_snapshots_and_definition_immutability(self):
        self.assertTrue(self.runtime.set_active("france",False))
        self.assertFalse(self.runtime.set_active("france",False))
        self.assertNotIn("france",self.runtime.ids(active_only=True)); self.assertEqual(62,len(self.runtime.ids(active_only=True)))
        snapshot=self.runtime.snapshot()
        self.assertNotIn("handle",json.dumps(snapshot).lower())
        self.assertEqual(63,len(snapshot["polities"])); self.assertFalse(next(x for x in snapshot["polities"] if x["id"]=="france")["active"])
        snapshot["polities"][0]["active"]=False
        self.assertTrue(self.runtime.require("england").active)
        self.assertEqual(self.original,self.source)
    def test_restore_is_atomic_and_rebuilds_derived_lookup(self):
        good=self.runtime.snapshot(); good["polities"].reverse(); next(x for x in good["polities"] if x["id"]=="france")["active"]=False
        self.runtime.restore(good)
        self.assertFalse(self.runtime.require("france").active)
        baseline=self.runtime.snapshot()
        for bad,pattern in [
            ({"schemaVersion":1,"polities":[{"id":"england","active":True},{"id":"england","active":False}]},"duplicate"),
            ({"schemaVersion":1,"polities":[{"id":"england","active":True}]},"missing polity"),
            ({"schemaVersion":1,"polities":[{"id":"spain","active":True}]},"incompatible"),
        ]:
            with self.assertRaisesRegex(PolityError,pattern): self.runtime.restore(bad)
            self.assertEqual(baseline,self.runtime.snapshot())
    def test_invalid_definitions_are_rejected(self):
        cases=[]
        duplicate=copy.deepcopy(self.source); duplicate["polities"].append(copy.deepcopy(duplicate["polities"][0])); cases.append((duplicate,"duplicate ID"))
        capital=copy.deepcopy(self.source); capital["polities"][0]["capitalSettlementId"]="missing"; cases.append((capital,"missing capital"))
        tier=copy.deepcopy(self.source); tier["polities"][0]["sovereignTier"]="president"; cases.append((tier,"invalid sovereign"))
        owner=copy.deepcopy(self.source); owner["provinces"][0]["legalOwnerPolityId"]="france"; cases.append((owner,"incompatible legal owner"))
        for candidate,pattern in cases:
            with self.subTest(pattern=pattern),self.assertRaisesRegex(PolityError,pattern): PolityRuntime(candidate)
    def test_campaign_save_round_trip_uses_stable_state_only(self):
        adapter=PolitySaveAdapter(self.runtime,{"calendar":{"day":1}})
        storage=campaign_save.MemorySaveStorage()
        players={"main":{"characterId":"captain"}}
        def activate(world,loaded_players,reconstructed):
            adapter.activate(world,reconstructed)
        manager=campaign_save.CampaignSaveManager(build_version="1",scenario_id="test",scenario_version="1",storage=storage,capture_state=lambda:(adapter.capture_world(),players),validate_state=lambda world,loaded:adapter.validate_world(world),reconstruct_runtime=lambda world,loaded:adapter.reconstruct(world),activate_state=activate,is_save_safe=lambda:True)
        self.runtime.set_active("france",False); slot=campaign_save.SaveSlot("manual",1); manager.save(slot,"now")
        payload=storage.read(slot.stable_id)
        self.assertNotIn(b"handle",payload.lower()); self.assertNotIn(b"Kingdom of France",payload)
        self.runtime.set_active("france",True); manager.load(slot)
        self.assertFalse(self.runtime.require("france").active)
    def test_pre_polity_world_state_has_explicit_compatible_migration(self):
        adapter=PolitySaveAdapter(self.runtime,{})
        legacy={"calendar":{"day":3}}
        migrated=adapter.migrate_legacy_world(legacy)
        self.assertNotIn("polityState",legacy)
        self.assertEqual(self.runtime.snapshot(),migrated["polityState"])
        with self.assertRaisesRegex(PolityError,"missing polityState"): adapter.validate_world(legacy)
    def test_long_timeline_harness_carries_registered_polity_snapshot(self):
        from timeline_simulation import TimelineHarness
        state={"polityState":self.runtime.snapshot()}
        harness=TimelineHarness(seed=1,start_time=0,state=state)
        harness.register_invariant("polity_state_valid",lambda state,ctx:(self.runtime.validate_snapshot(state["polityState"]) and None))
        result=harness.run(end_time=1000,step_size=1)
        self.assertEqual(state,result["state"])

if __name__=="__main__": unittest.main()

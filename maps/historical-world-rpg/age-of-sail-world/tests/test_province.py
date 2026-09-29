import copy, json, sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
import campaign_save
from polity import PolityRuntime
from province import ProvinceError, ProvinceRuntime, ProvinceSaveAdapter

WORLD_PATH=ROOT/"scenario"/"world"/"world.json"

class ProvinceRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.source=json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        self.polities=PolityRuntime(self.source); self.runtime=ProvinceRuntime(self.source,self.polities)

    def test_initialization_keeps_governance_dimensions_distinct(self):
        self.assertEqual(98,len(self.runtime.ids())); self.assertIn("kent",self.runtime.ids()); self.assertIn("normandy",self.runtime.ids())
        kent=self.runtime.require("kent")
        self.assertEqual(("Kent","county",("dover","calais")),(kent.definition.name,kent.definition.administrative_type,kent.definition.settlement_ids))
        self.assertEqual(("england","england","england","england",35,False),(kent.legal_owner_polity_id,kent.controller_polity_id,kent.governing_polity_id,kent.sovereign_polity_id,kent.autonomy_percent,kent.occupied))

    def test_occupation_control_and_legal_transfer_are_atomic_and_ordered(self):
        occupied=self.runtime.transition("kent",controller_polity_id="france",reason="military_occupation")
        state=self.runtime.require("kent")
        self.assertEqual((1,"england","france",True),(occupied.sequence,state.legal_owner_polity_id,state.controller_polity_id,state.occupied))
        transferred=self.runtime.transition("kent",legal_owner_polity_id="france",controller_polity_id="england",reason="peace_treaty")
        self.assertEqual(["legalOwnerPolityId","controllerPolityId"],[item[0] for item in transferred.changes])
        self.assertEqual(("france","england",True),(self.runtime.require("kent").legal_owner_polity_id,self.runtime.require("kent").controller_polity_id,self.runtime.require("kent").occupied))
        self.assertEqual([1,2],[event.sequence for event in self.runtime.events])

    def test_invalid_references_inactive_participants_and_noop_roll_back(self):
        baseline=self.runtime.snapshot()
        for kwargs,pattern in [({"controller_polity_id":"spain"},"unknown polity"),({"legal_owner_polity_id":"spain","controller_polity_id":"france"},"unknown polity"),({"controller_polity_id":"england"},"must change")]:
            with self.subTest(kwargs=kwargs),self.assertRaisesRegex(ProvinceError,pattern): self.runtime.transition("kent",reason="test_transition",**kwargs)
            self.assertEqual(baseline,self.runtime.snapshot())
        with self.assertRaisesRegex(ProvinceError,"unknown province"): self.runtime.transition("missing",controller_polity_id="france")
        self.polities.set_active("france",False)
        with self.assertRaisesRegex(ProvinceError,"inactive polity"): self.runtime.transition("kent",controller_polity_id="france")
        self.assertEqual(baseline,self.runtime.snapshot())

    def test_derived_indexes_reconstruct_after_transfers_and_are_not_persisted(self):
        self.runtime.transition("kent",controller_polity_id="france",legal_owner_polity_id="france",reason="annexation")
        self.assertEqual(("ile_de_france","kent","loire_france","normandy"),self.runtime.provinces_for("france","controller"))
        snapshot=self.runtime.snapshot(); self.assertNotIn("indexes",snapshot)
        restored=ProvinceRuntime(self.source,self.polities); restored.restore(snapshot)
        self.assertEqual(self.runtime.indexes_snapshot(),restored.indexes_snapshot())
        bad=copy.deepcopy(snapshot); bad["provinces"][0]["legalOwnerPolityId"]="missing"; baseline=restored.snapshot()
        with self.assertRaisesRegex(ProvinceError,"missing polity"): restored.restore(bad)
        self.assertEqual(baseline,restored.snapshot())

    def test_snapshot_and_campaign_save_round_trip_have_no_transient_references(self):
        adapter=ProvinceSaveAdapter(self.runtime,{"calendar":{"day":1}}); storage=campaign_save.MemorySaveStorage(); players={"main":{"characterId":"captain"}}
        manager=campaign_save.CampaignSaveManager(build_version="1",scenario_id="test",scenario_version="1",storage=storage,capture_state=lambda:(adapter.capture_world(),players),validate_state=lambda world,loaded:adapter.validate_world(world),reconstruct_runtime=lambda world,loaded:adapter.reconstruct(world),activate_state=lambda world,loaded,reconstructed:adapter.activate(world,reconstructed),is_save_safe=lambda:True)
        self.runtime.transition("kent",controller_polity_id="france",reason="military_occupation")
        slot=campaign_save.SaveSlot("manual",1); manager.save(slot,"now"); payload=storage.read(slot.stable_id)
        self.assertNotIn(b"handle",payload.lower()); self.assertNotIn(b"widget",payload.lower())
        self.runtime.transition("kent",legal_owner_polity_id="france",reason="annexation"); manager.load(slot)
        self.assertEqual(("england","france",True),(self.runtime.require("kent").legal_owner_polity_id,self.runtime.require("kent").controller_polity_id,self.runtime.require("kent").occupied))

    def test_legacy_world_migration_is_explicit_and_non_mutating(self):
        adapter=ProvinceSaveAdapter(self.runtime,{}); legacy={"calendar":{"day":3}}; migrated=adapter.migrate_legacy_world(legacy)
        self.assertNotIn("provinceState",legacy); self.assertEqual(self.runtime.snapshot(),migrated["provinceState"])
        with self.assertRaisesRegex(ProvinceError,"missing provinceState"): adapter.validate_world(legacy)

    def test_deterministic_timeline_transitions_survive_checkpoint_resume(self):
        from timeline_simulation import TimelineHarness
        def configure(harness):
            def step(state,ctx):
                runtime=ProvinceRuntime(self.source,self.polities); runtime.restore(state["provinceState"])
                if ctx.time==2: runtime.transition("kent",controller_polity_id="france",reason="military_occupation")
                if ctx.time==4: runtime.transition("kent",legal_owner_polity_id="france",reason="peace_treaty")
                state["provinceState"]=runtime.snapshot()
            harness.register_step("government","province_transitions",step)
        initial={"provinceState":self.runtime.snapshot()}; full=TimelineHarness(seed=9,start_time=0,state=initial); configure(full); expected=full.run(end_time=4,step_size=1)
        partial=TimelineHarness(seed=9,start_time=0,state=initial); configure(partial); partial.run(end_time=2,step_size=1)
        resumed=TimelineHarness.from_checkpoint(partial.checkpoint()); configure(resumed); actual=resumed.run(end_time=4,step_size=1)
        self.assertEqual(expected["stateHash"],actual["stateHash"]); self.assertEqual([1,2],[event["sequence"] for event in actual["state"]["provinceState"]["transitionEvents"]])

if __name__=="__main__": unittest.main()

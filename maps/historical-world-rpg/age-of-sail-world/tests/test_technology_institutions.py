import copy, json, sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
import campaign_save
from technology_institutions import (
    MAX_PERCENT_UNITS, ResearchError, TechnologyInstitutionRuntime,
    TechnologyInstitutionSaveAdapter, UNITS_PER_POINT,
)
from timeline_simulation import TimelineHarness

WORLD=json.loads((ROOT/"scenario"/"world"/"world.json").read_text(encoding="utf-8"))

class TechnologyInstitutionTests(unittest.TestCase):
    def runtime(self,world=None,date="1450-01-01"):
        return TechnologyInstitutionRuntime(world or WORLD,date)

    def test_prerequisites_cross_tree_completion_and_unlock_order(self):
        world=copy.deepcopy(WORLD)
        node=next(x for x in world["technologies"] if x["id"]=="standardized_charts")
        node["unlocks"]=[{"kind":"policy","contentId":"z_policy"},{"kind":"ability","contentId":"a_ability"}]
        france=next(x for x in world["polityResearchStates"] if x["polityId"]=="france")
        france["completedTechnologyIds"].append("oceanic_seamanship")
        france["establishedInstitutionIds"].append("movable_type_printing")
        france["researchProgress"]=[{"nodeId":"celestial_navigation","progress":65}]
        runtime=self.runtime(world,"1600-01-01")
        baseline=runtime.snapshot()
        with self.assertRaisesRegex(ResearchError,"unavailable prerequisites"):
            runtime.advance_research("france","standardized_charts",1000,"1600-01-01")
        self.assertEqual(baseline,runtime.snapshot())
        events=runtime.advance_research("france","celestial_navigation",39,"1600-01-01")
        self.assertEqual(["technology_completed","content_unlocked"],[x.kind for x in events])
        self.assertEqual("progression_celestial_navigation",events[1].content_id)
        events=runtime.advance_research("france","standardized_charts",165,"1600-01-01")
        self.assertEqual(
            [("technology_completed",None),("content_unlocked","ability"),("content_unlocked","policy")],
            [(x.kind,x.unlock_kind) for x in events],
        )
        self.assertIn("standardized_charts",runtime.completed("france"))
        snapshot=runtime.snapshot()
        with self.assertRaisesRegex(ResearchError,"already complete"):
            runtime.advance_research("france","standardized_charts",1,"1600-01-01")
        self.assertEqual(snapshot,runtime.snapshot())

    def test_ahead_of_time_cost_is_finite_and_preferred_date_removes_penalty(self):
        runtime=self.runtime()
        early=runtime.cost_units("standardized_charts","1450-01-01")
        preferred=runtime.cost_units("standardized_charts","1550-01-01")
        late=runtime.cost_units("standardized_charts","1700-01-01")
        self.assertEqual(165*UNITS_PER_POINT,preferred)
        self.assertEqual(preferred,late)
        self.assertEqual(165*16*UNITS_PER_POINT,early)
        self.assertGreater(early,preferred)

    def test_independent_uneven_diffusion_and_equivalent_run_determinism(self):
        def run():
            runtime=self.runtime()
            for _ in range(1200):
                runtime.advance_adoption("kent","celestial_navigation","0.01")
                runtime.advance_adoption("normandy","celestial_navigation","0.02")
            return runtime
        one,two=run(),run()
        self.assertEqual(one.snapshot(),two.snapshot())
        self.assertEqual(12*UNITS_PER_POINT,one.adoption_units("kent","celestial_navigation"))
        self.assertEqual(24*UNITS_PER_POINT,one.adoption_units("normandy","celestial_navigation"))
        self.assertNotEqual(one.adoption_units("kent","celestial_navigation"),one.adoption_units("normandy","celestial_navigation"))

    def test_invalid_inputs_and_malformed_restore_are_atomic(self):
        runtime=self.runtime(); baseline=runtime.snapshot()
        calls=[
            lambda:runtime.advance_research("england","missing",1,"1500-01-01"),
            lambda:runtime.advance_research("missing","celestial_navigation",1,"1500-01-01"),
            lambda:runtime.advance_research("england","standardized_charts",float("nan"),"1500-01-01"),
            lambda:runtime.advance_adoption("missing","celestial_navigation",1),
            lambda:runtime.advance_adoption("kent","missing",1),
        ]
        for call in calls:
            with self.assertRaises(ResearchError): call()
            self.assertEqual(baseline,runtime.snapshot())
        malformed=copy.deepcopy(baseline); malformed["polities"][0]["progress"].append({"nodeId":"celestial_navigation","workUnits":-1})
        with self.assertRaisesRegex(ResearchError,"malformed progress"): runtime.restore(malformed)
        self.assertEqual(baseline,runtime.snapshot())

    def test_save_load_legacy_migration_and_checkpoint_resume(self):
        runtime=self.runtime(date="1450-01-01"); adapter=TechnologyInstitutionSaveAdapter(runtime,{"calendar":{"date":"1450-01-01"}})
        storage=campaign_save.MemorySaveStorage(); players={"main":{"characterId":"captain"}}
        manager=campaign_save.CampaignSaveManager(
            build_version="1",scenario_id="test",scenario_version="1",storage=storage,
            capture_state=lambda:(adapter.capture_world(),players),
            validate_state=lambda world,loaded:adapter.validate_world(world),
            reconstruct_runtime=lambda world,loaded:adapter.reconstruct(world),
            activate_state=lambda world,loaded,reconstructed:adapter.activate(world,reconstructed),
            is_save_safe=lambda:True,
        )
        runtime.advance_adoption("kent","celestial_navigation",1)
        slot=campaign_save.SaveSlot("manual",1); expected=runtime.snapshot(); manager.save(slot,"now")
        runtime.advance_adoption("kent","celestial_navigation",1); manager.load(slot)
        self.assertEqual(expected,runtime.snapshot())
        legacy={"calendar":{"date":"1450-01-01"}}; migrated=adapter.migrate_legacy_world(legacy)
        self.assertNotIn("technologyInstitutionState",legacy); adapter.validate_world(migrated)

        def configure(harness):
            def step(state,ctx):
                current=self.runtime(); current.restore(state["research"])
                current.advance_adoption("kent","celestial_navigation","0.001")
                state["research"]=current.snapshot()
            harness.register_step("technology_institutions","diffusion",step)
        initial={"research":self.runtime().snapshot()}
        full=TimelineHarness(seed=7,start_time=1450,state=initial); configure(full)
        expected=full.run(end_time=1820,step_size=1)
        partial=TimelineHarness(seed=7,start_time=1450,state=initial); configure(partial); partial.run(end_time=1600,step_size=1)
        resumed=TimelineHarness.from_checkpoint(partial.checkpoint()); configure(resumed)
        actual=resumed.run(end_time=1820,step_size=1)
        self.assertEqual(expected["stateHash"],actual["stateHash"])

    def test_adoption_clamps_and_rejects_duplicate_completion(self):
        runtime=self.runtime()
        runtime.advance_adoption("kent","celestial_navigation",100)
        self.assertEqual(MAX_PERCENT_UNITS,runtime.adoption_units("kent","celestial_navigation"))
        before=runtime.snapshot()
        with self.assertRaisesRegex(ResearchError,"already fully adopted"):
            runtime.advance_adoption("kent","celestial_navigation",1)
        self.assertEqual(before,runtime.snapshot())

    def test_all_authored_unlocks_are_delivered_with_provenance(self):
        runtime=self.runtime(date="1820-01-01")
        delivered=[]
        for node_id,node in runtime.nodes.items():
            runtime.research['france']={'completed':set(runtime.nodes)-{node_id},'progress':{}}
            events=runtime.advance_research('france',node_id,1000000,'1820-01-01')
            actual=[(e.node_id,e.unlock_kind,e.content_id) for e in events[1:]]
            expected=sorted((node_id,u['kind'],u['contentId']) for u in node['unlocks'])
            self.assertEqual(expected,actual)
            delivered.extend(actual)
        self.assertEqual(220,len(delivered))

    def test_derived_entitlements_preserve_shared_content_controllers_and_history(self):
        runtime=self.runtime()
        runtime.research['france']['completed']={'mass_army_logistics','dockyard_logistics','naval_administration'}
        before=runtime.snapshot(); expected=runtime.entitlements('france')
        self.assertEqual(7,len(expected))
        self.assertEqual(2,sum(e['kind']=='building' and e['contentId']=='dry_dock' for e in expected))
        self.assertEqual(['mass_conscription','common_wagon_train','supply_efficiency'],
                         [e['contentId'] for e in expected if e['nodeId']=='mass_army_logistics'])
        self.assertTrue(all(e['bindingStatus']=='unbound' and e['controllerId']=='france' for e in expected))
        other=runtime.entitlements('england')
        for _ in range(3):
            runtime.restore(before)
            self.assertEqual(expected,runtime.entitlements('france'))
            self.assertEqual(other,runtime.entitlements('england'))
            self.assertEqual(before,runtime.snapshot())
        self.assertEqual((),runtime.events)

    def test_mutated_unlock_definition_rejects_before_progress_or_completion_changes(self):
        for unlocks in ([{'kind':'food','contentId':'bonus'}], [{'kind':'unit'}],
                        [{'kind':'unit','contentId':'bad,id'}],
                        [{'kind':'unit','contentId':'same'}]*2):
            runtime=self.runtime()
            runtime.research['france']={'completed':set(),'progress':{}}
            runtime.nodes['pike_and_shot']['unlocks']=unlocks
            before=runtime.snapshot()
            for points in (1,1000000):
                with self.assertRaises(ResearchError):
                    runtime.advance_research('france','pike_and_shot',points,'1820-01-01')
                self.assertEqual(before,runtime.snapshot())

if __name__=="__main__": unittest.main()

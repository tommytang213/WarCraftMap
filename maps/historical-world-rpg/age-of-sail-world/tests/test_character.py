import copy, json, sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
import campaign_save
from character import CharacterError, CharacterRuntime, CharacterSaveAdapter
from timeline_simulation import TimelineHarness

def fixture():
    def display(ident): return {"id":ident,"name":ident.replace("_"," ").title(),"description":"Scenario-authored."}
    return {
        "polities":[{"id":"england"},{"id":"france"}],
        "titleGrants":[{"id":"naval_commission"}],
        "traits":[display("steadfast"),display("navigator")],
        "skills":[display("navigation"),display("command")],
        "professions":[display("officer"),display("diplomat")],
        "personalQuests":[{"id":"lost_chart","title":"Lost Chart","summary":"Recover it.","characterId":"alice"}],
        "characters":[
            {"id":"alice","displayName":"Alice","biography":"A test companion.","traitIds":["steadfast"],"skills":[{"skillId":"navigation","rating":40}],"professionIds":["officer"],"personalQuestIds":["lost_chart"],"loyalty":{"score":20,"permanentState":"none"},"allegiancePolityId":"england","available":True,"recruited":False,"active":True,"runtimeTemplateId":"companion_hero","recruitmentCosts":[{"resourceId":"money","amount":50}],"rewardIds":["chart_reward"],"titleGrantIds":["naval_commission"]},
            {"id":"bob","displayName":"Bob","biography":"Another test companion.","traitIds":[],"skills":[{"skillId":"command","rating":30}],"professionIds":[],"personalQuestIds":[],"loyalty":{"score":0,"permanentState":"none"},"allegiancePolityId":"france","available":True,"recruited":False,"active":True,"runtimeTemplateId":"companion_hero"}],
        "relationshipThresholds":[
            {"id":"trusted","scope":"loyalty","minimum":50,"maximum":100,"consequences":[{"kind":"buff","contentId":"trusted_command"},{"kind":"content_availability","contentId":"private_confidence"}]},
            {"id":"works_well","scope":"companion_relationship","minimum":40,"maximum":100,"consequences":[{"kind":"synergy","contentId":"coordinated_actions"}]},
            {"id":"hostile","scope":"companion_relationship","minimum":-100,"maximum":-40,"consequences":[{"kind":"friction","contentId":"open_quarrel"},{"kind":"debuff","contentId":"poor_coordination"}]}],
        "companionRelationships":[{"id":"alice_bob","characterAId":"alice","characterBId":"bob","score":0}]}

class CharacterRuntimeTests(unittest.TestCase):
    def setUp(self): self.source=fixture(); self.original=copy.deepcopy(self.source); self.runtime=CharacterRuntime(self.source)

    def test_initialization_definitions_and_integrated_references(self):
        self.assertEqual(("alice","bob"),self.runtime.ids())
        alice=self.runtime.require("alice")
        self.assertEqual((("money",50),),alice.definition.recruitment_costs)
        self.assertEqual(("chart_reward",),alice.definition.reward_ids)
        self.assertEqual(("naval_commission",),alice.definition.title_grant_ids)
        self.assertEqual(("lost_chart",),alice.definition.personal_quest_ids)
        self.assertEqual(self.original,self.source)
        with self.assertRaises(TypeError): alice.skills["navigation"]=99

    def test_recruit_dismiss_allegiance_availability_traits_skills_professions(self):
        self.runtime.recruit("alice"); self.assertTrue(self.runtime.require("alice").recruited)
        self.runtime.dismiss("alice"); self.runtime.set_available("alice",False)
        self.assertFalse(self.runtime.require("alice").available)
        self.runtime.set_available("alice",True); self.runtime.set_allegiance("alice","france")
        self.runtime.add_trait("alice","navigator"); self.runtime.set_skill("alice","command",55)
        self.runtime.add_profession("alice","diplomat")
        view=self.runtime.require("alice")
        self.assertEqual(("navigator","steadfast"),view.trait_ids)
        self.assertEqual(55,view.skills["command"]); self.assertIn("diplomat",view.profession_ids)

    def test_threshold_events_are_typed_deterministic_and_independent(self):
        loyalty=self.runtime.change_loyalty("alice",30)
        self.assertEqual([("buff","trusted_command",True),("content_availability","private_confidence",True)],[(x.event_type,x.content_id,x.active) for x in loyalty])
        synergy=self.runtime.change_relationship("bob","alice",40)
        self.assertEqual([("synergy","coordinated_actions",True)],[(x.event_type,x.content_id,x.active) for x in synergy])
        self.assertEqual(50,self.runtime.require("alice").loyalty)
        self.assertEqual(40,self.runtime.relationship_score("alice","bob"))
        exit_events=self.runtime.set_relationship("alice","bob",-40)
        self.assertEqual([("friction",True),("debuff",True),("synergy",False)],[(x.event_type,x.active) for x in exit_events])

    def test_oathbound_is_atomic_and_permanent(self):
        self.runtime.recruit("alice"); self.runtime.enter_oathbound("alice"); baseline=self.runtime.snapshot()
        operations=[lambda:self.runtime.dismiss("alice"),lambda:self.runtime.change_loyalty("alice",-1),lambda:self.runtime.set_allegiance("alice","france"),lambda:self.runtime.set_available("alice",False),lambda:self.runtime.set_active("alice",False),lambda:self.runtime.remove_trait("alice","steadfast"),lambda:self.runtime.enter_oathbound("alice")]
        for operation in operations:
            with self.assertRaises(CharacterError): operation()
            self.assertEqual(baseline,self.runtime.snapshot())

    def test_invalid_ranges_missing_refs_inactive_and_snapshot_rollback(self):
        baseline=self.runtime.snapshot()
        for operation in [lambda:self.runtime.change_loyalty("alice",1000),lambda:self.runtime.set_skill("alice","missing",1),lambda:self.runtime.add_trait("alice","missing"),lambda:self.runtime.change_relationship("alice","bob",101)]:
            with self.assertRaises(CharacterError): operation()
            self.assertEqual(baseline,self.runtime.snapshot())
        self.runtime.set_active("bob",False)
        with self.assertRaisesRegex(CharacterError,"active"): self.runtime.change_relationship("alice","bob",1)
        bad=self.runtime.snapshot(); bad["characters"][0]["loyalty"]=200; saved=self.runtime.snapshot()
        with self.assertRaises(CharacterError): self.runtime.restore(bad)
        self.assertEqual(saved,self.runtime.snapshot())

    def test_malformed_definitions_are_rejected(self):
        cases=[]
        duplicate=fixture(); duplicate["characters"].append(copy.deepcopy(duplicate["characters"][0])); cases.append((duplicate,"duplicate"))
        missing=fixture(); missing["characters"][0]["traitIds"]=["missing"]; cases.append((missing,"missing reference"))
        malformed=fixture(); malformed["relationshipThresholds"][0]["minimum"]=80; malformed["relationshipThresholds"][0]["maximum"]=50; cases.append((malformed,"minimum cannot exceed"))
        duplicate_pair=fixture(); duplicate_pair["companionRelationships"].append({"id":"reverse","characterAId":"bob","characterBId":"alice","score":0}); cases.append((duplicate_pair,"duplicate companion pair"))
        for value,pattern in cases:
            with self.subTest(pattern=pattern),self.assertRaisesRegex(CharacterError,pattern): CharacterRuntime(value)

    def test_runtime_representation_recreates_without_authoritative_changes(self):
        self.runtime.recruit("alice"); state=self.runtime.snapshot(); made=[]
        factory=lambda definition,view: made.append({"template":definition.runtime_template_id,"id":view.id}) or object()
        first=self.runtime.reconstruct_runtime(factory); self.assertEqual(("alice",),tuple(first))
        self.assertTrue(self.runtime.lose_runtime_representation("alice")); second=self.runtime.reconstruct_runtime(factory)
        self.assertIsNot(first["alice"],second["alice"]); self.assertEqual(state,self.runtime.snapshot())
        self.assertNotIn("handle",json.dumps(state).lower())

    def test_save_load_and_legacy_migration(self):
        adapter=CharacterSaveAdapter(self.runtime,{"calendar":{"day":1}}); storage=campaign_save.MemorySaveStorage(); players={"main":{"characterId":"player"}}
        manager=campaign_save.CampaignSaveManager(build_version="1",scenario_id="test",scenario_version="1",storage=storage,capture_state=lambda:(adapter.capture_world(),players),validate_state=lambda world,loaded:adapter.validate_world(world),reconstruct_runtime=lambda world,loaded:adapter.reconstruct(world),activate_state=lambda world,loaded,reconstructed:adapter.activate(world,reconstructed),is_save_safe=lambda:True)
        self.runtime.recruit("alice"); self.runtime.change_loyalty("alice",10); expected=self.runtime.snapshot(); slot=campaign_save.SaveSlot("manual",1); manager.save(slot,"now")
        self.runtime.dismiss("alice"); manager.load(slot); self.assertEqual(expected,self.runtime.snapshot())
        legacy={"calendar":{"day":2}}; migrated=adapter.migrate_legacy_world(legacy)
        self.assertNotIn("characterState",legacy); self.assertIn("characterState",migrated)

    def test_long_timeline_checkpoint_resume_equivalence(self):
        initial={"characterState":self.runtime.snapshot()}
        def configure(harness):
            def step(state,context):
                state["characterState"]["characters"][0]["loyalty"] += context.random_int("alice","loyalty",0,1)
            harness.register_step("characters","loyalty_progress",step)
        full=TimelineHarness(seed=11,start_time=0,state=initial); configure(full); full_result=full.run(end_time=100,step_size=1,checkpoint_times=(40,))
        resumed=TimelineHarness.from_checkpoint(full.checkpoints[40]); configure(resumed); resumed_result=resumed.run(end_time=100,step_size=1)
        self.assertEqual(full_result["stateHash"],resumed_result["stateHash"])

if __name__=="__main__": unittest.main()

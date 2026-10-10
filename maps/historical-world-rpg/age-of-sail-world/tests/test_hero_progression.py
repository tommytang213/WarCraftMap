import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine")); sys.path.insert(0,str(ROOT/"tooling"))
from hero_progression import HeroProgressionError, HeroProgressionRuntime, HeroProgressionSaveAdapter, WORLD_STATE_KEY
from hero_progression_catalog import build_report, load_catalog
from global_characters import equipment_catalog


class HeroProgressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog,cls.source=load_catalog(); cls.ids=[x["id"] for x in cls.source["characters"]]
        cls.quests={x["id"] for x in cls.source["personalQuests"]}

    def runtime(self):
        world=json.loads((ROOT/"scenario/world/world.json").read_text())
        return HeroProgressionRuntime(self.catalog,self.ids,quest_ids=self.quests,event_ids={x["id"] for x in world["events"]},
            item_ids=equipment_catalog(),office_ids={"sovereign","settlement_administrator","province_governor","army_commander","fleet_commander"},command_ids={"army","fleet"})

    def test_release_scale_references_and_deterministic_report(self):
        runtime=self.runtime(); self.assertEqual(300,runtime.cap); self.assertGreaterEqual(len(self.ids),100)
        report=build_report(self.catalog,self.source)
        self.assertEqual(report,json.loads((ROOT/"scenario/characters/reports/progression-coverage.json").read_text()))
        self.assertEqual(set(report["dimensions"]["region"]),set(self.source["coverageRegions"]))
        self.assertEqual(32,report["localFieldBudget"])
        subprocess.run([sys.executable,"tooling/hero_progression_catalog.py"],cwd=ROOT,check=True,capture_output=True,text=True)

    def test_curve_adjacent_multi_level_and_cap_are_exact(self):
        r=self.runtime(); ident=self.ids[0]; initial=r.require(ident)["level"]
        self.assertLess(r.experience_for_level(initial),r.experience_for_level(initial+1))
        result=r.award_experience(ident,"quest_completion",multiplier=10000000)
        self.assertEqual(300,result.new_level); self.assertGreater(result.levels_gained,1)
        at_cap=r.award_experience(ident,"combat_participation")
        self.assertEqual((300,0),(at_cap.new_level,at_cap.levels_gained))

    def test_choices_prerequisites_and_invalid_transition_rollback(self):
        r=self.runtime(); ident=next(x["id"] for x in self.catalog["characterProfiles"] if x["personalTreeId"]=="martial_signature")
        r.award_experience(ident,"quest_completion",multiplier=10000000); before=r.snapshot()
        with self.assertRaises(HeroProgressionError): r.choose_perk(ident,"martial_veteran")
        self.assertEqual(before,r.snapshot())
        r.choose_perk(ident,"martial_initiate"); r.choose_perk(ident,"martial_veteran")

    def test_late_era_starting_progression_uses_career_and_role_context(self):
        profiles={x["id"]:x for x in self.catalog["characterProfiles"]}
        self.assertGreater(profiles["jose_de_san_martin"]["startingLevel"],profiles["kupe"]["startingLevel"])
        self.assertTrue(all(x["startingBasis"]["reputationClass"]=="authored_historical" for x in profiles.values()))

    def test_uncapped_strategic_roster_local_budget_and_unique_authority(self):
        r=self.runtime(); loc="stress_fixture"
        for ident in self.ids: r.assign(ident,"field",None,loc)
        with self.assertRaises(HeroProgressionError): r.instantiate_local_group(loc,lambda i,s:i,budget=32)
        r=self.runtime()
        for ident in self.ids[:32]: r.assign(ident,"field",None,loc)
        self.assertEqual(32,len(r.instantiate_local_group(loc,lambda i,s:object())))
        self.assertEqual(len(self.ids),len(r.snapshot()["characters"]))

    def test_wounded_recovery_remote_assignment_and_reconstruction(self):
        r=self.runtime(); ident=self.ids[0]; r.assign(ident,"governor","city_a","city_a"); r.defeat(ident,100,recovery_days=12)
        self.assertEqual("wounded",r.require(ident)["condition"]); self.assertEqual((),r.recover(111)); self.assertEqual((ident,),r.recover(112))
        r.assign(ident,"field",None,"map_a"); snap=r.snapshot(); r.restore(snap)
        self.assertEqual({ident},set(r.instantiate_local_group("map_a",lambda i,s:{"id":i})))

    def test_defeat_keeps_deadline_location_and_progression_across_resume(self):
        runtime = self.runtime()
        first, second = self.ids[:2]
        for ident in (first, second):
            runtime.assign(ident, "field", None, "battle_location")
            runtime.award_experience(ident, "command_victory", multiplier=3)
        before = runtime.require(first)
        runtime.instantiate_local_group("battle_location", lambda i, s: object())
        duration = self.catalog["defeatRecovery"]["recoveryDays"]
        runtime.defeat(first, 100, recovery_days=duration)
        self.assertNotIn(first, runtime._runtime_objects)
        wounded = runtime.snapshot()
        runtime.defeat(first, 115, recovery_days=duration)
        self.assertEqual(wounded, runtime.snapshot())
        self.assertEqual({second}, set(runtime.instantiate_local_group("battle_location", lambda i, s: object())))
        runtime.defeat(second, 100, recovery_days=duration)
        self.assertEqual({}, runtime.instantiate_local_group("battle_location", lambda i, s: object()))
        self.assertEqual((), runtime.recover(115))
        resumed = self.runtime()
        resumed.restore(runtime.snapshot())
        self.assertEqual((), resumed.recover(129))
        self.assertEqual(tuple(sorted((first, second))), resumed.recover(130))
        runtime.recover(1000)
        self.assertEqual(runtime.snapshot(), resumed.snapshot())
        recovered = resumed.snapshot()
        self.assertEqual((), resumed.recover(1000))
        self.assertEqual(recovered, resumed.snapshot())
        for key in ("level", "experience", "skills", "masteries", "perkIds", "commandExperience", "locationId"):
            self.assertEqual(before[key], resumed.require(first)[key], key)
        self.assertIsNone(resumed.require(first)["recoveryUntilDay"])
        self.assertEqual("reserve", resumed.require(first)["assignment"]["kind"])
        self.assertEqual({}, resumed.instantiate_local_group("battle_location", lambda i, s: object()))

    def test_save_load_migration_checkpoint_resume_equivalence(self):
        uninterrupted=self.runtime(); resumed=self.runtime(); ident=self.ids[1]
        for _ in range(10): uninterrupted.award_experience(ident,"command_victory")
        for _ in range(4): resumed.award_experience(ident,"command_victory")
        checkpoint=resumed.snapshot(); resumed=self.runtime(); resumed.restore(checkpoint)
        for _ in range(6): resumed.award_experience(ident,"command_victory")
        self.assertEqual(uninterrupted.snapshot(),resumed.snapshot())
        self.assertIn(WORLD_STATE_KEY,resumed.migrate_legacy_world({"campaignDate":"1700-01-01"}))
        adapter=HeroProgressionSaveAdapter(resumed,{"campaignDate":"1700-01-01"}); world=adapter.capture_world()
        rebuilt=adapter.reconstruct(world); adapter.activate(world,rebuilt)
        self.assertEqual(resumed.snapshot(),world[WORLD_STATE_KEY])

    def test_catalog_and_snapshot_rejection_are_atomic(self):
        bad=copy.deepcopy(self.catalog); bad["characterProfiles"][0]["startingLevel"]=301
        with self.assertRaises(HeroProgressionError):
            bad["characterProfiles"][0]["scenarioUnlocks"]=[]
            HeroProgressionRuntime(bad,self.ids,quest_ids=self.quests)
        r=self.runtime(); before=r.snapshot(); broken=copy.deepcopy(before); broken["characters"][0]["level"]+=1
        with self.assertRaises(HeroProgressionError): r.restore(broken)
        self.assertEqual(before,r.snapshot())


if __name__=="__main__": unittest.main()

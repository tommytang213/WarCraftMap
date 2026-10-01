import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
sys.path.insert(0,str(ROOT/"tooling"))
from character import CharacterError, CharacterRuntime
from character_availability import CharacterAvailabilityError, CharacterAvailabilityRuntime
from global_characters import equipment_catalog, load_source, projection, validate


class GlobalCharacterRosterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=load_source()
        cls.world=json.loads((ROOT/"scenario/world/world.json").read_text())
        cls.by_id={x["id"]:x for x in cls.source["characters"]}
        cls.settlement_regions={x["id"]:x["regionalInstanceId"].split("_")[0] for x in cls.world["settlements"]}

    def context(self, when, **changes):
        value={"date":when,"settlementControllers":{x["id"]:x["controllerPolityId"] for x in self.world["settlements"]},
               "destroyedSettlementIds":[],"rebuiltSettlementIds":[],"activeRegionIds":[],
               "activePolityIds":[x["id"] for x in self.world["polities"]],
               "eventIds":[x["id"] for x in self.world["events"]],
               "technologyIds":[x["id"] for x in self.world["technologies"]+self.world["institutions"]],
               "questIds":[],"discoveryIds":[]}
        value.update(changes); return value

    def test_authority_projection_and_all_reference_gates(self):
        validate(self.source,self.world,equipment_catalog())
        expected=projection(self.source)
        for key,value in expected.items(): self.assertEqual(value,self.world[key])
        subprocess.run([sys.executable,"tooling/global_characters.py"],cwd=ROOT,check=True,capture_output=True,text=True)

    def test_global_coverage_periods_and_selective_relationships(self):
        self.assertEqual(set(self.source["coverageRegions"]),{x["regionId"] for x in self.source["characters"]})
        self.assertTrue(any(x["availabilityWindow"]["startDate"] < "1500" for x in self.source["characters"]))
        self.assertTrue(any(x["availabilityWindow"]["startDate"] > "1750" for x in self.source["characters"]))
        self.assertLess(len(self.source["companionRelationships"]),len(self.source["characters"]))
        self.assertGreaterEqual(len(self.source["characters"]),35)
        self.assertTrue(all(sum(c["regionId"]==r for c in self.source["characters"]) >= 5 for r in self.source["coverageRegions"]))
        self.assertEqual(len(self.source["characters"]),len(self.source["personalQuests"]))
        self.assertTrue(all(q["objectives"] and q["outcomes"] for q in self.source["personalQuests"]))

    def test_historical_identity_roles_offices_and_commands_are_single_authorities(self):
        ids=[c["id"] for c in self.source["characters"]]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertTrue(all(c["authoredHistorical"] and c["historicalEvidenceIds"] for c in self.source["characters"]))
        self.assertTrue(any("sovereign" in c["roleIds"] for c in self.source["characters"]))
        self.assertTrue(any("army_commander" in c["officeEligibility"] for c in self.source["characters"]))
        self.assertTrue(any("fleet_commander" in c["officeEligibility"] for c in self.source["characters"]))

    def test_boundary_dates_conditions_and_deterministic_suppression(self):
        runtime=CharacterAvailabilityRuntime(self.source["characters"])
        leonardo=self.by_id["leonardo_da_vinci"]["availabilityWindow"]
        self.assertFalse(runtime.evaluate("leonardo_da_vinci",self.context("1469-12-31")).available)
        self.assertTrue(runtime.evaluate("leonardo_da_vinci",self.context(leonardo["startDate"])).available)
        self.assertTrue(runtime.evaluate("leonardo_da_vinci",self.context(leonardo["endDate"])).available)
        self.assertFalse(runtime.evaluate("leonardo_da_vinci",self.context("1519-05-03")).available)
        no_event=self.context("1495-01-01",eventIds=[])
        self.assertEqual("conditions_not_met",runtime.evaluate("askia_muhammad",no_event).reason)

    def test_changed_control_destroyed_rebuilt_and_alternate_location(self):
        runtime=CharacterAvailabilityRuntime(self.source["characters"])
        changed=self.context("1800-01-01")
        changed["settlementControllers"]["london"]="france"
        self.assertEqual("dover",runtime.evaluate("horatio_nelson",changed).location_id)
        destroyed=self.context("1480-01-01",destroyedSettlementIds=["florence"])
        self.assertEqual("milan",runtime.evaluate("leonardo_da_vinci",destroyed).location_id)
        destroyed["destroyedSettlementIds"].append("milan")
        self.assertEqual("no_valid_location",runtime.evaluate("leonardo_da_vinci",destroyed).reason)
        rebuilt=self.context("1480-01-01",destroyedSettlementIds=[] ,rebuiltSettlementIds=["florence"])
        self.assertEqual("florence",runtime.evaluate("leonardo_da_vinci",rebuilt).location_id)

    def test_inactive_remote_region_projection_does_not_change_identity(self):
        runtime=CharacterAvailabilityRuntime(self.source["characters"])
        runtime.refresh(self.context("1768-01-01",activeRegionIds=["europe"]))
        before=runtime.snapshot()
        self.assertIn("tupaia",{x["id"] for x in before["characters"]})
        projected=runtime.project_region("europe",self.settlement_regions)
        self.assertIn("catherine_ii",projected)
        self.assertNotIn("tupaia",projected)
        runtime.restore(copy.deepcopy(before)); self.assertEqual(before,runtime.snapshot())

    def test_recruited_and_oathbound_survive_impossible_historical_state(self):
        runtime=CharacterAvailabilityRuntime(self.source["characters"])
        runtime.refresh(self.context("1768-01-01"))
        first=runtime.snapshot()
        retained=runtime.refresh(self.context("1820-01-01",destroyedSettlementIds=["tahiti_council","samoa_fono"]),
                                 {"tupaia":{"recruited":True,"permanentState":"oathbound"}})
        result=next(x for x in retained if x.character_id=="tupaia")
        self.assertEqual("retained_companion",result.reason)
        self.assertEqual(next(x for x in first["characters"] if x["id"]=="tupaia")["authoritativeLocationId"],result.location_id)

    def test_character_transitions_rollback_relationships_and_reconstruction(self):
        runtime=CharacterRuntime(self.world)
        runtime.set_available("tupaia",True); runtime.recruit("tupaia"); runtime.enter_oathbound("tupaia")
        baseline=runtime.snapshot()
        for operation in (lambda:runtime.dismiss("tupaia"),lambda:runtime.set_allegiance("tupaia","england"),lambda:runtime.change_loyalty("tupaia",-1)):
            with self.assertRaises(CharacterError): operation()
            self.assertEqual(baseline,runtime.snapshot())
        runtime.set_available("piri_reis",True)
        runtime.change_relationship("piri_reis","tupaia",25)
        self.assertEqual(40,runtime.relationship_score("piri_reis","tupaia"))
        made=runtime.reconstruct_runtime(lambda definition,view:{"stableId":view.id})
        self.assertEqual({"tupaia"},set(made)); runtime.lose_runtime_representation("tupaia")
        self.assertEqual({"tupaia"},set(runtime.reconstruct_runtime(lambda definition,view:{"stableId":view.id})))

    def test_availability_save_load_checkpoint_and_invalid_restore_rollback(self):
        runtime=CharacterAvailabilityRuntime(self.source["characters"]); runtime.refresh(self.context("1600-01-01"))
        checkpoint=runtime.snapshot(); restored=CharacterAvailabilityRuntime(self.source["characters"]); restored.restore(checkpoint)
        self.assertEqual(checkpoint,restored.snapshot())
        bad=copy.deepcopy(checkpoint); bad["characters"].pop(); baseline=restored.snapshot()
        with self.assertRaises(CharacterAvailabilityError): restored.restore(bad)
        self.assertEqual(baseline,restored.snapshot())

    def test_multi_century_simulation_is_deterministic_and_never_duplicates(self):
        def simulate():
            runtime=CharacterAvailabilityRuntime(self.source["characters"]); result=[]
            for year in range(1450,1821):
                values=runtime.refresh(self.context(f"{year:04d}-01-01")); active=[x.character_id for x in values if x.available]
                self.assertEqual(len(active),len(set(active))); result.append((year,tuple(active)))
            return result,runtime.snapshot()
        self.assertEqual(simulate(),simulate())


if __name__=="__main__": unittest.main()

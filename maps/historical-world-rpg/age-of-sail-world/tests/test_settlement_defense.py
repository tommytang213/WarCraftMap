import copy
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from settlement_defense import RecordingDefenseAdapter, SettlementDefenseError, SettlementDefenseRuntime, SettlementDefenseSaveAdapter


DEFS={"schemaVersion":1,"rules":{"reinforcementIntervalSeconds":10,"quietPeriodSeconds":20,"strengthPerUnit":10,
    "manpowerPerStrength":1,"supplyPerStrength":2,"replenishmentIntervalDays":5,"replenishmentStrength":4},
    "defaultProfileId":"local_militia","profiles":[{"id":"local_militia","baseQuality":45,
        "composition":[{"archetypeId":"levy","weight":3}],"behaviorIds":["hold_core"]}],
    "resolverRules":[
        {"id":"gunpowder","when":{"technologyIdsAll":["gunpowder"]},"addComposition":[{"archetypeId":"musketeer","weight":2}],"behaviorIds":["volley_fire"]},
        {"id":"fortified","when":{"buildingIdsAny":["stone_wall"]},"addComposition":[{"archetypeId":"artillery","weight":1}],"behaviorIds":["fortification_fire"]}],
    "initialGarrisons":[{"settlementId":"port","availableStrength":20,"manpower":40,"reserves":20,"supply":100,"readiness":70,"profileId":"local_militia"}]}

class View:
    controller_polity_id="england"
class Settlements:
    def ids(self): return ("port",)
    def require(self,sid):
        if sid!="port": raise ValueError
        return View()

class DefenseTests(unittest.TestCase):
    def setUp(self): self.adapter=RecordingDefenseAdapter(); self.runtime=SettlementDefenseRuntime(DEFS,Settlements(),self.adapter)
    def test_attack_idempotence_resources_waves_and_quiet_cleanup(self):
        units=self.runtime.start_attack("port",attacker_polity_id="france",conflict_id="war_one",now_seconds=0,conflict_validated=True)
        self.assertEqual(20,sum(x.strength for x in units)); self.assertEqual(0,self.runtime.management_status("port")["availableStrength"])
        self.assertEqual(units,self.runtime.start_attack("port",attacker_polity_id="france",conflict_id="war_one",now_seconds=1,conflict_validated=True))
        self.runtime.advance(10); self.assertEqual(10,self.runtime.management_status("port")["reserves"])
        self.runtime.advance(20); self.assertEqual(0,self.runtime.management_status("port")["reserves"])
        self.runtime.advance(100); self.assertEqual(40,sum(x.strength for x in self.runtime.units("port")))
        self.runtime.end_attack("port",100); self.runtime.advance(119); self.assertTrue(self.runtime.units("port"))
        self.runtime.advance(120); self.assertFalse(self.runtime.units("port")); self.assertEqual(40,self.runtime.management_status("port")["availableStrength"])
        self.assertEqual(40,self.runtime.management_status("port")["manpower"]); self.assertEqual(100,self.runtime.management_status("port")["supply"])
    def test_casualties_persist_and_replenishment_costs_time(self):
        unit=self.runtime.start_attack("port",attacker_polity_id="france",conflict_id="war_one",now_seconds=0,conflict_validated=True)[0]
        self.runtime.report_casualty(unit.id,6,now_seconds=2); self.runtime.end_attack("port",2); self.runtime.advance(22)
        self.assertEqual((14,6),(self.runtime.management_status("port")["availableStrength"],self.runtime.management_status("port")["casualties"]))
        self.assertEqual(0,self.runtime.replenish("port",day=4,manpower=99,supply=99))
        self.assertEqual(4,self.runtime.replenish("port",day=5,manpower=4,supply=8))
        self.assertEqual(2,self.runtime.management_status("port")["casualties"])
    def test_protected_units_and_third_party_validation(self):
        with self.assertRaises(SettlementDefenseError): self.runtime.start_attack("port",attacker_polity_id="pirates",conflict_id="raid",now_seconds=0,conflict_validated=False)
        unit=self.runtime.start_attack("port",attacker_polity_id="france",conflict_id="war_one",now_seconds=0,conflict_validated=True)[0]
        for action in ("command","transfer","embark","loot","disband","inventory","cargo"): self.assertFalse(self.runtime.authorize_action(unit.id,action))
        self.assertTrue(self.runtime.management_status("port")["aiControlled"]); self.assertFalse(self.runtime.management_status("port")["directControlAllowed"])
    def test_save_load_mid_siege_and_capture_cleanup(self):
        unit=self.runtime.start_attack("port",attacker_polity_id="france",conflict_id="war_one",now_seconds=0,conflict_validated=True)[0]
        self.runtime.report_casualty(unit.id,3,now_seconds=2); snapshot=self.runtime.snapshot()
        restored=SettlementDefenseRuntime(DEFS,Settlements(),RecordingDefenseAdapter()); save=SettlementDefenseSaveAdapter(restored,{})
        save.activate({"settlementDefenseState":snapshot},copy.deepcopy(snapshot))
        self.assertEqual(17,sum(x.strength for x in restored.units("port"))); self.assertEqual(3,restored.management_status("port")["casualties"])
        restored.on_capture("port","france",3); self.assertFalse(restored.units("port")); self.assertEqual(0,restored.management_status("port")["availableStrength"])
    def test_map_unload_reload_reprojects_without_free_resources(self):
        self.runtime.start_attack("port",attacker_polity_id="france",conflict_id="war_one",now_seconds=0,conflict_validated=True)
        before=self.runtime.management_status("port"); self.runtime.retire_region(["port"])
        abstract=self.runtime.management_status("port"); self.assertEqual(before["availableStrength"]+before["activeDefenseStrength"],abstract["availableStrength"])
        self.runtime.activate_region(["port"]); after=self.runtime.management_status("port")
        self.assertEqual(before["activeDefenseStrength"],after["activeDefenseStrength"]); self.assertEqual(before["availableStrength"],after["availableStrength"])
    def test_multi_era_qualitative_resolution(self):
        early=self.runtime.resolve("port",{"year":1450,"polityId":"england","technologyIds":[],"buildingIds":[],"unrest":0})
        late=self.runtime.resolve("port",{"year":1750,"polityId":"england","technologyIds":["gunpowder"],"buildingIds":["stone_wall"],"institutionIds":[],"equipmentIds":[],"reformIds":[],"resourceIds":[],"administratorCommand":80,"unrest":10})
        self.assertEqual(["levy"],[x["archetypeId"] for x in early["composition"]])
        self.assertEqual({"levy","musketeer","artillery"},{x["archetypeId"] for x in late["composition"]})
        self.assertIn("volley_fire",late["behaviorIds"]); self.assertGreater(late["quality"],early["quality"])

if __name__=="__main__": unittest.main()

import copy, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from administration import AdministrationError, AdministrationRuntime
from character import CharacterRuntime

def fixture():
    return {"settlements":[{"id":"port","controllerPolityId":"england","cultureId":"english"},{"id":"town","controllerPolityId":"england","cultureId":"english"}],
      "provinces":[{"id":"shire"}],"polities":[{"id":"england","cultureId":"english"}],
      "officeNameCultures":[{"id":"english","givenNames":["Anne","Thomas"],"familyNames":["Hawkins","Ward"],"traitIds":["pragmatic"],"professionId":"administrator"}],
      "officeTypes":[{"id":"mayor","role":"settlement_administrator","title":"Mayor","baseCapacity":1,"prestige":20},{"id":"governor","role":"province_governor","title":"Governor","baseCapacity":3,"prestige":50},{"id":"ruler","role":"sovereign","title":"Council Speaker","baseCapacity":8,"prestige":90},{"id":"general","role":"army_commander","title":"General","baseCapacity":1,"prestige":40},{"id":"admiral","role":"fleet_commander","title":"Admiral","baseCapacity":1,"prestige":40}],
      "politicalOffices":[]}

class AdministrationTests(unittest.TestCase):
    def test_deterministic_unique_persistent_officials_and_no_runtime_names(self):
        a=AdministrationRuntime(fixture(),campaign_seed="x"); b=AdministrationRuntime(fixture(),campaign_seed="x")
        self.assertEqual(a.snapshot(),b.snapshot()); self.assertEqual(2,len(a.officials))
        self.assertEqual(2,len({x["displayName"] for x in a.officials.values()}))
        self.assertNotIn("Governor_",str(a.snapshot()))
        restored=AdministrationRuntime(fixture(),campaign_seed="different"); restored.restore(a.snapshot()); self.assertEqual(a.snapshot(),restored.snapshot())

    def test_appointment_does_not_change_control_and_cycling_does_not_farm(self):
        runtime=AdministrationRuntime(fixture()); office="administrator_port"; official=runtime.offices[office]["holderCharacterId"]
        control=copy.deepcopy(runtime.settlements); initial=runtime.officials[official]["loyalty"]
        runtime.appoint(office,official); after=runtime.officials[official]["loyalty"]
        runtime.dismiss(office,confirm_risk=True); runtime.appoint(office,official)
        self.assertLessEqual(runtime.officials[official]["loyalty"],after); self.assertEqual(control,runtime.settlements); self.assertGreaterEqual(after,initial)

    def test_capacity_multijurisdiction_ui_location_and_no_clones(self):
        r=AdministrationRuntime(fixture()); holder=r.offices["administrator_port"]["holderCharacterId"]
        r.offices["administrator_port"]["jurisdictionIds"]=["port","town"]
        view=r.view("administrator_port")
        self.assertEqual(holder,view["holderCharacterId"]); self.assertIn("administration",view["skills"]); self.assertGreater(view["capacity"],1)
        made=[]; r.reconstruct(("port","town"),lambda x:made.append(x["id"]) or object()); self.assertEqual(2,len(set(made)))

    def test_capture_fills_vacancy_and_risky_removal_warns(self):
        r=AdministrationRuntime(fixture()); oid="administrator_port"; holder=r.offices[oid]["holderCharacterId"]
        r.dismiss(oid,confirm_risk=True); r.on_settlement_acquired("port","france")
        self.assertIsNotNone(r.offices[oid]["holderCharacterId"]); self.assertTrue(r.offices[oid]["acting"])
        r.officials[holder]["loyalty"]=-80; r.offices[oid]["holderCharacterId"]=holder; r.offices[oid]["localSupport"]=100
        self.assertTrue(r.removal_warning(oid).risky)
        with self.assertRaisesRegex(AdministrationError,"Warning"): r.dismiss(oid)

    def test_oathbound_never_regresses_and_collective_sovereign_is_valid(self):
        r=AdministrationRuntime(fixture()); holder=r.offices["administrator_port"]["holderCharacterId"]
        r.officials[holder]["permanentState"]="oathbound"; before=r.officials[holder]["loyalty"]
        r.dismiss("administrator_port",confirm_risk=True); self.assertEqual(before,r.officials[holder]["loyalty"])
        r.offices["english_council"]={"id":"english_council","officeTypeId":"ruler","jurisdictionIds":["england"],"holderCharacterId":None,"collectiveBodyId":"parliament","collectiveBodyName":"Parliament"}
        # collective governance is represented by a vacant-holder sovereign office, not a fake monarch
        self.assertIsNone(r.offices["english_council"]["holderCharacterId"])
        self.assertTrue(r.view("english_council")["collective"])

    def test_stress_hundreds_remain_abstract(self):
        f=fixture(); f["settlements"]=[{"id":f"city_{i}","controllerPolityId":"england","cultureId":"english"} for i in range(400)]
        r=AdministrationRuntime(f); self.assertEqual(400,len(r.officials)); self.assertEqual({},r.reconstruct((),lambda _:object()))

if __name__=="__main__": unittest.main()

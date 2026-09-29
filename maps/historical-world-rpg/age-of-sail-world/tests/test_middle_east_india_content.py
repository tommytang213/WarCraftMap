import copy, json, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"tooling")); sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from middle_east_india_content import MiddleEastIndiaContentError, project, validate
from settlement import RecordingSettlementAdapter, SettlementRuntime

class MiddleEastIndiaContentTests(unittest.TestCase):
    def setUp(self):
        self.path=ROOT/"scenario/settlements/middle-east-india-1450.json"; self.source=json.loads(self.path.read_text()); self.world=json.loads((ROOT/"scenario/world/world.json").read_text())
    def candidate(self,value):
        directory=tempfile.TemporaryDirectory(); path=Path(directory.name)/"candidate.json"; path.write_text(json.dumps(value)); return directory,path
    def test_authority_projection_and_capture_references(self):
        source,politics,geography,positions=validate(); projected=project(source,politics,geography,positions,self.world)
        self.assertEqual(projected,project(copy.deepcopy(source),politics,geography,positions,self.world)); selected=[x for x in projected["settlements"] if x.get("regionalInstanceId")=="middle_east_india_mainland"]
        self.assertEqual((26,8,16), (len(selected),sum("portAccess" in x for x in selected),len(source["tradeRoutes"])))
        cores={x["id"] for x in projected["cityCores"]}; layouts={x["id"] for x in projected["defenseLayouts"]}
        for item in selected:
            self.assertTrue(item["capturable"] and item["civilianFacilitiesInvulnerable"]); self.assertIn(item["cityCoreId"],cores); self.assertIn(item["defenseLayoutId"],layouts)
    def test_inland_maritime_route_and_bad_port_are_rejected(self):
        for mutate,message in ((lambda x:x["tradeRoutes"].append({"id":"bad_ship","fromSettlementId":"delhi","toSettlementId":"aden","kind":"maritime","contract":"settlement_trade_endpoint"}),"inland maritime route"),(lambda x:x["settlements"].__iter__().__next__().update({"port":{"maritimeZoneId":"red_sea_navigation","access":"coastal"}}),"invalid port access")):
            value=copy.deepcopy(self.source); mutate(value); directory,path=self.candidate(value)
            with directory,self.assertRaisesRegex(MiddleEastIndiaContentError,message): validate(path)
    def test_overlap_bounds_and_entry_clearance_are_rejected(self):
        cases=[]
        outside=copy.deepcopy(self.source); next(x for x in outside["settlements"] if x["id"]=="konya")["position"]=[101,67]; cases.append((outside,"outside local bounds"))
        overlap=copy.deepcopy(self.source); next(x for x in overlap["settlements"] if x["id"]=="konya")["position"]=[10,72]; cases.append((overlap,"overlap"))
        blocked=copy.deepcopy(self.source); next(x for x in blocked["settlements"] if x["id"]=="konya")["position"]=[5,68]; cases.append((blocked,"obstructs entry anchor"))
        for value,message in cases:
            directory,path=self.candidate(value)
            with directory,self.assertRaisesRegex(MiddleEastIndiaContentError,message): validate(path)
    def test_trade_and_boundary_reachability(self):
        required=set(self.source["requiredOverlandEndpoints"]); edges=[(x["fromSettlementId"],x["toSettlementId"]) for x in self.source["tradeRoutes"] if x["kind"]=="overland"]
        seen=set(); pending=[next(iter(required))]
        while pending:
            current=pending.pop()
            if current not in seen: seen.add(current); pending.extend(b if a==current else a for a,b in edges if a==current or b==current)
        self.assertTrue(required<=seen); self.assertEqual({"europe","africa","southeast_asia"},{x["neighborRegionId"] for x in self.source["transitions"]})
    def test_activation_retirement_capture_and_save_restore(self):
        runtime=SettlementRuntime(self.world,RecordingSettlementAdapter()); regional=sorted(x["id"] for x in self.world["settlements"] if x.get("regionalInstanceId")=="middle_east_india_mainland")
        self.assertEqual(tuple(regional),runtime.activate_region("middle_east_india_mainland")); runtime.update("delhi",controllerPolityId="timurid_empire"); runtime.set_service_available("delhi","market",False); saved=runtime.snapshot(); self.assertEqual(tuple(regional),runtime.retire_region("middle_east_india_mainland"))
        restored=SettlementRuntime(self.world,RecordingSettlementAdapter()); restored.restore(saved,reconstruct=True); self.assertEqual("timurid_empire",restored.require("delhi").controller_polity_id); self.assertFalse(restored.require("delhi").services["market"]); self.assertTrue(restored.require("delhi").represented)

if __name__=="__main__": unittest.main()

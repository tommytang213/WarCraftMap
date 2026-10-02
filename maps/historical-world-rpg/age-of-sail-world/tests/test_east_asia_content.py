import copy, json, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"tooling")); sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from east_asia_content import EastAsiaContentError, project, update_economy, validate
from settlement import RecordingSettlementAdapter, SettlementRuntime

class EastAsiaContentTests(unittest.TestCase):
    def setUp(self):
        self.path=ROOT/"scenario/settlements/east-asia-1450.json"; self.source=json.loads(self.path.read_text()); self.world=json.loads((ROOT/"scenario/world/world.json").read_text()); self.economy=json.loads((ROOT/"scenario/economy/economy.json").read_text())
    def candidate(self,value):
        directory=tempfile.TemporaryDirectory(); path=Path(directory.name)/"candidate.json"; path.write_text(json.dumps(value)); return directory,path
    def test_authority_coverage_and_deterministic_projection(self):
        source,politics,geography,positions=validate(); projected=project(source,politics,geography,positions,self.world)
        self.assertEqual((118,36,144,4),(len(source["settlements"]),sum("port" in x for x in source["settlements"]),len(source["tradeRoutes"]),len(source["transitions"])))
        self.assertEqual(projected,project(copy.deepcopy(source),politics,geography,positions,self.world))
        selected=[x for x in projected["settlements"] if x["id"] in {s["id"] for s in source["settlements"]}]
        cores={x["id"] for x in projected["cityCores"]}; layouts={x["id"] for x in projected["defenseLayouts"]}
        for item in selected:
            self.assertTrue(item["capturable"] and item["civilianFacilitiesInvulnerable"]); self.assertIn(item["cityCoreId"],cores); self.assertIn(item["defenseLayoutId"],layouts); self.assertEqual(item["regionalInstanceId"],item["physicalMapId"])
    def test_port_validity_and_inland_maritime_rejection(self):
        bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="beijing")["port"]={"maritimeZoneId":"node_east_china_sea","access":"coastal"}
        directory,path=self.candidate(bad)
        with directory,self.assertRaisesRegex(EastAsiaContentError,"invalid port access"): validate(path)
        bad=copy.deepcopy(self.source); bad["tradeRoutes"].append({"id":"bad_ship","fromSettlementId":"beijing","toSettlementId":"busan","kind":"maritime","contract":"settlement_trade_endpoint"})
        directory,path=self.candidate(bad)
        with directory,self.assertRaisesRegex(EastAsiaContentError,"inland maritime route"): validate(path)
    def test_placement_overlap_accessibility_and_entry_clearance(self):
        mutations=[]
        bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="beijing")["position"]=[200,200]; mutations.append((bad,"outside local bounds"))
        bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="xian")["position"]=[52,45]; mutations.append((bad,"overlap"))
        bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="beijing")["navigationZoneId"]="node_tibetan_barrier"; mutations.append((bad,"invalid navigation zone"))
        bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="chengdu")["position"]=[16,1]; mutations.append((bad,"obstructs entry anchor"))
        for value,message in mutations:
            directory,path=self.candidate(value)
            with self.subTest(message=message),directory,self.assertRaisesRegex(EastAsiaContentError,message): validate(path)
    def test_trade_and_adjoining_region_reachability(self):
        source,_,_,_=validate(); mainland=[(x["fromSettlementId"],x["toSettlementId"]) for x in source["tradeRoutes"] if x["kind"]!="maritime"]
        seen=set(); pending=[source["requiredMainlandEndpoints"][0]]
        while pending:
            node=pending.pop()
            if node not in seen: seen.add(node); pending.extend(b if a==node else a for a,b in mainland if node in (a,b))
        self.assertTrue(set(source["requiredMainlandEndpoints"])<=seen)
        self.assertEqual({"middle_east_india","southeast_asia","pacific","americas_caribbean"},{x["neighborRegionId"] for x in source["transitions"]})
    def test_activation_retirement_reconstruction_capture_and_save(self):
        runtime=SettlementRuntime(self.world,RecordingSettlementAdapter())
        for region in sorted({x["regionalInstanceId"] for x in self.source["settlements"]}): runtime.activate_region(region)
        runtime.update("beijing",controllerPolityId="oirat_confederation"); runtime.set_service_available("beijing","market",False)
        runtime.retire_region("east_asia_china_north"); runtime.update("beijing",kind="fort"); saved=runtime.snapshot()
        restored=SettlementRuntime(self.world,RecordingSettlementAdapter()); restored.restore(saved,reconstruct=True)
        self.assertEqual("oirat_confederation",restored.require("beijing").controller_polity_id); self.assertEqual("fort",restored.require("beijing").kind); self.assertFalse(restored.require("beijing").services["market"]); self.assertTrue(restored.require("beijing").represented)
    def test_economy_projection_is_deterministic_and_diverse(self):
        source,_,_,_=validate(); a=update_economy(source,self.economy); b=update_economy(copy.deepcopy(source),self.economy); self.assertEqual(a,b)
        markets=[x for x in a["catalog"]["markets"] if x["id"].startswith("eas_")]; balances=[x for x in a["state"]["storeBalances"] if x["id"].startswith("eas_")]
        self.assertEqual((118,118),(len(markets),len(balances))); self.assertGreater(len({x["currencies"][0]["amountMinor"] for x in balances}),10)

if __name__=="__main__": unittest.main()

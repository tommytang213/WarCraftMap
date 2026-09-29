import copy, json, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"tooling")); sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from southeast_asia_content import SoutheastAsiaContentError, project, update_economy, validate
from settlement import RecordingSettlementAdapter, SettlementRuntime

class SoutheastAsiaContentTests(unittest.TestCase):
    def setUp(self):
        self.path=ROOT/"scenario/settlements/southeast-asia-1450.json"; self.source=json.loads(self.path.read_text()); self.world=json.loads((ROOT/"scenario/world/world.json").read_text()); self.economy=json.loads((ROOT/"scenario/economy/economy.json").read_text())
    def candidate(self,value):
        directory=tempfile.TemporaryDirectory(); path=Path(directory.name)/"candidate.json"; path.write_text(json.dumps(value)); return directory,path
    def test_authority_references_coverage_and_deterministic_projection(self):
        source,politics,geography,positions=validate(); projected=project(source,politics,geography,positions,self.world)
        self.assertEqual((20,15,20,3),(len(source["settlements"]),sum("port" in x for x in source["settlements"]),len(source["tradeRoutes"]),len(source["transitions"])))
        self.assertEqual(projected,project(copy.deepcopy(source),politics,geography,positions,self.world))
        selected=[x for x in projected["settlements"] if x["id"] in {s["id"] for s in source["settlements"]}]
        self.assertEqual(20,len(selected)); cores={x["id"] for x in projected["cityCores"]}; layouts={x["id"] for x in projected["defenseLayouts"]}
        for item in selected:
            self.assertTrue(item["capturable"] and item["civilianFacilitiesInvulnerable"]); self.assertIn(item["cityCoreId"],cores); self.assertIn(item["defenseLayoutId"],layouts); self.assertEqual(item["regionalInstanceId"],item["physicalMapId"])
    def test_port_topology_and_inland_maritime_routes_are_rejected(self):
        bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="ava")["port"]={"maritimeZoneId":"node_bay_bengal","access":"coastal"}
        directory,path=self.candidate(bad)
        with directory,self.assertRaisesRegex(SoutheastAsiaContentError,"invalid port access"): validate(path)
        bad=copy.deepcopy(self.source); bad["tradeRoutes"].append({"id":"bad_ship","fromSettlementId":"ava","toSettlementId":"malacca","kind":"maritime","contract":"settlement_trade_endpoint"})
        directory,path=self.candidate(bad)
        with directory,self.assertRaisesRegex(SoutheastAsiaContentError,"inland maritime route"): validate(path)
    def test_placement_accessibility_overlap_and_entry_clearance(self):
        cases=[]
        bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="ava")["position"]=[200,200]; cases.append((bad,"outside local bounds"))
        bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="ava")["position"]=[20,34]; cases.append((bad,"overlap"))
        bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="ava")["position"]=[0,48]; cases.append((bad,"obstructs entry anchor"))
        bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="ava")["navigationZoneId"]="node_arakan_barrier"; cases.append((bad,"invalid navigation zone"))
        for value,message in cases:
            directory,path=self.candidate(value)
            with self.subTest(message=message),directory,self.assertRaisesRegex(SoutheastAsiaContentError,message): validate(path)
    def test_mainland_maritime_and_adjoining_region_reachability(self):
        source,_,_,_=validate(); mainland=[(x["fromSettlementId"],x["toSettlementId"]) for x in source["tradeRoutes"] if x["kind"]!="maritime"]
        seen=set(); pending=[source["requiredMainlandEndpoints"][0]]
        while pending:
            n=pending.pop()
            if n not in seen: seen.add(n); pending.extend(b if a==n else a for a,b in mainland if n in (a,b))
        self.assertTrue(set(source["requiredMainlandEndpoints"])<=seen); self.assertEqual({"middle_east_india","east_asia","pacific"},{x["neighborRegionId"] for x in source["transitions"]})
    def test_activation_retirement_capture_inactive_mutation_and_save_restore(self):
        runtime=SettlementRuntime(self.world,RecordingSettlementAdapter()); content_ids={x["id"] for x in self.source["settlements"]}; regions=sorted({x["regionalInstanceId"] for x in self.source["settlements"]})
        for region in regions: runtime.activate_region(region)
        runtime.update("malacca",controllerPolityId="ayutthaya_kingdom"); runtime.set_service_available("malacca","market",False)
        runtime.retire_region("sea_malay_sumatra"); runtime.update("malacca",kind="fort"); saved=runtime.snapshot()
        replacement=SettlementRuntime(self.world,RecordingSettlementAdapter()); replacement.restore(saved,reconstruct=True)
        self.assertEqual("ayutthaya_kingdom",replacement.require("malacca").controller_polity_id); self.assertEqual("fort",replacement.require("malacca").kind); self.assertFalse(replacement.require("malacca").services["market"]); self.assertTrue(replacement.require("malacca").represented)
        self.assertTrue(content_ids<=set(replacement.ids()))
    def test_settlement_economy_profiles_and_market_projection_are_deterministic(self):
        source,_,_,_=validate(); a=update_economy(source,self.economy); b=update_economy(copy.deepcopy(source),self.economy); self.assertEqual(a,b)
        markets=[x for x in a["catalog"]["markets"] if x["id"].startswith("sea_")]; balances=[x for x in a["state"]["storeBalances"] if x["id"].startswith("sea_")]
        self.assertEqual((20,20),(len(markets),len(balances))); self.assertGreater(len({x["currencies"][0]["amountMinor"] for x in balances}),10)

if __name__=="__main__": unittest.main()

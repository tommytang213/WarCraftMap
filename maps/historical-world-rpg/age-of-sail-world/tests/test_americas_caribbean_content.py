import copy, json, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"tooling")); sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from americas_caribbean_content import AmericasContentError, project, update_economy, validate
from settlement import RecordingSettlementAdapter, SettlementRuntime

class AmericasContentTests(unittest.TestCase):
 def setUp(self):
  self.path=ROOT/"scenario/settlements/americas-caribbean-1450.json"; self.source=json.loads(self.path.read_text()); self.world=json.loads((ROOT/"scenario/world/world.json").read_text()); self.economy=json.loads((ROOT/"scenario/economy/economy.json").read_text())
 def candidate(self,value):
  d=tempfile.TemporaryDirectory(); p=Path(d.name)/"candidate.json"; p.write_text(json.dumps(value)); return d,p
 def test_authority_coverage_and_deterministic_projection(self):
  source,politics,geography,positions=validate(); a=project(source,politics,geography,positions,self.world); b=project(copy.deepcopy(source),politics,geography,positions,self.world)
  self.assertEqual((155,40,52,4),(len(source["settlements"]),sum("port" in x for x in source["settlements"]),len(source["tradeRoutes"]),len(source["transitions"]))); self.assertEqual(a,b)
  ids={x["id"] for x in source["settlements"]}; selected=[x for x in a["settlements"] if x["id"] in ids]; cores={x["id"] for x in a["cityCores"]}; defenses={x["id"] for x in a["defenseLayouts"]}
  for x in selected: self.assertTrue(x["capturable"] and x["civilianFacilitiesInvulnerable"]); self.assertIn(x["cityCoreId"],cores); self.assertIn(x["defenseLayoutId"],defenses); self.assertEqual(x["regionalInstanceId"],x["physicalMapId"])
 def test_port_and_inland_maritime_rejection(self):
  bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="cusco")["port"]={"maritimeZoneId":"node_south_pacific","access":"coastal"}; d,p=self.candidate(bad)
  with d,self.assertRaisesRegex(AmericasContentError,"invalid port access"): validate(p)
  bad=copy.deepcopy(self.source); bad["tradeRoutes"].append({"id":"invalid_ship","fromSettlementId":"cusco","toSettlementId":"chan_chan","kind":"maritime","contract":"settlement_trade_endpoint"}); d,p=self.candidate(bad)
  with d,self.assertRaisesRegex(AmericasContentError,"inland maritime route"): validate(p)
 def test_placement_accessibility_overlap_and_physical_map(self):
  cases=[]
  bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="cusco")["position"]=[500,500]; cases.append((bad,"outside local bounds"))
  bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="cusco")["position"]=next(x for x in bad["settlements"] if x["id"]=="chan_chan")["position"]; cases.append((bad,"overlap"))
  bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="cusco")["navigationZoneId"]="node_andes_barrier"; cases.append((bad,"invalid navigation zone"))
  bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="cusco")["physicalMapId"]="americas_caribbean_islands"; cases.append((bad,"invalid physical-map assignment"))
  for value,message in cases:
   d,p=self.candidate(value)
   with self.subTest(message=message),d,self.assertRaisesRegex(AmericasContentError,message): validate(p)
 def test_trade_and_transition_reachability(self):
  source,_,_,_=validate(); self.assertEqual({"europe","africa","east_asia","pacific"},{x["neighborRegionId"] for x in source["transitions"]}); ports={x["id"] for x in source["settlements"] if "port" in x}
  routed={v for r in source["tradeRoutes"] if r["kind"]=="maritime" for v in (r["fromSettlementId"],r["toSettlementId"])}; self.assertTrue(ports<=routed)
 def test_activation_capture_inactive_mutation_reconstruction_and_save(self):
  runtime=SettlementRuntime(self.world,RecordingSettlementAdapter()); runtime.activate_region("americas_mexico_central"); runtime.update("tenochtitlan",controllerPolityId="acolhua_texcoco"); runtime.set_service_available("tenochtitlan","market",False); runtime.retire_region("americas_mexico_central"); runtime.update("tenochtitlan",kind="fort"); saved=runtime.snapshot(); replacement=SettlementRuntime(self.world,RecordingSettlementAdapter()); replacement.restore(saved,reconstruct=True)
  self.assertEqual("acolhua_texcoco",replacement.require("tenochtitlan").controller_polity_id); self.assertEqual("fort",replacement.require("tenochtitlan").kind); self.assertFalse(replacement.require("tenochtitlan").services["market"]); self.assertTrue(replacement.require("tenochtitlan").represented)
 def test_economy_profiles_and_market_projection(self):
  source,_,_,_=validate(); a=update_economy(source,self.economy); self.assertEqual(a,update_economy(copy.deepcopy(source),self.economy)); markets=[x for x in a["catalog"]["markets"] if x["id"].startswith("amer_")]; balances=[x for x in a["state"]["storeBalances"] if x["id"].startswith("amer_")]; self.assertEqual((155,155),(len(markets),len(balances))); self.assertGreater(len({x["currencies"][0]["amountMinor"] for x in balances}),10)
if __name__=="__main__": unittest.main()

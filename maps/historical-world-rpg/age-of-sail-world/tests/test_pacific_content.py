import copy, json, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"tooling")); sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from pacific_content import PacificContentError, project, update_economy, validate
from pacific_politics import validate as validate_politics
from settlement import RecordingSettlementAdapter, SettlementRuntime

class PacificContentTests(unittest.TestCase):
 def setUp(self):
  self.source=json.loads((ROOT/"scenario/settlements/pacific-1450.json").read_text()); self.world=json.loads((ROOT/"scenario/world/world.json").read_text()); self.economy=json.loads((ROOT/"scenario/economy/economy.json").read_text())
 def candidate(self,value):
  d=tempfile.TemporaryDirectory(); p=Path(d.name)/"candidate.json"; p.write_text(json.dumps(value)); return d,p
 def test_political_authority_coverage_and_deterministic_projection(self):
  politics=validate_politics(); source,politics,geography,positions=validate(); a=project(source,politics,geography,positions,self.world); b=project(copy.deepcopy(source),politics,geography,positions,self.world)
  self.assertEqual((24,39,20,40),(len(politics["polities"]),len(source["settlements"]),sum("port" in x for x in source["settlements"]),len(source["tradeRoutes"]))); self.assertEqual(a,b)
  selected={x["id"]:x for x in a["settlements"] if x["id"] in {s["id"] for s in source["settlements"]}}; cores={x["id"] for x in a["cityCores"]}; defenses={x["id"] for x in a["defenseLayouts"]}
  for item in source["settlements"]:
   row=selected[item["id"]]; self.assertEqual(item["physicalMapId"],row["physicalMapId"]); self.assertEqual(item["captureModel"]=="city_core",row["capturable"])
   if row["capturable"]: self.assertIn(row["cityCoreId"],cores); self.assertIn(row["defenseLayoutId"],defenses)
   else: self.assertNotIn("cityCoreId",row); self.assertNotIn("defenseLayoutId",row)
 def test_port_validity_and_inland_maritime_rejection(self):
  bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="kaiapoi_pa")["port"]={"maritimeZoneId":"node_new_zealand_sea","access":"coastal"}; d,p=self.candidate(bad)
  with d,self.assertRaisesRegex(PacificContentError,"invalid port access"): validate(p)
  bad=copy.deepcopy(self.source); bad["tradeRoutes"].append({"id":"invalid_inland_ship","fromSettlementId":"waipio","toSettlementId":"kaiapoi_pa","kind":"maritime","contract":"settlement_trade_endpoint"}); d,p=self.candidate(bad)
  with d,self.assertRaisesRegex(PacificContentError,"inland maritime route"): validate(p)
 def test_placement_overlap_accessibility_and_physical_map(self):
  cases=[]
  bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="waipio")["position"]=[500,500]; cases.append((bad,"outside local bounds"))
  bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="koror")["position"]=next(x for x in bad["settlements"] if x["id"]=="nan_madol")["position"]; cases.append((bad,"overlap"))
  bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="koror")["navigationZoneId"]="node_great_barrier_reef"; cases.append((bad,"invalid navigation zone"))
  bad=copy.deepcopy(self.source); next(x for x in bad["settlements"] if x["id"]=="koror")["physicalMapId"]="pacific_north"; cases.append((bad,"invalid physical-map assignment"))
  for value,message in cases:
   d,p=self.candidate(value)
   with self.subTest(message=message),d,self.assertRaisesRegex(PacificContentError,message): validate(p)
 def test_inter_island_long_distance_and_adjoining_reachability(self):
  source,_,_,_=validate(); self.assertEqual({"east_asia","southeast_asia","americas_caribbean"},{x["neighborRegionId"] for x in source["transitions"]})
  graph={}
  for r in source["tradeRoutes"]:
   if r["kind"]=="maritime": graph.setdefault(r["fromSettlementId"],set()).add(r["toSettlementId"]); graph.setdefault(r["toSettlementId"],set()).add(r["fromSettlementId"])
  seen=set(); pending=["honolulu_anchorage"]
  while pending:
   x=pending.pop()
   if x not in seen: seen.add(x); pending.extend(graph.get(x,()))
  self.assertIn("hanga_roa_anchorage",seen); self.assertIn("tamaki_makaurau",seen); self.assertEqual({x["id"] for x in source["settlements"] if "port" in x},seen)
 def test_activation_retirement_reconstruction_capture_inactive_mutation_and_save(self):
  runtime=SettlementRuntime(self.world,RecordingSettlementAdapter()); runtime.activate_region("pacific_west_polynesia"); runtime.update("mua",controllerPolityId="fijian_vanua"); runtime.set_service_available("mua","market",False); runtime.retire_region("pacific_west_polynesia"); runtime.update("mua",kind="fort"); saved=runtime.snapshot(); restored=SettlementRuntime(self.world,RecordingSettlementAdapter()); restored.restore(saved,reconstruct=True)
  self.assertEqual("fijian_vanua",restored.require("mua").controller_polity_id); self.assertEqual("fort",restored.require("mua").kind); self.assertFalse(restored.require("mua").services["market"]); self.assertTrue(restored.require("mua").represented)
 def test_settlement_economies_and_deterministic_market_projection(self):
  source,_,_,_=validate(); a=update_economy(source,self.economy); self.assertEqual(a,update_economy(copy.deepcopy(source),self.economy)); markets=[x for x in a["catalog"]["markets"] if x["id"].startswith("pac_")]; balances=[x for x in a["state"]["storeBalances"] if x["id"].startswith("pac_")]; self.assertEqual((39,39),(len(markets),len(balances))); self.assertGreater(len({x["currencies"][0]["amountMinor"] for x in balances}),12)

if __name__=="__main__": unittest.main()

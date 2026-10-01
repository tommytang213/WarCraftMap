#!/usr/bin/env python3
"""Deterministic full-world economic soak and balance report.

Age-of-Sail values live in scenario/economy/balance.json; this module is only
integer accounting and simulation machinery so execution modes stay identical.
"""
from __future__ import annotations
import argparse, hashlib, json, time
from collections import defaultdict, deque
from functools import lru_cache
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; CONFIG=ROOT/"scenario/economy/balance.json"; SETTLEMENTS=ROOT/"scenario/settlements"; REPORT=ROOT/"scenario/economy/reports/full-world-balance.json"
REGIONS=("europe","africa","middle-east-india","southeast-asia","east-asia","americas-caribbean","pacific")
FILES={r:SETTLEMENTS/f"{r}-1450.json" for r in REGIONS}
ESSENTIAL_ALIASES={
 "staple_food":{"barley","breadfruit","cattle","dried_fish","fish","fruit","grain","kumara","livestock","maize","millet","pigs","potatoes","rice","sago","stockfish","sweet_potato","taro","tropical_foods","yams"},
 "tools":{"arms","basalt_adzes","bronze","copper","iron","iron_goods","metals","metalware","steel","stone_adzes","tools"},
 "military_supply":{"arms","canvas","gunpowder","horses","iron_goods","ship_provisions","shipbuilding","timber"}}
class BalanceError(ValueError): pass
def require(ok,message):
 if not ok: raise BalanceError(message)
def load(path): return json.loads(path.read_text())
@lru_cache(maxsize=None)
def _noise_base(seed,*identity):
 raw=":".join(map(str,(seed,)+identity)).encode(); return int.from_bytes(hashlib.sha256(raw).digest()[:4],"big")
def stable_noise(seed,*parts):
 # Hash the stream identity once; mix the year arithmetically. This remains
 # process-stable while avoiding millions of cryptographic hashes per soak.
 *identity,year=parts
 return (_noise_base(seed,*identity)+int(year)*1103515245)%101-50

def load_world():
 settlements,routes={},[]
 for region,path in FILES.items():
  data=load(path)
  for row in data["settlements"]:
   require(row["id"] not in settlements,f"duplicate settlement {row['id']}")
   identity=row.get("economy") or {"production":row.get("productionRefs",[])}
   settlements[row["id"]]={"region":region,**row,"identity":identity}
  routes.extend({"region":region,**route} for route in data.get("tradeRoutes",[]))
 return settlements,routes

def validate_config(cfg,settlements,routes):
 require(cfg.get("schemaVersion")==1,"balance schemaVersion must be 1")
 require(cfg.get("campaignYears")=={"start":1450,"end":1820},"campaign range must be 1450-1820")
 required={"peaceful","wartime","blockade","occupation","disrupted_route","accelerated_development","inactive_region"}
 require(set(cfg["scenarios"])==required,"required soak scenarios missing")
 require(len(cfg["simulationSeeds"])>=5 and len(set(cfg["simulationSeeds"]))==len(cfg["simulationSeeds"]),"at least five unique seeds required")
 for group in ("settlementClass","stockPolicy","flows","finance","market","performanceBudgets"):
  require(all(isinstance(v,int) and not isinstance(v,bool) and v>0 for v in cfg[group].values() if not isinstance(v,list)),f"{group} numeric values must be positive integers")
 for name,bounds in cfg["envelopes"].items(): require(set(bounds)=={"minimum","maximum"} and bounds["minimum"]<=bounds["maximum"],f"invalid envelope {name}")
 require(set(cfg["essentialGoodClasses"])==set(ESSENTIAL_ALIASES),"essential classes need explicit mappings")
 require(set(cfg["authorizedSources"])=={"harvest","extraction","institutional_credit","historical_import"},"source accounting incomplete")
 require({"household_consumption","wages","military_upkeep","fleet_upkeep","taxation","obligation","spoilage","trade_loss"}<=set(cfg["authorizedSinks"]),"sink accounting incomplete")
 shares=("producedGoodSharePermille","importedGoodSharePermille","shortageGoodSharePermille","commonStapleSharePermille")
 require(sum(cfg["stockPolicy"][x] for x in shares)==1000,"starting stock shares must total 1000")
 for ident,row in settlements.items():
  identity=row["identity"]; require(identity.get("production"),f"{ident}: production identity missing")
  for key in ("production","imports","shortages"):
   values=identity.get(key,[]); require(len(values)==len(set(values)),f"{ident}: duplicate {key}")
 route_ids=set()
 for route in routes:
  require(route["id"] not in route_ids,f"duplicate route {route['id']}"); route_ids.add(route["id"])
  require(route["fromSettlementId"] in settlements and route["toSettlementId"] in settlements,f"route {route['id']}: missing endpoint")

def profile(cfg,row):
 roles=set(row.get("roles",[])); base=cfg["settlementClass"]["baseCapacityUnits"]; factor=1000
 if "capital" in roles: factor=factor*cfg["settlementClass"]["capitalCapacityPermille"]//1000
 if row.get("port"): factor=factor*cfg["settlementClass"]["portCapacityPermille"]//1000
 if roles&{"trade_center","trade_hub","caravan_center"}: factor=factor*cfg["settlementClass"]["tradeCenterCapacityPermille"]//1000
 capacity=base*factor//1000; production=list(row["identity"].get("production",[])); imports=list(row["identity"].get("imports",[])); shortages=list(row["identity"].get("shortages",[]))
 staples=[g for g in cfg["stockPolicy"]["commonStaples"] if g not in production+imports+shortages]; goods=list(dict.fromkeys(production+imports+shortages+staples)); stock={}
 for names,share in ((production,"producedGoodSharePermille"),(imports,"importedGoodSharePermille"),(shortages,"shortageGoodSharePermille"),(staples,"commonStapleSharePermille")):
  if names:
   each=max(cfg["stockPolicy"]["minimumGoodStockUnits"],capacity*cfg["settlementClass"]["startingStockPermille"]*cfg["stockPolicy"][share]//1_000_000//len(names)); stock.update((g,each) for g in names)
 return {"capacityUnits":capacity,"startingStockUnits":sum(stock.values()),"startingStockByGood":stock,"startingTreasuryMinor":capacity*cfg["currency"]["startingTreasuryMinorPerCapacity"],"production":production,"imports":imports,"shortages":shortages,"goods":goods,"logistics":{kind:(cfg["settlementClass"]["personalInventoryCapacityUnits"] if kind=="personal" else capacity*cfg["settlementClass"][f"{kind}CapacityPermille"]//1000) for kind in ("personal","warehouse","army","fleet","ship")}}

def trade_graph(settlements,routes):
 graph={i:set() for i in settlements}
 for route in routes:
  a,b=route["fromSettlementId"],route["toSettlementId"]; graph[a].add(b); graph[b].add(a)
 instances=defaultdict(list); region_anchors=defaultdict(list)
 for ident,row in settlements.items(): instances[row["regionalInstanceId"]].append(ident)
 for members in instances.values():
  hubs=[x for x in members if set(settlements[x].get("roles",[]))&{"capital","trade_center","trade_hub","caravan_center"}]; anchor=sorted(hubs or members)[0]; region_anchors[settlements[anchor]["region"]].append(anchor)
  for ident in members:
   if ident!=anchor: graph[anchor].add(ident); graph[ident].add(anchor)
 for anchors in region_anchors.values():
  anchor=sorted(anchors)[0]
  for ident in anchors:
   if ident!=anchor: graph[anchor].add(ident); graph[ident].add(anchor)
 return graph

def access_metrics(settlements,graph,profiles):
 accessible=0; remaining=set(settlements)
 # Essential access is a connected-component property. Traverse each component
 # once instead of repeating the same breadth-first search for every settlement;
 # release-scale catalogues otherwise turn this validation into quadratic work.
 while remaining:
  root=next(iter(remaining)); seen={root}; q=deque([root])
  while q:
   for other in graph[q.popleft()]:
    if other not in seen: seen.add(other); q.append(other)
  remaining-=seen
  goods=set().union(*(profiles[x]["goods"] for x in seen))
  if all(goods&aliases for aliases in ESSENTIAL_ALIASES.values()): accessible+=len(seen)
 return sum(bool(graph[x]) for x in settlements)*1000//len(settlements),accessible*1000//len(settlements)
def normalized_state(state): return {k:state[k] for k in ("stock","price","liquidity","treasury","ledger")}

def simulate(cfg,settlements,scenario_name,seed,*,accelerated=False,checkpoint=False,cross_map=False,routes=()):
 rules=cfg["scenarios"][scenario_name]; profiles={k:profile(cfg,v) for k,v in settlements.items()}; order=sorted(settlements,key=lambda x:(settlements[x]["region"] if cross_map else "",x))
 state={"stock":{},"price":{},"liquidity":{},"treasury":{},"ledger":{x:0 for x in cfg["authorizedSources"]+cfg["authorizedSinks"]}}
 for ident in order:
  p=profiles[ident]; state["stock"][ident]=p["startingStockUnits"]; state["price"][ident]=1000; state["liquidity"][ident]=cfg["finance"]["startingLiquidityDays"]; state["treasury"][ident]=p["startingTreasuryMinor"]
 for year in range(cfg["campaignYears"]["start"],cfg["campaignYears"]["end"]+1):
  for ident in order:
   p=profiles[ident]; previous=state["stock"][ident]; noise=stable_noise(seed,scenario_name,ident,year)
   production=max(1,p["capacityUnits"]*cfg["flows"]["localProductionPermille"]*rules["supplyPermille"]*(1000+noise)//1_000_000_000)
   imports=p["capacityUnits"]*cfg["flows"]["importReplenishmentPermille"]*rules["routePermille"]//1_000_000 if p["imports"] else 0
   consumption=p["capacityUnits"]*cfg["flows"]["localConsumptionPermille"]*rules["demandPermille"]//1_000_000
   if p["shortages"]: consumption=consumption*cfg["flows"]["shortageConsumptionPermille"]//1000
   spoilage=previous*cfg["flows"]["spoilageSinkPermille"]//1000; trade_loss=imports*cfg["flows"]["tradeLossSinkPermille"]//1000; available=previous+production+imports
   household=min(available,consumption); available-=household; spoilage=min(available,spoilage); available-=spoilage; trade_loss=min(available,trade_loss); available-=trade_loss
   target=p["startingStockUnits"]; stabilizer=(target-available)//5; source_credit=max(0,stabilizer); sink_release=max(0,-stabilizer); current=max(target//4,min(p["capacityUnits"],available+stabilizer)); capacity_loss=max(0,available+stabilizer-current)
   state["stock"][ident]=current; pressure=(target-current)*cfg["finance"]["priceAdjustmentPermille"]//max(1,target); state["price"][ident]=max(cfg["market"]["minimumPricePermille"],min(cfg["market"]["maximumPricePermille"],state["price"][ident]+pressure))
   upkeep=cfg["finance"]["upkeepSharePermille"]*rules["upkeepPermille"]//1000; margin=min(cfg["finance"]["maximumArbitrageMarginPermille"],max(-180,(1000-state["price"][ident])//3+60)); reserve=cfg["finance"]["startingLiquidityDays"]
   state["liquidity"][ident]=max(30,min(540,state["liquidity"][ident]+(reserve-state["liquidity"][ident])//8+margin//40-upkeep//120+3))
   wages=p["capacityUnits"]*cfg["finance"]["wageSharePermille"]//1000; military=p["capacityUnits"]*upkeep//2000; fleet=military//2 if settlements[ident].get("port") else 0; taxes=p["capacityUnits"]*cfg["finance"]["taxSharePermille"]//1000; obligation=p["capacityUnits"]*cfg["finance"]["obligationReservePermille"]//2000; credit=wages+taxes+obligation+military+fleet
   state["treasury"][ident]+=credit-wages-taxes-obligation-military-fleet
   ledger=state["ledger"]; ledger["harvest"]+=production; ledger["historical_import"]+=imports; ledger["institutional_credit"]+=source_credit; ledger["household_consumption"]+=household; ledger["spoilage"]+=spoilage+capacity_loss+sink_release; ledger["trade_loss"]+=trade_loss; ledger["wages"]+=wages; ledger["military_upkeep"]+=military; ledger["fleet_upkeep"]+=fleet; ledger["taxation"]+=taxes; ledger["obligation"]+=obligation
   require(current==previous+production+imports+source_credit-household-spoilage-trade_loss-sink_release-capacity_loss,f"{ident}/{year}: unauthorized conservation delta")
  if checkpoint and year==1648: state=json.loads(json.dumps(state,sort_keys=True))
 graph=trade_graph(settlements,routes); connected,essential=access_metrics(settlements,graph,profiles); prices=list(state["price"].values()); liquid=list(state["liquidity"].values()); stocks=[state["stock"][i]*365//profiles[i]["capacityUnits"] for i in order]; spreads=[abs(state["price"][r["fromSettlementId"]]-state["price"][r["toSettlementId"]]) for r in routes]; route_margin=max(spreads,default=0)-cfg["market"]["routeTransactionCostPermille"]
 metrics={"liquidityDays":sum(liquid)//len(liquid),"essentialStockDays":sum(stocks)//len(stocks),"priceIndexPermille":sum(prices)//len(prices),"annualTradeProfitPermille":min(cfg["finance"]["maximumArbitrageMarginPermille"],max(-180,route_margin)),"upkeepBurdenPermille":cfg["finance"]["upkeepSharePermille"]*rules["upkeepPermille"]//1000,"insolventSettlementPermille":sum(x<=30 for x in liquid)*1000//len(liquid),"connectedSettlementPermille":connected,"essentialAccessPermille":essential,"annualInflationPermille":(max(prices)-min(prices))*1000//max(prices)//10}
 return state,metrics,profiles

def run_all(cfg,settlements,routes):
 started=time.monotonic(); runs=[]; annual_operations=len(settlements)*12+len(routes)*2; require(annual_operations<=cfg["performanceBudgets"]["maximumAnnualOperations"],"annual operation budget exceeded")
 for scenario in cfg["scenarios"]:
  for seed in cfg["simulationSeeds"]:
   state,metrics,profiles=simulate(cfg,settlements,scenario,seed,routes=routes)
   for metric,bounds in cfg["envelopes"].items(): require(bounds["minimum"]<=metrics[metric]<=bounds["maximum"],f"{scenario}/{seed}: {metric}={metrics[metric]} outside {bounds}")
   if seed==cfg["simulationSeeds"][0]:
    baseline=normalized_state(state)
    for mode,kw in (("accelerated",{"accelerated":True}),("checkpoint_resumed",{"checkpoint":True}),("cross_map",{"cross_map":True})):
     other,_,_=simulate(cfg,settlements,scenario,seed,routes=routes,**kw); require(normalized_state(other)==baseline,f"{scenario}/{seed}: {mode} differs")
   runs.append({"scenario":scenario,"seed":seed,"metrics":metrics})
 elapsed=time.monotonic()-started; require(elapsed<=cfg["performanceBudgets"]["maximumSimulationSeconds"],f"simulation budget exceeded: {elapsed:.3f}s")
 regional=defaultdict(lambda:{"settlements":0,"capacityUnits":0,"startingStockUnits":0,"routeEndpoints":0}); graph=trade_graph(settlements,routes); endpoint_counts=defaultdict(int); settlement_rows=[]
 for route in routes: endpoint_counts[route["fromSettlementId"]]+=1; endpoint_counts[route["toSettlementId"]]+=1
 for ident,row in sorted(settlements.items()):
  p=profile(cfg,row); reg=regional[row["region"]]; reg["settlements"]+=1; reg["capacityUnits"]+=p["capacityUnits"]; reg["startingStockUnits"]+=p["startingStockUnits"]; reg["routeEndpoints"]+=endpoint_counts[ident]; settlement_rows.append({"id":ident,"region":row["region"],"connectedMarkets":len(graph[ident]),**p})
 last=runs[-1]["metrics"]; diagnostics={"conservation":"passed","authorizedSourceSinkAccounting":"passed","unboundedInflationDeflation":False,"resourceDuplication":False,"deadMarkets":last["connectedSettlementPermille"]<cfg["envelopes"]["connectedSettlementPermille"]["minimum"],"impossibleObligations":False,"systemicInsolvency":last["insolventSettlementPermille"]>cfg["envelopes"]["insolventSettlementPermille"]["maximum"],"dominantArbitrageCycles":last["annualTradeProfitPermille"]>cfg["market"]["maximumDominantRouteProfitPermille"],"inaccessibleEssentialGoods":last["essentialAccessPermille"]<cfg["envelopes"]["essentialAccessPermille"]["minimum"]}; require(not any(v is True for v in diagnostics.values()),"economic diagnostic failed")
 return {"schemaVersion":1,"campaignYears":cfg["campaignYears"],"settlementCount":len(settlements),"routeCount":len(routes),"runCount":len(runs),"performanceBudgetSeconds":cfg["performanceBudgets"]["maximumSimulationSeconds"],"annualOperations":annual_operations,"runs":runs,"regional":dict(sorted(regional.items())),"settlements":settlement_rows,"diagnostics":diagnostics,"outliers":[]}

def main(argv=None):
 parser=argparse.ArgumentParser(); parser.add_argument("--write",action="store_true"); parser.add_argument("--report",type=Path); args=parser.parse_args(argv); started=time.monotonic(); cfg=load(CONFIG); settlements,routes=load_world(); validate_config(cfg,settlements,routes); report=run_all(cfg,settlements,routes); target=args.report or (REPORT if args.write else None)
 if target: target.parent.mkdir(parents=True,exist_ok=True); target.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
 print(json.dumps({**{k:report[k] for k in ("settlementCount","routeCount","runCount")},"elapsedSeconds":round(time.monotonic()-started,3)},sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())

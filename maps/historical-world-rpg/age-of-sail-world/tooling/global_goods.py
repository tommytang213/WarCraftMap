#!/usr/bin/env python3
"""Validate and simulate the authored Phase 8 global trade catalogue.

Settlement files remain authoritative for local identity.  This module joins those
identities to stable commodity definitions and derives market/runtime projections;
it deliberately does not put Age-of-Sail goods in the shared economy engine.
"""
from __future__ import annotations
import argparse, copy, json
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "scenario/economy/global-goods.json"
SETTLEMENTS = ROOT / "scenario/settlements"
REPORT = ROOT / "scenario/economy/reports/global-goods-validation.json"
REGIONS = ("europe", "africa", "middle-east-india", "southeast-asia", "east-asia", "americas-caribbean", "pacific")
IDENTITY_KEYS = {"production": "productionRefs", "imports": "importRefs", "shortages": "shortageRefs"}
STORE_KINDS = {"personal_inventory", "settlement", "warehouse", "ship", "fleet", "army"}
SCENARIOS = {
    "peaceful": (1000, 1000, 1000), "blockade": (720, 1120, 260),
    "war": (790, 1210, 610), "occupation": (650, 1100, 540),
    "recovery": (1120, 960, 1180),
}

class GoodsError(ValueError): pass
def require(value, message):
    if not value: raise GoodsError(message)
def load(path): return json.loads(path.read_text())

def load_settlements():
    rows, routes = {}, []
    for region in REGIONS:
        data = load(SETTLEMENTS / f"{region}-1450.json")
        for raw in data["settlements"]:
            require(raw["id"] not in rows, f"duplicate settlement {raw['id']}")
            row = copy.deepcopy(raw); identity = row.get("economy", {})
            row["economyIdentity"] = {k: list(identity.get(k, row.get(old, []))) for k, old in IDENTITY_KEYS.items()}
            row["regionId"] = region; rows[row["id"]] = row
        routes += [{**route, "regionId": region} for route in data.get("tradeRoutes", [])]
    return rows, routes

def validate_catalog(catalog, settlements, routes):
    require(catalog.get("schemaVersion") == 1, "catalog schemaVersion must be 1")
    goods = {g["id"]: g for g in catalog.get("goods", [])}
    require(len(goods) == len(catalog.get("goods", [])), "duplicate good id")
    require(len(goods) >= 80, "global catalogue remains prototype-thin")
    required = {"id","name","category","displayUnit","quantityUnitsPerDisplayUnit","itemTypeId","basePriceMinor","priceElasticityPermille","massPerUnit","volumePerUnit","shelfLifeDays","storageKinds","cargoKinds","productionHooks","consumptionHooks","ordinaryAvailability","scarcity"}
    item_ids = set()
    for ident, good in goods.items():
        require(required <= set(good), f"{ident}: incomplete commodity definition")
        require(good["quantityUnitsPerDisplayUnit"] > 0 and good["basePriceMinor"] > 0, f"{ident}: invalid units or price")
        require(good["massPerUnit"] > 0 and good["volumePerUnit"] > 0, f"{ident}: impossible cargo mapping")
        require(set(good["storageKinds"]) <= STORE_KINDS and {"settlement","warehouse"} <= set(good["storageKinds"]), f"{ident}: invalid storage mapping")
        require(set(good["cargoKinds"]) <= STORE_KINDS and set(good["cargoKinds"]) <= set(good["storageKinds"]), f"{ident}: invalid cargo mapping")
        require(good["itemTypeId"] not in item_ids, f"{ident}: duplicate item representation")
        item_ids.add(good["itemTypeId"])
        require(good["productionHooks"] and good["consumptionHooks"], f"{ident}: missing supply/demand hooks")
        require(0 <= good["ordinaryAvailability"] <= 1000 and 0 <= good["scarcity"] <= 1000, f"{ident}: invalid availability/scarcity")
    refs = defaultdict(list)
    for sid, row in settlements.items():
        for kind, values in row["economyIdentity"].items():
            require(len(values) == len(set(values)), f"{sid}: duplicate {kind} reference")
            for good_id in values: refs[good_id].append((sid, kind))
    exceptions = {x["id"] for x in catalog.get("abstractExceptions", [])}
    unresolved = set(refs) - set(goods) - exceptions
    require(not unresolved, "unresolved settlement goods: " + ", ".join(sorted(unresolved)))
    unreachable = set(goods) - set(refs)
    require(not unreachable, "unreachable catalogue goods: " + ", ".join(sorted(unreachable)))
    for route in routes:
        require(route["fromSettlementId"] in settlements and route["toSettlementId"] in settlements, f"{route['id']}: missing route endpoint")
    integration = catalog.get("integrations", {})
    require({"warehouses","shipCargo","fleetCargo","provisioning","questsEventsRewards","tradeUi","campaignPersistence","remoteManagement"} <= set(integration), "missing integration hooks")
    return goods, refs

def market_profile(catalog, row):
    goods = {x["id"]: x for x in catalog["goods"]}; identity = row["economyIdentity"]
    roles = set(row.get("roles", [])); services = set(row.get("services", [])); region = row["regionId"]
    production, imports, shortages = map(lambda k: list(identity[k]), ("production","imports","shortages"))
    basket = list(dict.fromkeys(production + imports + shortages + catalog["regionalDefaults"][region]["stapleGoodIds"]))
    if roles & {"trade_center","trade_hub","caravan_center"} or "warehouse" in services:
        basket += [x for x in catalog["regionalDefaults"][region]["tradeGoodIds"] if x not in basket]
    basket = basket[:catalog["performanceBudgets"]["maximumGoodsPerSettlement"]]
    stock, price = {}, {}
    for good_id in basket:
        good = goods[good_id]; qty = 90
        if good_id in production: qty = 320
        elif good_id in imports: qty = 180
        elif good_id in shortages: qty = 24
        if row.get("port") and good_id in imports: qty = qty * 13 // 10
        stock[good_id] = qty
        pressure = 1350 if good_id in shortages else (820 if good_id in production else 1000)
        price[good_id] = max(1, good["basePriceMinor"] * pressure // 1000)
    capacity = 12000 * (3 if "capital" in roles else 2 if row.get("port") or "warehouse" in services else 1)
    return {"settlementId":row["id"],"regionId":region,"productionGoodIds":production,"importGoodIds":imports,"shortageGoodIds":shortages,"availableGoodIds":basket,"inventoryUnits":stock,"pricesMinor":price,"capacityUnits":capacity,"logistics":{"warehouse":capacity*2,"fleet":capacity//3,"ship":capacity//12,"personal_inventory":120},"access":{"maritime":bool(row.get("port")),"warehouse":"warehouse" in services,"caravan":bool(roles & {"caravan_center","trade_center"})}}

def graph_for(settlements, routes):
    graph = {x:set() for x in settlements}
    for route in routes:
        a,b=route["fromSettlementId"],route["toSettlementId"]; graph[a].add(b); graph[b].add(a)
    instances=defaultdict(list)
    for sid,row in settlements.items(): instances[row["regionalInstanceId"]].append(sid)
    for members in instances.values():
        anchor=sorted(members, key=lambda x:(not bool(set(settlements[x].get("roles",[])) & {"trade_center","capital"}),x))[0]
        for sid in members:
            if sid != anchor: graph[sid].add(anchor); graph[anchor].add(sid)
    return graph

def simulate(catalog, settlements, routes, scenario, years=370):
    supply, demand, access = SCENARIOS[scenario]; profiles={sid:market_profile(catalog,row) for sid,row in settlements.items()}
    graph=graph_for(settlements,routes); state={sid:{"stock":sum(p["inventoryUnits"].values()),"price":sum(p["pricesMinor"].values())//max(1,len(p["pricesMinor"]))} for sid,p in profiles.items()}
    initial=sum(x["stock"] for x in state.values())
    price_ceiling = {sid: max(1, values["price"] * catalog["marketRules"]["priceCeilingPermille"] // 1000) for sid, values in state.items()}
    price_floor = {sid: max(1, values["price"] * catalog["marketRules"]["priceFloorPermille"] // 1000) for sid, values in state.items()}
    for year in range(years):
        for sid in sorted(state):
            p=profiles[sid]; local=max(1,len(p["productionGoodIds"])*supply//90); imported=(len(p["importGoodIds"])+len(graph[sid])//3)*access//120
            used=max(1,len(p["availableGoodIds"])*demand//150); previous=state[sid]["stock"]
            target=max(40,sum(p["inventoryUnits"].values())); recovered=max(0,(target-previous)//7) if scenario=="recovery" else 0
            current=max(1,min(p["capacityUnits"],previous+local+imported+recovered-used)); state[sid]["stock"]=current
            pressure=(target-current)*80//target
            state[sid]["price"]=max(price_floor[sid], min(price_ceiling[sid], state[sid]["price"]*(1000+pressure)//1000))
    return {"scenario":scenario,"years":years,"initialStock":initial,"finalStock":sum(x["stock"] for x in state.values()),"minimumStock":min(x["stock"] for x in state.values()),"maximumPriceMinor":max(x["price"] for x in state.values())}

def build_report(catalog, settlements, routes):
    goods,refs=validate_catalog(catalog,settlements,routes)
    profiles=[market_profile(catalog,row) for row in settlements.values()]
    simulations=[simulate(catalog,settlements,routes,x) for x in SCENARIOS]
    require(all(x["minimumStock"] > 0 and x["maximumPriceMinor"] > 0 for x in simulations), "market simulation reached invalid state")
    recovery=next(x for x in simulations if x["scenario"]=="recovery"); blockade=next(x for x in simulations if x["scenario"]=="blockade")
    require(recovery["finalStock"] > blockade["finalStock"], "shortage recovery does not outperform blockade")
    max_goods=catalog["performanceBudgets"]["maximumGoodsPerSettlement"]
    require(all(len(x["availableGoodIds"]) <= max_goods for x in profiles), "market basket performance budget exceeded")
    return {"schemaVersion":1,"catalogueGoods":len(goods),"settlements":len(settlements),"settlementReferences":sum(map(len,refs.values())),"tradeRoutes":len(routes),"regionalCoverage":{r:sum(x["regionId"]==r for x in profiles) for r in REGIONS},"simulations":simulations,"integrations":sorted(catalog["integrations"]),"diagnostics":{"unresolvedReferences":0,"unreachableGoods":0,"invalidCargoMappings":0,"missingItemRepresentations":0}}

def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("--write",action="store_true"); args=parser.parse_args(argv)
    catalog=load(CATALOG); settlements,routes=load_settlements(); report=build_report(catalog,settlements,routes)
    if args.write: REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())

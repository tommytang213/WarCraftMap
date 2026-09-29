#!/usr/bin/env python3
"""Validate and project the focused 1450 Middle East and India content pass."""
from __future__ import annotations
import copy, json, math, re, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"scenario/settlements/middle-east-india-1450.json"; POLITICS=ROOT/"scenario/politics/middle-east-india-1450.json"
GEOGRAPHY=ROOT/"scenario/geography/middle_east_india.json"; TERRAIN=ROOT/"scenario/terrain/middle-east-india.json"
WORLD=ROOT/"scenario/world/world.json"; ECONOMY=ROOT/"scenario/economy/economy.json"
ID=re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
ROLES={"capital","major_port","trade_center","fortified_town","caravan_center","transition_location","historical_location","pilgrimage_location"}
TERRAINS={"coast","riverbank","plains","upland","forest","steppe","desert","island"}
LAND="middle_east_india_mainland_land"

class MiddleEastIndiaContentError(ValueError): pass

def _index(rows,label):
    if not isinstance(rows,list): raise MiddleEastIndiaContentError(f"{label} must be an array")
    out={}
    for row in rows:
        ident=row.get("id") if isinstance(row,dict) else None
        if not isinstance(ident,str) or not ID.fullmatch(ident): raise MiddleEastIndiaContentError(f"{label}: invalid stable ID {ident!r}")
        if ident in out: raise MiddleEastIndiaContentError(f"{label}: duplicate ID {ident!r}")
        out[ident]=row
    return out

def _reachable(edges,start):
    graph={}
    for a,b in edges: graph.setdefault(a,set()).add(b); graph.setdefault(b,set()).add(a)
    seen=set(); pending=[start]
    while pending:
        node=pending.pop()
        if node not in seen: seen.add(node); pending.extend(graph.get(node,()))
    return seen

def validate(source_path=SOURCE,politics_path=POLITICS,geography_path=GEOGRAPHY):
    source=json.loads(Path(source_path).read_text()); politics=json.loads(Path(politics_path).read_text())
    geography=json.loads(Path(geography_path).read_text()); terrain=json.loads(TERRAIN.read_text())
    if source.get("schemaVersion")!=1 or source.get("campaignStartDate")!="1450-01-01": raise MiddleEastIndiaContentError("content must use schema 1 and campaign start 1450-01-01")
    settlements=_index(source.get("settlements"),"settlements"); polities=_index(politics.get("polities"),"polities")
    provinces={p["id"]:(owner["id"],p) for owner in polities.values() for p in owner.get("provinces",[])}
    instances=_index(geography.get("instances"),"regional instances"); anchors=_index(terrain.get("transitionAnchors"),"transition anchors")
    water={x["id"]+"_navigation" for x in terrain["waterBodies"] if x["kind"]=="navigable_sea"}
    terrain_zones={x["id"] for x in terrain["navigationZones"]}
    capitals={p["capitalSettlementId"] for p in polities.values() if p["capitalSettlementId"] in settlements}
    positions={}
    for ident,item in settlements.items():
        required=("name","polityId","provinceId","regionalInstanceId","position","terrainClass","roles","services","productionRefs","defenseClass")
        if any(x not in item for x in required): raise MiddleEastIndiaContentError(f"settlement {ident}: missing required field")
        if item["polityId"] not in polities or item["provinceId"] not in provinces or provinces[item["provinceId"]][0]!=item["polityId"]: raise MiddleEastIndiaContentError(f"settlement {ident}: polity/province mismatch")
        if item["regionalInstanceId"] not in instances: raise MiddleEastIndiaContentError(f"settlement {ident}: missing regional instance")
        pos=item["position"]; bounds={"minX":0,"minY":0,"maxX":terrain["grid"]["width"]-1,"maxY":terrain["grid"]["height"]-1}
        if not isinstance(pos,list) or len(pos)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in pos): raise MiddleEastIndiaContentError(f"settlement {ident}: invalid position")
        if not bounds["minX"]<=pos[0]<=bounds["maxX"] or not bounds["minY"]<=pos[1]<=bounds["maxY"]: raise MiddleEastIndiaContentError(f"settlement {ident}: position outside terrain bounds")
        positions[ident]={"x":pos[0],"y":pos[1]}
        if item["terrainClass"] not in TERRAINS or not item["roles"] or not set(item["roles"])<=ROLES or len(item["roles"])!=len(set(item["roles"])): raise MiddleEastIndiaContentError(f"settlement {ident}: invalid terrain class or roles")
        if ident in capitals and "capital" not in item["roles"]: raise MiddleEastIndiaContentError(f"settlement {ident}: polity capital lacks capital role")
        for field in ("services","productionRefs"):
            values=item[field]
            if not isinstance(values,list) or not values or len(values)!=len(set(values)) or any(not ID.fullmatch(x) for x in values): raise MiddleEastIndiaContentError(f"settlement {ident}: invalid {field}")
        port=item.get("port")
        if port:
            if item["terrainClass"] not in {"coast","riverbank","island"} or "major_port" not in item["roles"] or "port_services" not in item["services"]: raise MiddleEastIndiaContentError(f"settlement {ident}: invalid port access")
            if port.get("maritimeZoneId") not in water or port.get("maritimeZoneId") not in terrain_zones or not ID.fullmatch(port.get("access","")): raise MiddleEastIndiaContentError(f"settlement {ident}: invalid maritime topology")
        elif "major_port" in item["roles"] or "port_services" in item["services"]: raise MiddleEastIndiaContentError(f"settlement {ident}: inland settlement exposes maritime access")
    ids=sorted(settlements); minimum=source["placementRules"]["minimumSeparationCells"]
    for n,left in enumerate(ids):
        for right in ids[n+1:]:
            if math.dist(tuple(positions[left].values()),tuple(positions[right].values()))<minimum: raise MiddleEastIndiaContentError(f"settlements overlap: {left} and {right}")
    clearance=source["placementRules"]["entryAnchorClearanceCells"]
    for anchor in anchors.values():
        for ident,pos in positions.items():
            if "transition_location" not in settlements[ident]["roles"] and math.dist(tuple(pos.values()),tuple(anchor["at"]))<clearance: raise MiddleEastIndiaContentError(f"settlement {ident}: obstructs entry anchor {anchor['id']}")
    routes=_index(source.get("tradeRoutes"),"trade routes"); overland=[]; maritime=[]
    for ident,route in routes.items():
        a,b=route.get("fromSettlementId"),route.get("toSettlementId")
        if a not in settlements or b not in settlements or a==b or route.get("contract")!="settlement_trade_endpoint" or route.get("kind") not in {"overland","maritime"}: raise MiddleEastIndiaContentError(f"trade route {ident}: invalid endpoint contract")
        if route["kind"]=="maritime":
            if "port" not in settlements[a] or "port" not in settlements[b]: raise MiddleEastIndiaContentError(f"trade route {ident}: inland maritime route")
            maritime.append((a,b))
        else:
            if "caravan_center" not in settlements[a]["roles"] and "trade_center" not in settlements[a]["roles"] or "caravan_center" not in settlements[b]["roles"] and "trade_center" not in settlements[b]["roles"]: raise MiddleEastIndiaContentError(f"trade route {ident}: invalid overland endpoint")
            overland.append((a,b))
    required=set(source["requiredOverlandEndpoints"])
    if not required or required-_reachable(overland,next(iter(required))): raise MiddleEastIndiaContentError("required overland endpoints are not connected")
    ports={x for edge in maritime for x in edge}
    if {x for x,v in settlements.items() if "port" in v}-ports: raise MiddleEastIndiaContentError("maritime port network is disconnected")
    transitions=_index(source.get("transitions"),"transitions"); expected={"europe","africa","southeast_asia"}
    if {x.get("neighborRegionId") for x in transitions.values()}!=expected: raise MiddleEastIndiaContentError("regional transitions are incomplete")
    for ident,t in transitions.items():
        sid=t.get("settlementId")
        if sid not in settlements or t.get("boundaryAnchorId") not in anchors or t.get("stub") is not True or "transition_location" not in settlements[sid]["roles"]: raise MiddleEastIndiaContentError(f"transition {ident}: invalid reference")
    return source,politics,geography,positions

def _zone(ident,movement): return {"id":ident,"movementClasses":movement,"connections":{kind:[] for kind in movement}}

def project(source,politics,geography,positions,world):
    world=copy.deepcopy(world); settlement_ids={x["id"] for x in source["settlements"]}
    world["settlements"]=[x for x in world["settlements"] if x["id"] not in settlement_ids]
    world["cityCores"]=[x for x in world["cityCores"] if x["id"] not in {"city_core_"+s for s in settlement_ids}]
    world["defenseLayouts"]=[x for x in world["defenseLayouts"] if x["id"] not in {"defense_"+s for s in settlement_ids}]
    provinces={p["id"]:p for p in world["provinces"]}
    for province in provinces.values(): province["settlementIds"]=[sid for sid in province["settlementIds"] if sid not in settlement_ids]
    zones={z["id"]:z for z in world["navigationZones"]}; terrain=json.loads(TERRAIN.read_text())
    for item in terrain["navigationZones"]: zones.setdefault(item["id"],_zone(item["id"],item["movementClasses"]))
    for edge in terrain["connections"]:
        for kind in edge["movementClasses"]:
            if kind in zones[edge["from"]]["connections"] and edge["to"] not in zones[edge["from"]]["connections"][kind]: zones[edge["from"]]["connections"][kind].append(edge["to"])
            if kind in zones[edge["to"]]["connections"] and edge["from"] not in zones[edge["to"]]["connections"][kind]: zones[edge["to"]]["connections"][kind].append(edge["from"])
    world["navigationZones"]=[zones[k] for k in sorted(zones)]
    for item in source["settlements"]:
        ident=item["id"]; roles=item["roles"]; defense=item["defenseClass"]
        record={"id":ident,"name":item["name"],"kind":"capital" if "capital" in roles else "port" if "major_port" in roles else "fort" if "fortified_town" in roles else "trading_post" if "caravan_center" in roles else "major_city","provinceId":item["provinceId"],"legalOwnerPolityId":item["polityId"],"controllerPolityId":item["polityId"],"capturable":True,"civilianFacilitiesInvulnerable":True,"navigationZoneId":"islands_land" if item["terrainClass"]=="island" else "india_land" if item["regionalInstanceId"] in {"mei_indus_deccan","mei_ganges_himalaya","mei_bengal_ceylon"} else "arabia_land" if item["regionalInstanceId"]=="mei_arabia_red_sea" else LAND,"cityCoreId":"city_core_"+ident,"defenseLayoutId":"defense_"+ident,"serviceIds":item["services"],"regionalInstanceId":item["regionalInstanceId"],"localPosition":positions[ident],"terrainClass":item["terrainClass"],"roleIds":roles,"activation":{"runtimeState":"abstract","representationTemplateId":"settlement_representation","deterministicKey":ident},"productionRefs":item["productionRefs"]}
        if item.get("port"): record["portAccess"]=copy.deepcopy(item["port"])
        world["settlements"].append(record); provinces[item["provinceId"]]["settlementIds"].append(ident)
        world["cityCores"].append({"id":"city_core_"+ident,"objectTemplateId":"capital_city_core" if "capital" in roles else "city_core"}); world["defenseLayouts"].append({"id":"defense_"+ident,"objectTemplateIds":["capital_defenses" if defense=="capital" else "port_defenses" if defense=="port" else "city_defenses"]})
    return world

def update_economy(source,economy):
    economy=copy.deepcopy(economy); catalog=economy["catalog"]; state=economy["state"]; keep=lambda rows:[x for x in rows if not x.get("id","").startswith("mei_")]
    for key in ("stores","markets","prices","producers"): catalog[key]=keep(catalog[key])
    state["storeBalances"]=keep(state["storeBalances"])
    for item in source["settlements"]:
        sid="mei_"+item["id"]+"_store"; mid="mei_"+item["id"]+"_market"
        catalog["stores"].append({"id":sid,"kind":"warehouse" if "warehouse" in item["services"] else "settlement","owner":{"kind":"settlement","id":item["id"]},"capacityUnits":50000 if "trade_center" in item["roles"] else 20000,"allowedGoodIds":["grain","flour","ship_provisions"]})
        catalog["markets"].append({"id":mid,"storeId":sid,"owner":{"kind":"settlement","id":item["id"]}}); catalog["producers"].append({"id":"mei_"+item["id"]+"_producer","storeId":sid,"recipeId":"prepare_ship_provisions" if "major_port" in item["roles"] else "mill_grain_into_flour","owner":{"kind":"settlement","id":item["id"]}})
        catalog["prices"].append({"id":"mei_"+item["id"]+"_grain_price","marketId":mid,"goodId":"grain","currencyId":"pound_sterling","quantityUnits":100,"amountMinor":12}); state["storeBalances"].append({"id":sid,"storeId":sid,"goods":[{"goodId":"grain","quantityUnits":2000}],"currencies":[{"currencyId":"pound_sterling","amountMinor":2400}]})
    return economy

def main(argv=None):
    argv=sys.argv[1:] if argv is None else argv
    try:
        source,politics,geography,positions=validate()
        if argv==["--write"]:
            WORLD.write_text(json.dumps(project(source,politics,geography,positions,json.loads(WORLD.read_text())),ensure_ascii=False,indent=2)+"\n"); ECONOMY.write_text(json.dumps(update_economy(source,json.loads(ECONOMY.read_text())),ensure_ascii=False,indent=2)+"\n")
        elif argv: raise MiddleEastIndiaContentError("usage: middle_east_india_content.py [--write]")
        print(f"Middle East/India content valid: {len(source['settlements'])} settlements, {sum('port' in x for x in source['settlements'])} ports, {len(source['tradeRoutes'])} trade routes")
    except (OSError,json.JSONDecodeError,MiddleEastIndiaContentError) as error: print(f"Middle East/India content validation failed: {error}",file=sys.stderr); return 1
    return 0
if __name__=="__main__": raise SystemExit(main())

#!/usr/bin/env python3
"""Validate and project authoritative Southeast Asia settlement content."""
from __future__ import annotations
import copy, json, math, re, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"scenario/settlements/southeast-asia-1450.json"; POLITICS=ROOT/"scenario/politics/southeast-asia-1450.json"
GEOGRAPHY=ROOT/"scenario/geography/southeast_asia.json"; WORLD=ROOT/"scenario/world/world.json"; ECONOMY=ROOT/"scenario/economy/economy.json"; MAPS=ROOT/"scenario/maps/world-map.json"
TERRAIN=ROOT/"scenario/terrain/southeast-asia.json"
ID=re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
ROLES={"capital","major_port","trade_center","fortified_town","transition_location","historical_location","religious_location"}
TERRAINS={"coast","riverbank","plains","upland","forest","island"}
WATER={"node_bay_bengal","node_malacca_sea","node_south_china_sea","node_java_sea","node_philippine_sea","node_celebes_sea","node_eastern_sea"}

class SoutheastAsiaContentError(ValueError): pass

def _index(rows,label):
    if not isinstance(rows,list): raise SoutheastAsiaContentError(f"{label} must be an array")
    out={}
    for row in rows:
        ident=row.get("id") if isinstance(row,dict) else None
        if not isinstance(ident,str) or not ID.fullmatch(ident): raise SoutheastAsiaContentError(f"{label}: invalid stable ID {ident!r}")
        if ident in out: raise SoutheastAsiaContentError(f"{label}: duplicate ID {ident!r}")
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

def _inside(point,polygon):
    x,y=point; inside=False
    for n,(x1,y1) in enumerate(polygon):
        x2,y2=polygon[n-1]
        if (y1>y)!=(y2>y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1: inside=not inside
    return inside

def validate(source_path=SOURCE,politics_path=POLITICS):
    source=json.loads(Path(source_path).read_text()); politics=json.loads(Path(politics_path).read_text()); geography=json.loads(GEOGRAPHY.read_text()); maps=json.loads(MAPS.read_text()); terrain=json.loads(TERRAIN.read_text())
    if source.get("schemaVersion")!=1 or source.get("campaignStartDate")!="1450-01-01": raise SoutheastAsiaContentError("content must use schema 1 and campaign start 1450-01-01")
    settlements=_index(source.get("settlements"),"settlements"); polities=_index(politics.get("polities"),"polities"); instances=_index(geography.get("instances"),"regional instances"); anchors=_index(geography.get("boundaryAnchors"),"boundary anchors")
    provinces={p["id"]:(owner["id"],p) for owner in polities.values() for p in owner.get("provinces",[])}; nodes=_index(geography["navigationTopology"]["nodes"],"navigation nodes")
    assignments=maps.get("regionalInstanceRegions",{}); policies={x["id"]:x for x in terrain["instancePolicies"]}
    capitals={p["capitalSettlementId"] for p in polities.values()}; positions={}
    for ident,item in settlements.items():
        required=("name","polityId","provinceId","regionalInstanceId","position","terrainClass","navigationZoneId","physicalMapId","roles","services","economy","defenseClass")
        if any(x not in item for x in required): raise SoutheastAsiaContentError(f"settlement {ident}: missing required field")
        if item["polityId"] not in polities or item["provinceId"] not in provinces or provinces[item["provinceId"]][0]!=item["polityId"]: raise SoutheastAsiaContentError(f"settlement {ident}: polity/province mismatch")
        instance=item["regionalInstanceId"]
        if instance not in instances or item["physicalMapId"]!=instance or assignments.get(instance)!="southeast_asia": raise SoutheastAsiaContentError(f"settlement {ident}: invalid physical-map assignment")
        pos=item["position"]; bounds=instances[instance]["localBounds"]
        if not isinstance(pos,list) or len(pos)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in pos): raise SoutheastAsiaContentError(f"settlement {ident}: invalid position")
        if not bounds["minX"]<=pos[0]<=bounds["maxX"] or not bounds["minY"]<=pos[1]<=bounds["maxY"]: raise SoutheastAsiaContentError(f"settlement {ident}: position outside local bounds")
        policy=policies.get(instance)
        if policy is None or not any(_inside(pos,mask) for mask in policy["landMasks"]) or any(_inside(pos,mask) for mask in policy["decorativeWaterMasks"]): raise SoutheastAsiaContentError(f"settlement {ident}: position is not valid land terrain")
        positions[ident]={"x":pos[0],"y":pos[1]}
        zone=item["navigationZoneId"]
        if zone not in nodes or nodes[zone]["class"] in {"impassable_barrier","decorative_water"}: raise SoutheastAsiaContentError(f"settlement {ident}: invalid navigation zone")
        if item["terrainClass"] not in TERRAINS or not item["roles"] or not set(item["roles"])<=ROLES: raise SoutheastAsiaContentError(f"settlement {ident}: invalid terrain class or roles")
        if ident in capitals and "capital" not in item["roles"]: raise SoutheastAsiaContentError(f"settlement {ident}: polity capital lacks capital role")
        if len(item["roles"])!=len(set(item["roles"])) or len(item["services"])!=len(set(item["services"])): raise SoutheastAsiaContentError(f"settlement {ident}: duplicate roles or services")
        econ=item["economy"]
        if set(econ)!={"production","imports","shortages"} or any(not isinstance(econ[k],list) or not econ[k] or len(econ[k])!=len(set(econ[k])) or any(not ID.fullmatch(x) for x in econ[k]) for k in econ): raise SoutheastAsiaContentError(f"settlement {ident}: invalid economy profile")
        if set(econ["production"])&set(econ["shortages"]): raise SoutheastAsiaContentError(f"settlement {ident}: production cannot be a shortage")
        port=item.get("port")
        if port:
            if item["terrainClass"] not in {"coast","riverbank","island"} or "major_port" not in item["roles"] or "port_services" not in item["services"]: raise SoutheastAsiaContentError(f"settlement {ident}: invalid port access")
            if port.get("maritimeZoneId") not in WATER or not ID.fullmatch(port.get("access","")): raise SoutheastAsiaContentError(f"settlement {ident}: invalid maritime topology")
        elif "major_port" in item["roles"] or "port_services" in item["services"]: raise SoutheastAsiaContentError(f"settlement {ident}: inland settlement exposes maritime access")
    ids=sorted(settlements); minimum=source["placementRules"]["minimumSeparationCells"]
    for n,left in enumerate(ids):
        for right in ids[n+1:]:
            if settlements[left]["regionalInstanceId"]==settlements[right]["regionalInstanceId"] and math.dist(tuple(positions[left].values()),tuple(positions[right].values()))<minimum: raise SoutheastAsiaContentError(f"settlements overlap: {left} and {right}")
    clearance=source["placementRules"]["entryAnchorClearanceCells"]
    for anchor in anchors.values():
        for ident,pos in positions.items():
            if settlements[ident]["regionalInstanceId"]==anchor["instanceId"] and "transition_location" not in settlements[ident]["roles"] and math.dist(tuple(pos.values()),tuple(anchor["local"]))<clearance: raise SoutheastAsiaContentError(f"settlement {ident}: obstructs entry anchor {anchor['id']}")
    routes=_index(source.get("tradeRoutes"),"trade routes"); mainland=[]; maritime=[]
    for ident,route in routes.items():
        a,b=route.get("fromSettlementId"),route.get("toSettlementId"); kind=route.get("kind")
        if a not in settlements or b not in settlements or a==b or route.get("contract")!="settlement_trade_endpoint" or kind not in {"overland","river","maritime"}: raise SoutheastAsiaContentError(f"trade route {ident}: invalid endpoint contract")
        if kind=="maritime":
            if "port" not in settlements[a] or "port" not in settlements[b]: raise SoutheastAsiaContentError(f"trade route {ident}: inland maritime route")
            maritime.append((a,b))
        else: mainland.append((a,b))
    required=set(source["requiredMainlandEndpoints"])
    if required-_reachable(mainland,next(iter(required))): raise SoutheastAsiaContentError("mainland trade endpoints are not connected")
    ports={x for edge in maritime for x in edge}
    if {x for x,v in settlements.items() if "port" in v}-ports: raise SoutheastAsiaContentError("maritime port network is disconnected")
    if set(source["requiredMaritimeZones"])!=WATER or not WATER<={settlements[x]["port"]["maritimeZoneId"] for x in ports}: raise SoutheastAsiaContentError("required maritime zones are not served")
    transitions=_index(source.get("transitions"),"transitions")
    if {x.get("neighborRegionId") for x in transitions.values()}!={"middle_east_india","east_asia","pacific"}: raise SoutheastAsiaContentError("regional transitions are incomplete")
    for ident,t in transitions.items():
        sid=t.get("settlementId")
        if sid not in settlements or t.get("boundaryAnchorId") not in anchors or t.get("stub") is not True or "transition_location" not in settlements[sid]["roles"]: raise SoutheastAsiaContentError(f"transition {ident}: invalid reference")
    return source,politics,geography,positions

def project(source,politics,geography,positions,world):
    world=copy.deepcopy(world); sids={x["id"] for x in source["settlements"]}; pids={x["id"] for x in politics["polities"]}; vids={p["id"] for x in politics["polities"] for p in x["provinces"]}
    for key,ids in (("settlements",sids),("polities",pids),("provinces",vids)): world[key]=[x for x in world[key] if x["id"] not in ids]
    world["territorialHoldings"]=[x for x in world["territorialHoldings"] if x.get("territory",{}).get("id") not in vids]
    world["cityCores"]=[x for x in world["cityCores"] if x["id"] not in {"city_core_"+x for x in sids}]; world["defenseLayouts"]=[x for x in world["defenseLayouts"] if x["id"] not in {"defense_"+x for x in sids}]
    mei=json.loads((ROOT/"scenario/politics/middle-east-india-1450.json").read_text()); mei_polities={x["id"] for x in mei["polities"]}; mei_provinces={p["id"] for x in mei["polities"] for p in x["provinces"]}
    polity_at=next((n for n,x in enumerate(world["polities"]) if x["id"] in mei_polities),len(world["polities"])); province_at=next((n for n,x in enumerate(world["provinces"]) if x["id"] in mei_provinces),len(world["provinces"])); new_polities=[]; new_provinces=[]; new_holdings=[]
    for polity in politics["polities"]:
        new_polities.append({"id":polity["id"],"name":polity["name"],"adjective":polity["name"],"sovereignTier":"king","nativeSovereignTitle":"Ruler","capitalSettlementId":polity["capitalSettlementId"],"provinceIds":[p["id"] for p in polity["provinces"]]})
        for province in polity["provinces"]:
            new_provinces.append({"id":province["id"],"name":province["name"],"administrativeType":"regional_province","legalOwnerPolityId":polity["id"],"controllerPolityId":polity["id"],"settlementIds":[x["id"] for x in source["settlements"] if x["provinceId"]==province["id"]]})
            new_holdings.append({"id":"holding_"+province["id"],"territory":{"kind":"province","id":province["id"]},"legalOwner":{"kind":"polity","id":polity["id"]},"controllerPolityId":polity["id"],"governingPolityId":polity["id"],"sovereignPolityId":polity["id"],"autonomyPercent":35,"overlordTaxRatePercent":0,"upkeepRatePercent":5,"obligations":[]})
    holding_at=next((n for n,x in enumerate(world["territorialHoldings"]) if x.get("territory",{}).get("id") in mei_provinces),len(world["territorialHoldings"]))
    world["polities"][polity_at:polity_at]=new_polities; world["provinces"][province_at:province_at]=new_provinces; world["territorialHoldings"][holding_at:holding_at]=new_holdings
    zones={x["id"]:x for x in world["navigationZones"]}
    for node in geography["navigationTopology"]["nodes"]:
        movement=["flying"] if node["class"] in {"impassable_barrier","decorative_water"} else ["naval","amphibious","flying"] if node["class"] in {"navigable_sea","island_coast"} else ["land","amphibious","flying"]
        zones.setdefault(node["id"],{"id":node["id"],"movementClasses":movement,"connections":{k:[] for k in movement}})
    for edge in geography["navigationTopology"]["links"]:
        for movement in edge["movementClasses"]:
            if movement in zones[edge["from"]]["connections"] and edge["to"] not in zones[edge["from"]]["connections"][movement]: zones[edge["from"]]["connections"][movement].append(edge["to"])
            if movement in zones[edge["to"]]["connections"] and edge["from"] not in zones[edge["to"]]["connections"][movement]: zones[edge["to"]]["connections"][movement].append(edge["from"])
    world["navigationZones"]=[zones[k] for k in sorted(zones)]
    for item in source["settlements"]:
        ident=item["id"]; roles=item["roles"]; defense=item["defenseClass"]
        record={"id":ident,"name":item["name"],"kind":"capital" if "capital" in roles else "port" if "major_port" in roles else "fort" if "fortified_town" in roles else "major_city","provinceId":item["provinceId"],"legalOwnerPolityId":item["polityId"],"controllerPolityId":item["polityId"],"capturable":True,"civilianFacilitiesInvulnerable":True,"navigationZoneId":item["navigationZoneId"],"cityCoreId":"city_core_"+ident,"defenseLayoutId":"defense_"+ident,"serviceIds":item["services"],"regionalInstanceId":item["regionalInstanceId"],"physicalMapId":item["physicalMapId"],"localPosition":positions[ident],"terrainClass":item["terrainClass"],"roleIds":roles,"activation":{"runtimeState":"abstract","representationTemplateId":"settlement_representation","deterministicKey":ident},"economicProfile":copy.deepcopy(item["economy"]),"productionRefs":item["economy"]["production"]}
        if item.get("port"): record["portAccess"]=copy.deepcopy(item["port"])
        world["settlements"].append(record); world["cityCores"].append({"id":"city_core_"+ident,"objectTemplateId":"capital_city_core" if "capital" in roles else "city_core"}); world["defenseLayouts"].append({"id":"defense_"+ident,"objectTemplateIds":["capital_defenses" if defense=="capital" else "port_defenses" if defense=="port" else "city_defenses"]})
    return world

def update_economy(source,economy):
    economy=copy.deepcopy(economy); catalog=economy["catalog"]; state=economy["state"]; keep=lambda rows:[x for x in rows if not x.get("id","").startswith("sea_")]
    for key in ("stores","markets","prices","producers"): catalog[key]=keep(catalog[key])
    state["storeBalances"]=keep(state["storeBalances"])
    for n,item in enumerate(source["settlements"]):
        sid="sea_"+item["id"]+"_store"; mid="sea_"+item["id"]+"_market"; is_port="major_port" in item["roles"]
        catalog["stores"].append({"id":sid,"kind":"warehouse" if "warehouse" in item["services"] else "settlement","owner":{"kind":"settlement","id":item["id"]},"capacityUnits":50000 if "trade_center" in item["roles"] else 20000,"allowedGoodIds":["grain","flour","ship_provisions"]})
        catalog["markets"].append({"id":mid,"storeId":sid,"owner":{"kind":"settlement","id":item["id"]}}); catalog["producers"].append({"id":"sea_"+item["id"]+"_producer","storeId":sid,"recipeId":"prepare_ship_provisions" if is_port else "mill_grain_into_flour","owner":{"kind":"settlement","id":item["id"]}})
        catalog["prices"].append({"id":"sea_"+item["id"]+"_grain_price","marketId":mid,"goodId":"grain","currencyId":"pound_sterling","quantityUnits":100,"amountMinor":10+n%7}); state["storeBalances"].append({"id":sid,"storeId":sid,"goods":[{"goodId":"grain","quantityUnits":1200+n*73},{"goodId":"ship_provisions","quantityUnits":800+n*29}],"currencies":[{"currencyId":"pound_sterling","amountMinor":2000+n*101}]})
    return economy

def main(argv=None):
    argv=sys.argv[1:] if argv is None else argv
    try:
        source,politics,geography,positions=validate()
        if argv==["--write"]:
            WORLD.write_text(json.dumps(project(source,politics,geography,positions,json.loads(WORLD.read_text())),ensure_ascii=False,indent=2)+"\n"); ECONOMY.write_text(json.dumps(update_economy(source,json.loads(ECONOMY.read_text())),ensure_ascii=False,indent=2)+"\n")
        elif argv: raise SoutheastAsiaContentError("usage: southeast_asia_content.py [--write]")
        print(f"Southeast Asia content valid: {len(source['settlements'])} settlements, {sum('port' in x for x in source['settlements'])} ports, {len(source['tradeRoutes'])} trade routes")
    except (OSError,json.JSONDecodeError,SoutheastAsiaContentError) as error: print(f"Southeast Asia content validation failed: {error}",file=sys.stderr); return 1
    return 0
if __name__=="__main__": raise SystemExit(main())

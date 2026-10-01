#!/usr/bin/env python3
"""Validate and project authoritative 1450 European settlement content."""
from __future__ import annotations

import copy
import json
import math
import re
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scenario/settlements/europe-1450.json"
POLITICS = ROOT / "scenario/politics/europe-1450.json"
GEOGRAPHY = ROOT / "scenario/geography/europe.json"
WORLD = ROOT / "scenario/world/world.json"
ECONOMY = ROOT / "scenario/economy/economy.json"
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
ROLES = {"capital", "major_port", "trade_center", "fortified_town", "transition_location", "historical_location", "production_center", "religious_site"}
TERRAIN = {"coast", "riverbank", "plains", "upland", "forest", "steppe"}
SEA_ZONES = {"north_sea_atlantic", "english_channel", "bay_of_biscay", "iberian_atlantic", "western_mediterranean", "adriatic_sea", "baltic_sea", "aegean_black_sea"}
LAND_ZONE = {
    "europe_atlantic_isles": "atlantic_isles_land", "europe_iberia_western_med": "iberia_land",
    "europe_france_low_countries": "france_low_countries_land", "europe_central_alpine": "central_alpine_land",
    "europe_baltic_scandinavia": "baltic_scandinavia_land", "europe_italy_central_med": "italy_land",
    "europe_balkans_aegean": "balkans_aegean_land", "europe_eastern_black_sea": "eastern_europe_land",
}

class SettlementContentError(ValueError): pass

def _index(records, label):
    result = {}
    if not isinstance(records, list): raise SettlementContentError(f"{label} must be an array")
    for item in records:
        ident = item.get("id") if isinstance(item, dict) else None
        if not isinstance(ident, str) or not ID_RE.fullmatch(ident): raise SettlementContentError(f"{label}: invalid stable ID {ident!r}")
        if ident in result: raise SettlementContentError(f"{label}: duplicate ID {ident!r}")
        result[ident] = item
    return result

def local_position(record, instance):
    source = record["sourcePosition"]; transform = instance["transform"]
    distortion = record.get("declaredDistortion", {}).get("offset", [0, 0])
    return {"x": round((source[0]-transform["sourceOrigin"][0])*transform["scale"][0]+transform["offset"][0]+distortion[0], 2),
            "y": round((source[1]-transform["sourceOrigin"][1])*transform["scale"][1]+transform["offset"][1]+distortion[1], 2)}

def validate(source_path=SOURCE, politics_path=POLITICS, geography_path=GEOGRAPHY, world_path=WORLD):
    source=json.loads(Path(source_path).read_text()); politics=json.loads(Path(politics_path).read_text()); geography=json.loads(Path(geography_path).read_text()); world=json.loads(Path(world_path).read_text())
    if source.get("schemaVersion") != 1 or source.get("campaignStartDate") != "1450-01-01": raise SettlementContentError("Europe settlements must use schema 1 and campaign start 1450-01-01")
    settlements=_index(source.get("settlements"), "settlements"); instances=_index(geography.get("instances"), "regional instances")
    polities=_index(politics.get("polities"), "polities"); provinces={p["id"]:(owner["id"],p) for owner in politics["polities"] for p in owner["provinces"]}
    world_regions={r["id"] for r in world["regionalGeography"]["regions"]}; world_anchors={a["id"] for a in world["regionalGeography"]["anchors"]}; geo_anchors={a["id"] for a in geography["boundaryAnchors"]}
    capitals={p["capitalSettlementId"] for p in politics["polities"]}
    if not capitals <= set(settlements): raise SettlementContentError(f"missing polity capitals: {sorted(capitals-set(settlements))}")
    positions={}; ports=[]
    for ident,s in settlements.items():
        for field in ("name","polityId","provinceId","regionalInstanceId","terrainClass","roles","services","productionRefs","defenseClass"):
            if field not in s: raise SettlementContentError(f"settlement {ident}: missing {field}")
        if s["polityId"] not in polities: raise SettlementContentError(f"settlement {ident}: missing polity")
        if s["provinceId"] not in provinces or provinces[s["provinceId"]][0] != s["polityId"]: raise SettlementContentError(f"settlement {ident}: province ownership mismatch")
        if s["regionalInstanceId"] not in instances: raise SettlementContentError(f"settlement {ident}: missing regional instance")
        if s["terrainClass"] not in TERRAIN: raise SettlementContentError(f"settlement {ident}: invalid terrain class")
        if not isinstance(s["roles"],list) or not s["roles"] or not set(s["roles"]) <= ROLES or len(s["roles"]) != len(set(s["roles"])): raise SettlementContentError(f"settlement {ident}: invalid roles")
        if ident in capitals and "capital" not in s["roles"]: raise SettlementContentError(f"settlement {ident}: polity capital lacks capital role")
        for key in ("services","productionRefs"):
            if not isinstance(s[key],list) or not s[key] or len(s[key]) != len(set(s[key])) or any(not ID_RE.fullmatch(x) for x in s[key]): raise SettlementContentError(f"settlement {ident}: invalid {key}")
        source_pos=s.get("sourcePosition")
        if not isinstance(source_pos,list) or len(source_pos)!=2 or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in source_pos): raise SettlementContentError(f"settlement {ident}: invalid source position")
        pos=local_position(s,instances[s["regionalInstanceId"]]); bounds=instances[s["regionalInstanceId"]]["localBounds"]
        if not bounds["minX"] <= pos["x"] <= bounds["maxX"] or not bounds["minY"] <= pos["y"] <= bounds["maxY"]: raise SettlementContentError(f"settlement {ident}: position outside local bounds")
        positions[ident]=pos
        port=s.get("port")
        if port:
            if s["terrainClass"] not in {"coast","riverbank"} or "major_port" not in s["roles"] or "port_services" not in s["services"]: raise SettlementContentError(f"settlement {ident}: invalid port access")
            if port.get("maritimeZoneId") not in SEA_ZONES or not ID_RE.fullmatch(port.get("access", "")): raise SettlementContentError(f"settlement {ident}: invalid maritime topology")
            ports.append(ident)
        elif "major_port" in s["roles"] or "port_services" in s["services"]: raise SettlementContentError(f"settlement {ident}: inland settlement exposes maritime access")
    minimum=source["placementRules"]["minimumSeparationCells"]
    ids=sorted(settlements)
    for i,left in enumerate(ids):
        for right in ids[i+1:]:
            if settlements[left]["regionalInstanceId"] != settlements[right]["regionalInstanceId"]: continue
            distance=math.dist((positions[left]["x"],positions[left]["y"]),(positions[right]["x"],positions[right]["y"]))
            if distance < minimum: raise SettlementContentError(f"settlements overlap: {left} and {right}")
    clearance=source["placementRules"]["entryAnchorClearanceCells"]
    for anchor in geography["boundaryAnchors"]:
        for ident,s in settlements.items():
            if "transition_location" not in s["roles"] and s["regionalInstanceId"] == anchor["instanceId"] and math.dist((positions[ident]["x"],positions[ident]["y"]), anchor["local"]) < clearance:
                raise SettlementContentError(f"settlement {ident}: obstructs entry anchor {anchor['id']}")
    transitions=_index(source.get("transitions"), "transitions")
    expected={"americas_caribbean","africa","middle_east_india"}
    if {x.get("neighborRegionId") for x in transitions.values()} != expected: raise SettlementContentError("neighbor boundary stubs are incomplete")
    for ident,t in transitions.items():
        if t.get("settlementId") not in settlements or t.get("boundaryAnchorId") not in geo_anchors or t.get("neighborRegionId") not in world_regions or t.get("stub") is not True: raise SettlementContentError(f"transition {ident}: invalid reference")
        if "transition_location" not in settlements[t["settlementId"]]["roles"] and t["settlementId"] != "constantinople": raise SettlementContentError(f"transition {ident}: settlement is not an entry location")
    return source, politics, geography, world, positions

def _zone(ident, classes): return {"id":ident,"movementClasses":classes,"connections":{kind:[] for kind in classes}}

def project(source, politics, geography, world, positions):
    world=copy.deepcopy(world); settlements=source["settlements"]
    europe_ids={x["id"] for x in settlements}
    # Retain fixture zones, then add a deterministic Europe land/sea topology.
    zones={z["id"]:z for z in world["navigationZones"]}
    for ident in LAND_ZONE.values(): zones.setdefault(ident,_zone(ident,["land","amphibious","flying"]))
    for ident in SEA_ZONES: zones.setdefault(ident,_zone(ident,["naval","amphibious","flying"]))
    land_edges=[("atlantic_isles_land","france_low_countries_land"),("france_low_countries_land","iberia_land"),("france_low_countries_land","central_alpine_land"),("central_alpine_land","baltic_scandinavia_land"),("central_alpine_land","italy_land"),("central_alpine_land","balkans_aegean_land"),("central_alpine_land","eastern_europe_land"),("italy_land","balkans_aegean_land"),("balkans_aegean_land","eastern_europe_land")]
    sea_edges=[("north_sea_atlantic","english_channel"),("north_sea_atlantic","baltic_sea"),("english_channel","bay_of_biscay"),("bay_of_biscay","iberian_atlantic"),("iberian_atlantic","western_mediterranean"),("western_mediterranean","adriatic_sea"),("western_mediterranean","aegean_black_sea"),("adriatic_sea","aegean_black_sea")]
    for a,b in land_edges:
        for kind in ("land","amphibious","flying"):
            if b not in zones[a]["connections"][kind]: zones[a]["connections"][kind].append(b)
            if a not in zones[b]["connections"][kind]: zones[b]["connections"][kind].append(a)
    for a,b in sea_edges:
        for kind in ("naval","amphibious","flying"):
            if b not in zones[a]["connections"][kind]: zones[a]["connections"][kind].append(b)
            if a not in zones[b]["connections"][kind]: zones[b]["connections"][kind].append(a)
    world["navigationZones"]=[zones[k] for k in sorted(zones)]
    services={x["id"]:x for x in world["settlementServiceDefinitions"]}; services["warehouse"]={"id":"warehouse","name":"Warehouse"}; world["settlementServiceDefinitions"]=[services[k] for k in sorted(services)]
    # Replace only authored European rows. Political capital stubs and every other
    # region remain intact, so a regional density rebuild cannot erase the world.
    world["settlements"]=[x for x in world["settlements"] if x["id"] not in europe_ids and x.get("regionalInstanceId") not in LAND_ZONE]
    world["cityCores"]=[x for x in world["cityCores"] if x["id"] not in {"city_core_"+s for s in europe_ids}]
    world["defenseLayouts"]=[x for x in world["defenseLayouts"] if x["id"] not in {"defense_"+s for s in europe_ids}]
    europe_provinces={p["id"] for owner in politics["polities"] for p in owner["provinces"]}
    for p in world["provinces"]:
        if p["id"] in europe_provinces: p["settlementIds"]=[]
    provinces={p["id"]:p for p in world["provinces"]}
    for s in settlements:
        ident=s["id"]; roles=s["roles"]; defense=s["defenseClass"]
        item={"id":ident,"name":s["name"],"kind":"capital" if "capital" in roles else "port" if "major_port" in roles else "fort" if "fortified_town" in roles else "major_city",
              "provinceId":s["provinceId"],"legalOwnerPolityId":s["polityId"],"controllerPolityId":s["polityId"],"capturable":True,"civilianFacilitiesInvulnerable":True,
              "navigationZoneId":LAND_ZONE[s["regionalInstanceId"]],"cityCoreId":"city_core_"+ident,"defenseLayoutId":"defense_"+ident,"serviceIds":s["services"],
              "regionalInstanceId":s["regionalInstanceId"],"localPosition":positions[ident],"terrainClass":s["terrainClass"],"roleIds":roles,
              "activation":{"runtimeState":"abstract","representationTemplateId":"settlement_representation","deterministicKey":ident},"productionRefs":s["productionRefs"]}
        if s.get("port"): item["portAccess"]=copy.deepcopy(s["port"])
        world["settlements"].append(item); provinces[s["provinceId"]]["settlementIds"].append(ident)
        world["cityCores"].append({"id":"city_core_"+ident,"objectTemplateId":"capital_city_core" if "capital" in roles else "city_core"})
        world["defenseLayouts"].append({"id":"defense_"+ident,"objectTemplateIds":["capital_defenses" if defense=="capital" else "port_defenses" if defense=="port" else "city_defenses"]})
    return world

def update_economy(source, economy):
    economy=copy.deepcopy(economy); catalog=economy["catalog"]; state=economy["state"]
    # Settlement stores and markets are declarative endpoints; balances remain authoritative without map objects.
    keep=lambda rows: [r for r in rows if not r.get("id","").startswith("europe_")]
    catalog["stores"]=keep(catalog["stores"]); catalog["markets"]=keep(catalog["markets"]); catalog["prices"]=keep(catalog["prices"]); catalog["producers"]=keep(catalog["producers"]); state["storeBalances"]=keep(state["storeBalances"])
    for s in source["settlements"]:
        sid="europe_"+s["id"]+"_store"; mid="europe_"+s["id"]+"_market"
        catalog["stores"].append({"id":sid,"kind":"warehouse" if "warehouse" in s["services"] else "settlement","owner":{"kind":"settlement","id":s["id"]},"capacityUnits":50000 if "trade_center" in s["roles"] else 20000,"allowedGoodIds":["grain","flour","ship_provisions"]})
        catalog["markets"].append({"id":mid,"storeId":sid,"owner":{"kind":"settlement","id":s["id"]}})
        catalog["producers"].append({"id":"europe_"+s["id"]+"_producer","storeId":sid,"recipeId":"prepare_ship_provisions" if "major_port" in s["roles"] else "mill_grain_into_flour","owner":{"kind":"settlement","id":s["id"]}})
        catalog["prices"].append({"id":"europe_"+s["id"]+"_grain_price","marketId":mid,"goodId":"grain","currencyId":"pound_sterling","quantityUnits":100,"amountMinor":12})
        state["storeBalances"].append({"id":sid,"storeId":sid,"goods":[{"goodId":"grain","quantityUnits":2000}],"currencies":[{"currencyId":"pound_sterling","amountMinor":2400}]})
    return economy

def main(argv=None):
    argv=sys.argv[1:] if argv is None else argv
    try:
        source,politics,geography,world,positions=validate()
        if argv == ["--write"]:
            WORLD.write_text(json.dumps(project(source,politics,geography,world,positions),ensure_ascii=False,indent=2)+"\n")
            economy=json.loads(ECONOMY.read_text()); ECONOMY.write_text(json.dumps(update_economy(source,economy),ensure_ascii=False,indent=2)+"\n")
        elif argv: raise SettlementContentError("usage: europe_settlements.py [--write]")
        print(f"Europe settlements valid: {len(source['settlements'])} settlements, {sum('port' in x for x in source['settlements'])} ports, {len(source['transitions'])} boundary stubs")
    except (OSError,json.JSONDecodeError,SettlementContentError) as error:
        print(f"Europe settlement validation failed: {error}",file=sys.stderr); return 1
    return 0

if __name__ == "__main__": raise SystemExit(main())

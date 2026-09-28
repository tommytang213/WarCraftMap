#!/usr/bin/env python3
"""Build and validate the focused 1450 Africa regional-content pass."""
from __future__ import annotations

import copy
import json
import math
import re
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scenario/settlements/africa-1450.json"
POLITICS = ROOT / "scenario/politics/africa-1450.json"
GEOGRAPHY = ROOT / "scenario/geography/africa.json"
TERRAIN = ROOT / "scenario/terrain/africa.json"
WORLD = ROOT / "scenario/world/world.json"
ECONOMY = ROOT / "scenario/economy/economy.json"
ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
ROLES = {"capital", "major_port", "trade_center", "fortified_town", "caravan_center", "transition_location", "historical_location"}
TERRAINS = {"coast", "riverbank", "plains", "upland", "forest", "steppe", "desert", "island"}
SEA_ZONES = {"north_atlantic_navigation", "south_atlantic_navigation", "mediterranean_navigation", "red_sea_navigation", "indian_ocean_navigation", "mozambique_channel_navigation"}
LAND_ZONE = "africa_mainland_land"


class AfricaContentError(ValueError):
    pass


def _index(rows, label):
    if not isinstance(rows, list):
        raise AfricaContentError(f"{label} must be an array")
    out = {}
    for row in rows:
        ident = row.get("id") if isinstance(row, dict) else None
        if not isinstance(ident, str) or not ID.fullmatch(ident):
            raise AfricaContentError(f"{label}: invalid stable ID {ident!r}")
        if ident in out:
            raise AfricaContentError(f"{label}: duplicate ID {ident!r}")
        out[ident] = row
    return out


def _reachable(edges, start):
    graph = {}
    for a, b in edges:
        graph.setdefault(a, set()).add(b); graph.setdefault(b, set()).add(a)
    seen, pending = set(), [start]
    while pending:
        node = pending.pop()
        if node not in seen:
            seen.add(node); pending.extend(graph.get(node, ()))
    return seen


def validate(source_path=SOURCE, politics_path=POLITICS, geography_path=GEOGRAPHY):
    source = json.loads(Path(source_path).read_text()); politics = json.loads(Path(politics_path).read_text())
    geography = json.loads(Path(geography_path).read_text()); terrain = json.loads(TERRAIN.read_text())
    if source.get("schemaVersion") != 1 or source.get("campaignStartDate") != "1450-01-01":
        raise AfricaContentError("Africa content must use schema 1 and campaign start 1450-01-01")
    settlements = _index(source.get("settlements"), "settlements"); polities = _index(politics.get("polities"), "polities")
    provinces = {p["id"]: (owner["id"], p) for owner in polities.values() for p in owner.get("provinces", [])}
    instances = _index(geography.get("instances"), "regional instances"); anchors = _index(geography.get("boundaryAnchors"), "boundary anchors")
    water = {x["id"] + "_navigation" for x in terrain["waterBodies"] if x["kind"] == "navigable_sea"}
    if SEA_ZONES - water:
        raise AfricaContentError(f"maritime zones missing from generated topology: {sorted(SEA_ZONES-water)}")
    capitals = {p["capitalSettlementId"] for p in polities.values()}
    if not capitals <= set(settlements):
        raise AfricaContentError(f"missing polity capitals: {sorted(capitals-set(settlements))}")
    positions = {}
    for ident, item in settlements.items():
        required = ("name", "polityId", "provinceId", "regionalInstanceId", "position", "terrainClass", "roles", "services", "productionRefs", "defenseClass")
        if any(field not in item for field in required):
            raise AfricaContentError(f"settlement {ident}: missing required field")
        if item["polityId"] not in polities or item["provinceId"] not in provinces or provinces[item["provinceId"]][0] != item["polityId"]:
            raise AfricaContentError(f"settlement {ident}: polity/province mismatch")
        if item["regionalInstanceId"] not in instances:
            raise AfricaContentError(f"settlement {ident}: missing regional instance")
        pos = item["position"]
        if not isinstance(pos, list) or len(pos) != 2 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in pos):
            raise AfricaContentError(f"settlement {ident}: invalid position")
        bounds = instances[item["regionalInstanceId"]]["localBounds"]
        if not bounds["minX"] <= pos[0] <= bounds["maxX"] or not bounds["minY"] <= pos[1] <= bounds["maxY"]:
            raise AfricaContentError(f"settlement {ident}: position outside local bounds")
        positions[ident] = {"x": pos[0], "y": pos[1]}
        if item["terrainClass"] not in TERRAINS or not item["roles"] or not set(item["roles"]) <= ROLES or len(item["roles"]) != len(set(item["roles"])):
            raise AfricaContentError(f"settlement {ident}: invalid terrain class or roles")
        if ident in capitals and "capital" not in item["roles"]:
            raise AfricaContentError(f"settlement {ident}: polity capital lacks capital role")
        for field in ("services", "productionRefs"):
            values = item[field]
            if not isinstance(values, list) or not values or len(values) != len(set(values)) or any(not ID.fullmatch(x) for x in values):
                raise AfricaContentError(f"settlement {ident}: invalid {field}")
        port = item.get("port")
        if port:
            if item["terrainClass"] not in {"coast", "riverbank", "island"} or "major_port" not in item["roles"] or "port_services" not in item["services"]:
                raise AfricaContentError(f"settlement {ident}: invalid port access")
            if port.get("maritimeZoneId") not in SEA_ZONES or port["maritimeZoneId"] not in water or not ID.fullmatch(port.get("access", "")):
                raise AfricaContentError(f"settlement {ident}: invalid maritime topology")
        elif "major_port" in item["roles"] or "port_services" in item["services"]:
            raise AfricaContentError(f"settlement {ident}: inland settlement exposes maritime access")
    ids = sorted(settlements); minimum = source["placementRules"]["minimumSeparationCells"]
    for n, left in enumerate(ids):
        for right in ids[n+1:]:
            if math.dist(tuple(positions[left].values()), tuple(positions[right].values())) < minimum:
                raise AfricaContentError(f"settlements overlap: {left} and {right}")
    clearance = source["placementRules"]["entryAnchorClearanceCells"]
    for anchor in anchors.values():
        for ident, pos in positions.items():
            if "transition_location" not in settlements[ident]["roles"] and math.dist(tuple(pos.values()), tuple(anchor["local"])) < clearance:
                raise AfricaContentError(f"settlement {ident}: obstructs entry anchor {anchor['id']}")
    routes = _index(source.get("tradeRoutes"), "trade routes")
    endpoints = set()
    edges = []
    for ident, route in routes.items():
        a, b = route.get("fromSettlementId"), route.get("toSettlementId")
        if a not in settlements or b not in settlements or a == b or route.get("contract") != "settlement_trade_endpoint":
            raise AfricaContentError(f"trade route {ident}: invalid endpoint contract")
        if route.get("kind") == "maritime" and ("port" not in settlements[a] or "port" not in settlements[b]):
            raise AfricaContentError(f"trade route {ident}: inland maritime route")
        if route.get("kind") == "trans_saharan":
            if not {"caravan_center"} <= set(settlements[a]["roles"]) or not {"caravan_center"} <= set(settlements[b]["roles"]):
                raise AfricaContentError(f"trade route {ident}: trans-Saharan endpoints must be caravan centers")
            endpoints.update((a, b)); edges.append((a, b))
    required = set(source["requiredTransSaharanEndpoints"])
    if not required <= endpoints or required - _reachable(edges, next(iter(required))):
        raise AfricaContentError("trans-Saharan endpoints are not connected")
    transitions = _index(source.get("transitions"), "transitions")
    expected = {"europe", "middle_east_india", "americas_caribbean"}
    if {x.get("neighborRegionId") for x in transitions.values()} != expected:
        raise AfricaContentError("Africa regional transitions are incomplete")
    for ident, transition in transitions.items():
        sid = transition.get("settlementId")
        if sid not in settlements or transition.get("boundaryAnchorId") not in anchors or transition.get("stub") is not True or "transition_location" not in settlements[sid]["roles"]:
            raise AfricaContentError(f"transition {ident}: invalid reference")
    return source, politics, geography, positions


def _zone(ident, movement):
    return {"id": ident, "movementClasses": movement, "connections": {kind: [] for kind in movement}}


def project(source, politics, geography, positions, world):
    world = copy.deepcopy(world)
    africa_polities = {x["id"] for x in politics["polities"]}; africa_provinces = {p["id"] for x in politics["polities"] for p in x["provinces"]}
    africa_settlements = {x["id"] for x in source["settlements"]}
    world["polities"] = [x for x in world["polities"] if x["id"] not in africa_polities]
    world["provinces"] = [x for x in world["provinces"] if x["id"] not in africa_provinces]
    world["settlements"] = [x for x in world["settlements"] if x["id"] not in africa_settlements]
    world["cityCores"] = [x for x in world["cityCores"] if x["id"] not in {"city_core_"+s for s in africa_settlements}]
    world["defenseLayouts"] = [x for x in world["defenseLayouts"] if x["id"] not in {"defense_"+s for s in africa_settlements}]
    world["territorialHoldings"] = [x for x in world["territorialHoldings"] if x["id"] not in {"holding_"+p for p in africa_provinces}]
    for polity in politics["polities"]:
        province_ids = [p["id"] for p in polity["provinces"]]
        world["polities"].append({k: polity[k] for k in ("id", "name", "adjective", "sovereignTier", "nativeSovereignTitle", "capitalSettlementId")} | {"provinceIds": province_ids})
        for province in polity["provinces"]:
            world["provinces"].append({"id": province["id"], "name": province["name"], "administrativeType": province["administrativeType"], "legalOwnerPolityId": polity["id"], "controllerPolityId": polity["id"], "settlementIds": []})
            world["territorialHoldings"].append({"id":"holding_"+province["id"],"territory":{"kind":"province","id":province["id"]},"legalOwner":{"kind":"polity","id":polity["id"]},"controllerPolityId":polity["id"],"governingPolityId":polity["id"],"sovereignPolityId":polity["id"],"autonomyPercent":35,"overlordTaxRatePercent":0,"upkeepRatePercent":5,"obligations":[]})
    provinces = {p["id"]: p for p in world["provinces"]}
    zones = {z["id"]: z for z in world["navigationZones"]}
    zones.setdefault(LAND_ZONE, _zone(LAND_ZONE, ["land", "amphibious", "flying"]))
    for sea in sorted(SEA_ZONES):
        zones.setdefault(sea, _zone(sea, ["naval", "amphibious", "flying"]))
    sea_edges = [("north_atlantic_navigation", "mediterranean_navigation"), ("north_atlantic_navigation", "south_atlantic_navigation"), ("south_atlantic_navigation", "indian_ocean_navigation"), ("indian_ocean_navigation", "mozambique_channel_navigation"), ("indian_ocean_navigation", "red_sea_navigation"), ("red_sea_navigation", "mediterranean_navigation")]
    for a, b in sea_edges:
        for kind in ("naval", "amphibious", "flying"):
            if b not in zones[a]["connections"][kind]: zones[a]["connections"][kind].append(b)
            if a not in zones[b]["connections"][kind]: zones[b]["connections"][kind].append(a)
    world["navigationZones"] = [zones[k] for k in sorted(zones)]
    for item in source["settlements"]:
        ident = item["id"]; roles = item["roles"]; defense = item["defenseClass"]
        record = {"id": ident, "name": item["name"], "kind": "capital" if "capital" in roles else "port" if "major_port" in roles else "fort" if "fortified_town" in roles else "trading_post" if "caravan_center" in roles else "major_city", "provinceId": item["provinceId"], "legalOwnerPolityId": item["polityId"], "controllerPolityId": item["polityId"], "capturable": True, "civilianFacilitiesInvulnerable": True, "navigationZoneId": LAND_ZONE, "cityCoreId": "city_core_"+ident, "defenseLayoutId": "defense_"+ident, "serviceIds": item["services"], "regionalInstanceId": item["regionalInstanceId"], "localPosition": positions[ident], "terrainClass": item["terrainClass"], "roleIds": roles, "activation": {"runtimeState": "abstract", "representationTemplateId": "settlement_representation", "deterministicKey": ident}, "productionRefs": item["productionRefs"]}
        if item.get("port"): record["portAccess"] = copy.deepcopy(item["port"])
        world["settlements"].append(record); provinces[item["provinceId"]]["settlementIds"].append(ident)
        world["cityCores"].append({"id": "city_core_"+ident, "objectTemplateId": "capital_city_core" if "capital" in roles else "city_core"})
        world["defenseLayouts"].append({"id": "defense_"+ident, "objectTemplateIds": ["capital_defenses" if defense == "capital" else "port_defenses" if defense == "port" else "city_defenses"]})
    return world


def update_economy(source, economy):
    economy = copy.deepcopy(economy); catalog = economy["catalog"]; state = economy["state"]
    keep = lambda rows: [x for x in rows if not x.get("id", "").startswith("africa_")]
    for key in ("stores", "markets", "prices", "producers"): catalog[key] = keep(catalog[key])
    state["storeBalances"] = keep(state["storeBalances"])
    for item in source["settlements"]:
        sid = "africa_"+item["id"]+"_store"; mid = "africa_"+item["id"]+"_market"
        catalog["stores"].append({"id": sid, "kind": "warehouse" if "warehouse" in item["services"] else "settlement", "owner": {"kind": "settlement", "id": item["id"]}, "capacityUnits": 50000 if set(item["roles"]) & {"trade_center", "caravan_center"} else 20000, "allowedGoodIds": ["grain", "flour", "ship_provisions"]})
        catalog["markets"].append({"id": mid, "storeId": sid, "owner": {"kind": "settlement", "id": item["id"]}})
        catalog["producers"].append({"id": "africa_"+item["id"]+"_producer", "storeId": sid, "recipeId": "prepare_ship_provisions" if "major_port" in item["roles"] else "mill_grain_into_flour", "owner": {"kind": "settlement", "id": item["id"]}})
        catalog["prices"].append({"id": "africa_"+item["id"]+"_grain_price", "marketId": mid, "goodId": "grain", "currencyId": "pound_sterling", "quantityUnits": 100, "amountMinor": 12})
        state["storeBalances"].append({"id": sid, "storeId": sid, "goods": [{"goodId": "grain", "quantityUnits": 2000}], "currencies": [{"currencyId": "pound_sterling", "amountMinor": 2400}]})
    return economy


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        source, politics, geography, positions = validate()
        if argv == ["--write"]:
            WORLD.write_text(json.dumps(project(source, politics, geography, positions, json.loads(WORLD.read_text())), ensure_ascii=False, indent=2)+"\n")
            ECONOMY.write_text(json.dumps(update_economy(source, json.loads(ECONOMY.read_text())), ensure_ascii=False, indent=2)+"\n")
        elif argv:
            raise AfricaContentError("usage: africa_content.py [--write]")
        print(f"Africa content valid: {len(source['settlements'])} settlements, {sum('port' in x for x in source['settlements'])} ports, {len(source['tradeRoutes'])} trade routes")
    except (OSError, json.JSONDecodeError, AfricaContentError) as error:
        print(f"Africa content validation failed: {error}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

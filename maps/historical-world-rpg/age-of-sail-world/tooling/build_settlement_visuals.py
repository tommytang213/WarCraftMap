#!/usr/bin/env python3
"""Generate deterministic regional settlement sets and placement manifests.

The world projection is the coverage authority.  Regional settlement sources add
art direction, but Warcraft handles are deliberately absent from this format.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "scenario"
CATALOGUE = ROOT.parent / "_shared/assets/warcraft-3.0-stock.json"
REGIONS = ("europe", "africa", "middle_east_india", "southeast_asia",
           "east_asia", "americas_caribbean", "pacific")


class SettlementVisualError(ValueError):
    pass


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _region(instance):
    prefixes = (("mei_", "middle_east_india"), ("sea_", "southeast_asia"),
                ("east_asia_", "east_asia"), ("americas_", "americas_caribbean"),
                ("africa_", "africa"), ("europe_", "europe"), ("pacific_", "pacific"))
    for prefix, region in prefixes:
        if str(instance).startswith(prefix):
            return region
    raise SettlementVisualError(f"unknown regional instance {instance!r}")


def authored():
    rows = {}
    for path in sorted((SCENARIO / "settlements").glob("*.json")):
        doc = load(path)
        for row in doc.get("settlements", []):
            if row["id"] in rows:
                raise SettlementVisualError(f"duplicate authored settlement {row['id']}")
            rows[row["id"]] = row
    return rows


def _culture(region, terrain):
    if region == "europe": return "european_masonry"
    if region == "africa": return "sahelian_earthen" if terrain in {"desert", "steppe"} else "african_courtyard"
    if region == "middle_east_india": return "islamicate_indic_courtyard"
    if region == "southeast_asia": return "southeast_asian_timber"
    if region == "east_asia": return "east_asian_timber_masonry"
    if region == "americas_caribbean": return "american_stone_earthwork"
    return "pacific_timber_thatch"


def _set_id(region, terrain):
    climate = "arid" if terrain in {"desert", "steppe"} else "maritime" if terrain in {"coast", "island", "riverbank"} else "inland"
    return f"{region}_{climate}"


ROLE_TEMPLATES = {
    "city_core": ("human_town_hall", "city_core", 5, True, False),
    "civilian_service": ("human_town_hall", "civilian_service", 2, False, True),
    "production": ("human_town_hall", "production", 2, False, True),
    "warehouse": ("human_town_hall", "warehouse", 2, False, True),
    "port_access": ("human_transport_ship", "port_access", 2, False, True),
    "religious_historical": ("human_town_hall", "landmark", 2, False, True),
    "defense": ("human_town_hall", "defense", 3, True, False),
}


def build():
    world = load(SCENARIO / "world/world.json")
    details = authored()
    fit = load(SCENARIO / "visuals/historical-fit.json")
    gaps = [x for x in fit["mappings"] if x["entityKind"] == "building" and x["classification"] == "custom_model_candidate"]
    sets = []
    for region_index, region in enumerate(REGIONS):
        for climate in ("arid", "inland", "maritime"):
            sid = f"{region}_{climate}"
            sets.append({"id": sid, "regionId": region, "climateVariant": climate,
                "culturalFamily": _culture(region, "desert" if climate == "arid" else "coast" if climate == "maritime" else "plains"),
                "periodVariants": [{"id":"early_modern_1450_1699","fromYear":1450,"toYear":1699},
                                   {"id":"early_modern_1700_1820","fromYear":1700,"toYear":1820}],
                "densityVariants": {"village":1,"town":2,"city":3,"capital":4},
                "roleVisuals": [{"role": role, "assetId": spec[0], "semantic": spec[1],
                    "scale": round(0.9 + (region_index % 3) * 0.05, 2),
                    "tintProfile": f"{region}_{climate}",
                    "footprintCells": spec[2], "destructible": spec[3], "invulnerable": spec[4]}
                    for role, spec in ROLE_TEMPLATES.items()]})
    assignments = []
    for row in sorted(world["settlements"], key=lambda x:x["id"]):
        detail = details.get(row["id"], {})
        region = _region(row["regionalInstanceId"])
        terrain = detail.get("terrainClass", row.get("terrainClass", "plains"))
        roles = list(detail.get("roles", [row["kind"]]))
        services = list(detail.get("services", row.get("serviceIds", [])))
        productions = list(detail.get("productionRefs", []))
        port = detail.get("port") or row.get("portAccess")
        required = ["city_core"] if row.get("capturable") else []
        if services: required.append("civilian_service")
        if productions: required.append("production")
        if "warehouse" in services or "storage" in services: required.append("warehouse")
        if port: required.append("port_access")
        if set(roles) & {"religious_location","historical_location","pilgrimage_location"}: required.append("religious_historical")
        if row.get("defenseLayoutId"): required.append("defense")
        assignments.append({"settlementId":row["id"], "regionId":region,
            "regionalInstanceId":row["regionalInstanceId"], "polityId":row["controllerPolityId"],
            "provinceId":row["provinceId"], "visualSetId":_set_id(region, terrain),
            "terrainClass":terrain, "settlementClass":row["kind"], "roles":roles,
            "serviceIds":services, "productionIds":productions,
            "portAccess":port, "cityCoreId":row.get("cityCoreId"),
            "defenseLayoutId":row.get("defenseLayoutId"), "requiredVisualRoles":sorted(set(required)),
            "explicitException": None if required else "abstract_non_capturable_political_center"})
    layouts = [{"defenseLayoutId":x["id"], "settlementId":x["id"].removeprefix("defense_"),
                "visualRole":"defense", "objectTemplateIds":x["objectTemplateIds"]}
               for x in sorted(world["defenseLayouts"], key=lambda x:x["id"])]
    return {"format":"age_of_sail_settlement_visuals_v1", "scenario":"age_of_sail_world",
        "policy":{"authoritativeIdentitySource":"stable settlement state", "objectInstancesAreAuthoritative":False,
          "teamColorSource":"controller", "captureStateMarker":"city_core_team_color",
          "civilianSemantics":"invulnerable", "defenseSemantics":"destructible_rebuildable",
          "maxObjectsPerSettlement":24, "entryAnchorClearanceCells":1},
        "visualSets":sets, "settlementAssignments":assignments, "defenseLayoutAssignments":layouts,
        "customAssetRequirements":[{"id":f"building_{x['entityId']}_identity", "entityKind":"building",
            "entityId":x["entityId"], "sourceFitId":x["id"], "priority":x["replacementPriority"],
            "type":"custom_model", "fallbackAssetId":x["candidateAssetId"], "materialGap":x["knownMismatches"]}
            for x in sorted(gaps,key=lambda x:x["entityId"])]}


def placements(doc):
    sets = {x["id"]:x for x in doc["visualSets"]}
    manifests = defaultdict(list)
    for row in doc["settlementAssignments"]:
        spec = sets[row["visualSetId"]]; visuals={x["role"]:x for x in spec["roleVisuals"]}
        objects=[]
        # Fixed offsets leave the origin/entry lane clear and are stable across rebuilds.
        offsets=((4,0),(10,0),(16,0),(22,0),(28,0),(34,0),(40,0))
        for index, role in enumerate(row["requiredVisualRoles"]):
            visual=visuals[role]
            objects.append({"stableObjectId":f"{row['settlementId']}__{role}", "role":role,
                "assetId":visual["assetId"], "offsetCells":list(offsets[index]),
                "footprintCells":visual["footprintCells"], "destructible":visual["destructible"],
                "invulnerable":visual["invulnerable"]})
        manifests[row["regionalInstanceId"]].append({"settlementId":row["settlementId"],
            "visualSetId":row["visualSetId"], "entryAnchor":[0,0], "objects":objects})
    return {key: sorted(value,key=lambda x:x["settlementId"]) for key,value in sorted(manifests.items())}


def validate(doc, catalogue, world=None):
    world = world or load(SCENARIO / "world/world.json")
    assets={x["id"]:x for x in catalogue["assets"]}; sets={x["id"]:x for x in doc["visualSets"]}
    assignments={x["settlementId"]:x for x in doc["settlementAssignments"]}
    expected={x["id"] for x in world["settlements"]}
    if len(assignments)!=len(doc["settlementAssignments"]) or set(assignments)!=expected:
        raise SettlementVisualError("incomplete or duplicate settlement coverage")
    layout_ids={x["id"] for x in world["defenseLayouts"]}
    covered={x["defenseLayoutId"] for x in doc["defenseLayoutAssignments"]}
    if covered != layout_ids: raise SettlementVisualError("incomplete defense layout coverage")
    for sid,row in assignments.items():
        if row["regionId"] not in REGIONS or row["visualSetId"] not in sets: raise SettlementVisualError(f"{sid}: invalid region or visual set")
        visuals={x["role"]:x for x in sets[row["visualSetId"]]["roleVisuals"]}
        if not set(row["requiredVisualRoles"]) <= set(visuals): raise SettlementVisualError(f"{sid}: missing required role")
        if row["portAccess"] and row["terrainClass"] not in {"coast","island","riverbank"}: raise SettlementVisualError(f"{sid}: inland port visuals")
        if not row["requiredVisualRoles"] and not row.get("explicitException"): raise SettlementVisualError(f"{sid}: undeclared placeholder")
        for visual in visuals.values():
            asset=assets.get(visual["assetId"])
            if not asset: raise SettlementVisualError(f"{sid}: invalid asset")
            if not asset["scale"]["min"] <= visual["scale"] <= asset["scale"]["max"]: raise SettlementVisualError(f"{sid}: unsafe scale")
            if visual["footprintCells"] <= 0: raise SettlementVisualError(f"{sid}: invalid footprint")
    fit_ids={x["id"] for x in load(SCENARIO/"visuals/historical-fit.json")["mappings"]}
    for requirement in doc["customAssetRequirements"]:
        if requirement["sourceFitId"] not in fit_ids or requirement["fallbackAssetId"] not in assets:
            raise SettlementVisualError("undeclared custom asset gap")
    for instance, entries in placements(doc).items():
        for entry in entries:
            if len(entry["objects"]) > doc["policy"]["maxObjectsPerSettlement"]: raise SettlementVisualError("active-object budget")
            offsets=[tuple(x["offsetCells"]) for x in entry["objects"]]
            if len(offsets)!=len(set(offsets)): raise SettlementVisualError("conflicting placements")
            if any(abs(x)<=doc["policy"]["entryAnchorClearanceCells"] and abs(y)<=doc["policy"]["entryAnchorClearanceCells"] for x,y in offsets):
                raise SettlementVisualError("blocked entry")
            for index,left in enumerate(entry["objects"]):
                for right in entry["objects"][index+1:]:
                    dx=abs(left["offsetCells"][0]-right["offsetCells"][0]); dy=abs(left["offsetCells"][1]-right["offsetCells"][1])
                    clearance=(left["footprintCells"]+right["footprintCells"])/2
                    if dx < clearance and dy < clearance: raise SettlementVisualError("conflicting placements")
    return True


if __name__ == "__main__":
    doc=build(); validate(doc,load(CATALOGUE))
    target=SCENARIO/"visuals"; reports=target/"reports"
    target.mkdir(parents=True,exist_ok=True); reports.mkdir(parents=True,exist_ok=True)
    (target/"settlement-building-sets.json").write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n")
    (reports/"settlement-placement-manifests.json").write_text(json.dumps(placements(doc),indent=2,sort_keys=True)+"\n")

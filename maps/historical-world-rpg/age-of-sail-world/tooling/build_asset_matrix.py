#!/usr/bin/env python3
"""Build the Age of Sail historical-fit matrix from authored scenario entities."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "scenario"
REGIONS = ("europe", "africa", "middle_east_india", "southeast_asia", "east_asia", "americas_caribbean", "pacific")

def read(path):
    with path.open(encoding="utf-8") as handle: return json.load(handle)

def add(rows, seen, kind, ident, region="global", polity="unaffiliated", **hints):
    key = (kind, ident)
    if key not in seen:
        seen.add(key); rows.append({"kind":kind,"id":ident,"region":region,"polity":polity, **hints})

def entities():
    rows=[]; seen=set()
    for path in sorted((SCENARIO / "rosters").glob("*.json")):
        data=read(path)
        for x in data.get("runtimeTemplates",[]): add(rows,seen,"runtime_template",x["id"], objectId=x.get("warcraftUnitTypeId"))
        for x in data.get("ships",[]): add(rows,seen,"ship",x["id"])
        for x in data.get("archetypes",[]):
            if not x.get("abstract"): add(rows,seen,"unit",x["id"], polity=x.get("countryId") or "unaffiliated")
        for x in data.get("abilities",[]): add(rows,seen,"ability",x["id"])
    chars=read(SCENARIO/"characters/global.json")
    for x in chars["characters"]:
        add(rows,seen,"character",x["id"],x["regionId"],x.get("allegiancePolityId") or "unaffiliated")
        for ident in x.get("equipmentIds",[]): add(rows,seen,"equipment",ident,x["regionId"],x.get("allegiancePolityId") or "unaffiliated")
    for path in sorted((SCENARIO/"settlements").glob("*.json")):
        for x in read(path).get("settlements",[]):
            region=path.stem.rsplit("-1450",1)[0].replace("-","_")
            add(rows,seen,"settlement",x["id"],region,x.get("polityId","unaffiliated"))
    progression=read(SCENARIO/"progression/catalog.json")
    for x in progression.get("unlockReferences",[]):
        if x["kind"] in {"building","ability","unit"}: add(rows,seen,x["kind"],x["id"])
    treasure=read(SCENARIO/"treasures/age-of-sail.json")
    for x in treasure["treasures"]: add(rows,seen,"treasure",x["id"],(x.get("anchorRegionIds") or ["global"])[0])
    for pool in treasure["rewardPools"]:
        for entry in pool["entries"]:
            for outcome in entry["outcomes"]:
                if outcome["type"] == "inventory": add(rows,seen,"equipment",outcome["itemId"])
    for ident in ("selection_ring","movement_destination","quest_marker","regional_transition","settlement_nameplate","campaign_portrait_frame","inventory_slot","technology_button"):
        add(rows,seen,"ui_concept",ident)
    for path in sorted((SCENARIO/"terrain").glob("*.json")):
        data=read(path); region=data["regionId"]
        for collection in ("surfaces","waterBodies","linearFeatures","chokepoints","crossings","landmarks"):
            for x in data.get(collection,[]): add(rows,seen,"terrain_feature",x["id"],region)
    for ident in ("recruitment_spawn","settlement_capture","treasure_reveal","broadside_impact","research_complete","regional_transition_fade","regional_ambient_sound"):
        add(rows,seen,"effect",ident)
    return sorted(rows,key=lambda x:(x["kind"],x["region"],x["polity"],x["id"]))

def choice(entity):
    kind=entity["kind"]; ident=entity["id"]
    object_assets={"hfoo":"human_footman","hkni":"human_knight","hmtm":"human_mortar_team","hrif":"human_rifleman","hbot":"human_transport_ship","hbsh":"human_battleship"}
    if kind == "runtime_template": return object_assets.get(entity.get("objectId"),"human_footman"),"final_stock_fit",1,"Runtime object ID is pinned directly to stock data.","Fantasy costume or hull details remain."
    if kind in {"ship"}: return "human_transport_ship","temporary_placeholder",1,"Sailing silhouette reads clearly at gameplay zoom.","Stock hull does not identify rig, region, or period precisely."
    if kind == "unit": return "human_footman","acceptable_stock_variation",2,"Human scale, team color, and combat motion remain readable.","Armor and weapons are often European fantasy approximations."
    if kind == "character": return "human_footman","custom_model_candidate",1,"Stock humanoid provides a functional selection silhouette.","Named people require culturally and chronologically distinct portraits/models."
    if kind == "settlement": return "human_town_hall","acceptable_stock_variation",2,"Large civic silhouette and team color communicate ownership.","Architecture is western-European fantasy and cannot carry regional identity alone."
    if kind == "building": return "human_town_hall","custom_model_candidate",2,"Civic footprint is legible.","One hall cannot distinguish specialist institutions."
    if kind in {"equipment","treasure"}:
        priority = 3 if kind == "treasure" and ident.startswith("secret_") and ident != "secret_pacific_wreck_salvage" else 2
        return "treasure_chest","custom_icon_texture_candidate",priority,"Ground pickup is unmistakable.","Chest does not depict the authored object; dedicated icon is needed."
    if kind == "ability": return "spell_effect","custom_icon_texture_candidate",3,"Brief effect is visible without obscuring formations.","Holy fantasy language mismatches most mundane abilities."
    if kind == "effect": return "spell_effect","temporary_placeholder",2,"Strong transient feedback at world-map scale.","Magic glow is unsuitable for mundane artillery, research, and travel feedback."
    if kind == "terrain_feature": return "terrain_lordaeron_summer","acceptable_stock_variation",3,"Stock terrain remains performant and readable.","A single temperate texture cannot express all climates and landforms."
    if kind == "ui_concept": return None,"intentionally_invisible_data_only",4,"Concept is layout/data-only until the later interface visual-language pass.","No independent world asset is appropriate."
    raise AssertionError(kind)

def mapping(entity, index):
    asset, classification, priority, strength, mismatch=choice(entity)
    if entity["id"] == "regional_ambient_sound":
        asset, classification, priority = "ship_wood_sound", "sound_candidate", 2
        strength, mismatch = "Stock ship audio supplies immediate maritime feedback.", "A single boat set cannot represent regional ports, weather, or inland ambience."
    footprints={"human_footman":{"width":32,"height":32},"human_knight":{"width":48,"height":48},"human_mortar_team":{"width":48,"height":48},"human_rifleman":{"width":32,"height":32},"human_transport_ship":{"width":96,"height":96},"human_battleship":{"width":128,"height":128},"human_town_hall":{"width":160,"height":160},"treasure_chest":{"width":32,"height":32},"spell_effect":{"width":0,"height":0},"terrain_lordaeron_summer":{"width":128,"height":128},"ship_wood_sound":{"width":0,"height":0}}
    animations={"human_footman":["stand","walk","attack","death"],"human_knight":["stand","walk","attack","death"],"human_mortar_team":["stand","walk","attack","death"],"human_rifleman":["stand","walk","attack","death"],"human_transport_ship":["stand","walk","death"],"human_battleship":["stand","walk","attack","death"],"human_town_hall":["stand","birth","death"],"treasure_chest":["stand","death"],"spell_effect":["birth","stand","death"],"terrain_lordaeron_summer":[]}
    variation={"renderers":["classic","reforged"],"scale":1,"tint":asset not in {"spell_effect","terrain_lordaeron_summer","ship_wood_sound"},"attachments":[],"animations":animations.get(asset,[]),"footprint":footprints.get(asset,{"width":0,"height":0})}
    if not asset: variation={"renderers":[],"scale":1,"tint":False,"attachments":[],"animations":[],"footprint":{"width":0,"height":0}}
    return {"id":f"fit_{index:04d}","entityKind":entity["kind"],"entityId":entity["id"],"region":entity["region"],"polity":entity["polity"],"candidateAssetId":asset,"classification":classification,"historicalPeriod":"1450-1820","culturalApplicability":[entity["region"]],"readabilityStrengths":strength,"knownMismatches":mismatch,"permittedVariation":variation,"replacementPriority":priority}

def build():
    return {"format":"historical_fit_matrix_v1","scenario":"age_of_sail_world","boundedExceptions":[{"scope":"quest dialogue, policies, modifiers, professions, traits, technologies, institutions, and abstract economy resources","reason":"No independent runtime representation is authored; visual mapping begins if a runtime template or visible UI object is introduced."}],"mappings":[mapping(x,i+1) for i,x in enumerate(entities())]}

if __name__ == "__main__":
    target=SCENARIO/"visuals/historical-fit.json"; target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(build(),indent=2,sort_keys=True)+"\n",encoding="utf-8")

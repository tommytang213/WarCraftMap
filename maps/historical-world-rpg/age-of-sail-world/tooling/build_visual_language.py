#!/usr/bin/env python3
"""Build the scenario-owned country/unit visual language and stable previews."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "scenario"
REGION_FILES = {
    "europe":"europe-africa-middle-east-india.json", "africa":"europe-africa-middle-east-india.json",
    "middle_east_india":"europe-africa-middle-east-india.json",
    "southeast_asia":"southeast-east-asia-pacific.json", "east_asia":"southeast-east-asia-pacific.json",
    "pacific":"southeast-east-asia-pacific.json", "americas_caribbean":"americas-caribbean.json"}
TARGET_REGIONS = ("southeast_asia", "east_asia", "pacific", "americas_caribbean")

class VisualDataError(ValueError): pass

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def polities():
    answer = {}
    for path in sorted((SCENARIO / "politics").glob("*.json")):
        data = load(path); region = path.stem.rsplit("-1450", 1)[0].replace("-", "_")
        for row in data.get("polities", []): answer[row["id"]] = region
    return answer

def roster_data():
    merged, assignments = {}, []
    for path in sorted((SCENARIO / "rosters").glob("*.json")):
        data = load(path)
        for row in data.get("archetypes", []): merged[row["id"]] = row
        assignments += data.get("assignments", [])
    # Resolve inheritance only for the visual fields used here.
    def resolve(ident, trail=()):
        if ident in trail: raise ValueError("cyclic archetype inheritance")
        row = merged[ident]
        base = resolve(row["extends"], trail+(ident,)) if row.get("extends") in merged else {}
        return {**base, **row}
    return {k:resolve(k) for k in merged}, assignments

def ships():
    answer = {}
    for path in sorted((SCENARIO / "rosters").glob("*.json")):
        for row in load(path).get("ships", []): answer[row["id"]] = row
    return answer

def family(region, row):
    ident=row["id"]; category=row.get("category", "infantry")
    if row.get("shipId") or category in {"transport","merchant","warship"}: return f"{region}_maritime"
    if "elephant" in ident: return "southeast_asian_elephant"
    if category == "cavalry": return f"{region}_mounted"
    if category == "artillery": return f"{region}_gunpowder"
    if category in {"specialist","marine"}: return f"{region}_specialist"
    return f"{region}_land"

def asset_for(row):
    ident=row["id"]; category=row.get("category", "infantry")
    if row.get("shipId") or category in {"transport","merchant","warship"}:
        return "human_battleship" if category == "warship" else "human_transport_ship"
    if category == "artillery": return "human_mortar_team"
    if category == "cavalry": return "human_knight"
    if any(x in ident for x in ("matchlock","arqueb","musk","handgun","ranger")): return "human_rifleman"
    return "human_footman"

def build():
    polity_regions=polities(); archetypes, authored=roster_data()
    pairs=set()
    for assignment in authored:
        for polity in assignment["polityIds"]:
            for archetype in assignment["archetypeIds"]: pairs.add((polity,archetype))
    # Ordinary roster families are coverage contracts for every authored polity.
    families=load(SCENARIO/"rosters/global-roster-families.json")["families"]
    for fam in families:
        region=fam["politySource"].rsplit("-1450.json",1)[0].replace("-","_")
        for polity,r in polity_regions.items():
            if r == region:
                for archetype in fam["archetypeIds"]: pairs.add((polity,archetype))
    rows=[]
    family_ids=set()
    for polity,ident in sorted(pairs):
        row=archetypes[ident]; region=polity_regions[polity]; fid=family(region,row); family_ids.add(fid)
        availability=row.get("availability",{}); start=availability.get("historicalStartYear",1450)
        baseline={"assetId":asset_for(row),"scale":1.0,"attachments":[],"animationProfile":"ship" if row.get("shipId") else "land"}
        progression=[]
        if start>1450:
            progression.append({**baseline,"fromYear":start,"technologyIds":row.get("technologyIds",[])})
        rows.append({"polityId":polity,"regionId":region,"archetypeId":ident,"familyId":fid,
            "paletteId":f"palette_{polity}","culturalMarkingId":f"marking_{fid}","availableFromYear":start,
            "baseline":baseline,"progression":progression,"evidenceIds":[x["id"] for x in load(SCENARIO/"rosters"/REGION_FILES[region]).get("historicalEvidence",[])][:2]})
    chars=[]; requirements=[]
    for char in sorted(load(SCENARIO/"characters/global.json")["characters"],key=lambda x:x["id"]):
        region=char["regionId"]; cid=char["id"]
        chars.append({"characterId":cid,"polityId":char.get("allegiancePolityId"),"regionId":region,
            "assetId":"human_footman","iconAssetId":"human_footman_icon","portraitAssetId":"human_footman_portrait",
            "paletteId":f"palette_{char.get('allegiancePolityId') or region}","productionRequirementId":f"character_{cid}_identity"})
        requirements.append({"id":f"character_{cid}_identity","entityKind":"character","entityId":cid,
            "priority":"high","type":"custom_icon_texture_model","fallbackAssetIds":["human_footman","human_footman_icon","human_footman_portrait"],
            "acceptance":"Preserve the named person's period, culture, profession, and readable gameplay silhouette."})
    doc={"format":"age_of_sail_visual_language_v1","scenario":"age_of_sail_world",
        "policy":{"teamColorSource":"controller","importedUnitsRetainCulturalMarkings":True,"fallbackFamilyId":"global_shared_land",
          "attachments":"Only catalogue-declared attachment points are legal; current stock pass uses none.",
          "historicalBaselineYear":1450,"maxActiveVisualObjects":256},
        "families":[{"id":x,"sharedMechanicsDoNotImplySharedIdentity":True} for x in sorted(family_ids|{"global_shared_land"})],
        "rosterAssignments":rows,
        "shipAssignments":[{"shipId":x["id"],"assetId":"human_battleship" if x["category"]=="warship" else "human_transport_ship",
            "animationProfile":"ship","scale":1.0,"attachments":[],"status":"final_stock_assignment"}
            for x in sorted(ships().values(),key=lambda x:x["id"])],
        "characterAssignments":chars,"productionRequirements":requirements,
        "evidence":sum((load(SCENARIO/"rosters"/name).get("historicalEvidence",[]) for name in sorted(set(REGION_FILES.values()))),[])}
    return doc

def snapshots(document):
    return [{"label":f"{x['regionId']}::{x['polityId']}::{x['archetypeId']}::1450",
             "familyId":x["familyId"],"assetId":x["baseline"]["assetId"],"paletteId":x["paletteId"]}
            for x in document["rosterAssignments"]]

def previews(document):
    return {region:[{"label":f"{x['polityId']} / {x['archetypeId']}","familyId":x["familyId"],"assetId":x["baseline"]["assetId"]}
        for x in document["rosterAssignments"] if x["regionId"]==region] for region in TARGET_REGIONS}

def validate(document, catalogue):
    assets={x["id"]:x for x in catalogue["assets"]}; families={x["id"] for x in document["families"]}
    refs=[(x["polityId"],x["archetypeId"]) for x in document["rosterAssignments"]]
    if len(refs)!=len(set(refs)): raise VisualDataError("ambiguous roster assignment")
    requirements={x["id"] for x in document["productionRequirements"]}
    for row in document["rosterAssignments"]:
        if row["familyId"] not in families: raise VisualDataError("missing family")
        if row["availableFromYear"] < document["policy"]["historicalBaselineYear"]: raise VisualDataError("invalid unit period")
        for visual in [row["baseline"],*row.get("progression",[])]:
            asset=assets.get(visual["assetId"])
            if not asset: raise VisualDataError("invalid asset")
            if not asset["scale"]["min"] <= visual["scale"] <= asset["scale"]["max"]: raise VisualDataError("unsafe scale")
            if not set(visual["attachments"]) <= set(asset["attachmentPoints"]): raise VisualDataError("unsafe attachment")
    for row in document["shipAssignments"]:
        if row["assetId"] not in assets: raise VisualDataError("invalid ship asset")
    for row in document["characterAssignments"]:
        if row.get("productionRequirementId") not in requirements: raise VisualDataError("undeclared high-priority character placeholder")
        if not {row["assetId"],row["iconAssetId"],row["portraitAssetId"]} <= set(assets): raise VisualDataError("invalid character asset")
    return True

if __name__ == "__main__":
    doc=build(); target=SCENARIO/"visuals"; reports=target/"reports"
    validate(doc,load(ROOT.parent/"_shared/assets/warcraft-3.0-stock.json"))
    (target/"country-unit-language.json").write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n")
    (reports/"global-visual-snapshot.json").write_text(json.dumps(snapshots(doc),indent=2,sort_keys=True)+"\n")
    (reports/"regional-preview-scenes.json").write_text(json.dumps(previews(doc),indent=2,sort_keys=True)+"\n")

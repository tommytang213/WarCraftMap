#!/usr/bin/env python3
"""Validate and report the Phase 8 player-use catalogue deterministically."""
from __future__ import annotations
import json, sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SHARED=ROOT.parent/"_shared"/"engine"
sys.path.insert(0,str(SHARED))
import player_items

REGIONS=("europe","africa","middle_east_india","southeast_asia","east_asia","americas_caribbean","pacific")
ERAS=(1450,1550,1650,1750,1820)

def _all_ids(value):
    found=set()
    if isinstance(value,dict):
        if isinstance(value.get("id"),str): found.add(value["id"])
        for child in value.values(): found.update(_all_ids(child))
    elif isinstance(value,list):
        for child in value: found.update(_all_ids(child))
    return found

def scenario_references():
    def ids(*paths):
        result=set()
        for path in paths: result.update(_all_ids(json.loads((ROOT/path).read_text())))
        return result
    return {
      "regions":set(REGIONS),
      "cultures":{"portuguese","english","scottish","french","german","italian","maghrebi","sahelian","ethiopian","swahili","ottoman","persian","rajput","deccani"},
      "controllers":ids("scenario/politics/europe-1450.json","scenario/politics/africa-1450.json","scenario/politics/middle-east-india-1450.json")|{"mysore_kingdom"},
      "technologies":ids("scenario/progression/catalog.json"),
      "institutions":ids("scenario/progression/catalog.json"),
      "quests":ids("scenario/campaign-quests.json")|{"circumnavigation_legacy"},
      "events":ids("scenario/historical-events.json"),
      "settlements":ids("scenario/settlements/europe-1450.json","scenario/settlements/africa-1450.json","scenario/settlements/middle-east-india-1450.json")}

def build_report(data):
    player_items.validate_catalog(data); items=data["items"]
    by_region=Counter(); by_era=Counter(); by_arch=Counter(); by_slot=Counter(); by_level=Counter(); by_prov=Counter(); by_set=Counter(); by_rarity=Counter(); by_category=Counter(); by_unique=Counter(); by_settlement=Counter()
    for item in items:
        regions=item["requirements"].get("regionIds",REGIONS)
        by_region.update(regions); by_arch.update(item["merchant"].get("archetypeIds",[])); by_slot.update(item["comparison"].get("slotIds",[]) or ["none"])
        by_rarity[item["rarityId"]]+=1; by_prov[item["provenance"]["kind"]]+=1
        by_category[item["category"]]+=1; by_unique["singular" if item["unique"] else "ordinary"]+=1
        by_settlement.update(item["merchant"].get("settlementIds",[]) or ["not_restricted"])
        by_level[f"{((item['itemLevel']-1)//50)*50+1}-{((item['itemLevel']-1)//50+1)*50}"]+=1
        if item["comparison"].get("setId"): by_set[item["comparison"]["setId"]]+=1
        for year in ERAS:
            if item["requirements"].get("startYear",1450)<=year<=item["requirements"].get("endYear",1820): by_era[str(year)]+=1
    return {"schemaVersion":1,"status":"pass","scope":"Europe, Africa, and Middle East-India first regional slice; global target remains open","catalogueTargetComplete":False,"itemCount":len(items),"uniqueCount":sum(x["unique"] for x in items),"byRegion":dict(sorted(by_region.items())),"byEra":dict(sorted(by_era.items())),"byArchetype":dict(sorted(by_arch.items())),"bySlot":dict(sorted(by_slot.items())),"byCategory":dict(sorted(by_category.items())),"byRarity":dict(sorted(by_rarity.items())),"byLevelBand":dict(sorted(by_level.items())),"byProvenance":dict(sorted(by_prov.items())),"bySet":dict(sorted(by_set.items())),"bySettlementRestriction":dict(sorted(by_settlement.items())),"byUniqueClass":dict(sorted(by_unique.items()))}

def main():
    source=ROOT/"scenario/inventory/player-use-catalog.json"; report=ROOT/"scenario/inventory/reports/catalogue-coverage.json"
    data=json.loads(source.read_text()); player_items.validate_catalog_references(data,scenario_references()); built=build_report(data); report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(built,indent=2,sort_keys=True)+"\n"); print(json.dumps(built,sort_keys=True))
if __name__=="__main__": main()

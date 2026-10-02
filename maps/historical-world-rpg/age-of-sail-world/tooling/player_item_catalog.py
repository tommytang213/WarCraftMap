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

def build_report(data):
    player_items.validate_catalog(data); items=data["items"]
    by_region=Counter(); by_subregion=Counter(); by_era=Counter(); by_arch=Counter(); by_slot=Counter(); by_level=Counter(); by_prov=Counter(); by_set=Counter(); by_rarity=Counter(); by_category=Counter(); by_historical_class=Counter()
    for item in items:
        regions=item["requirements"].get("regionIds",REGIONS)
        by_region.update(regions); by_subregion.update(item.get("coverage",{}).get("subregionIds",["global_or_foundation"])); by_arch.update(item["merchant"].get("archetypeIds",[])); by_slot.update(item["comparison"].get("slotIds",[]) or ["none"])
        by_category[item["category"]]+=1; by_historical_class[item.get("coverage",{}).get("historicalClass","foundation")]+=1
        by_rarity[item["rarityId"]]+=1; by_prov[item["provenance"]["kind"]]+=1
        by_level[f"{((item['itemLevel']-1)//50)*50+1}-{((item['itemLevel']-1)//50+1)*50}"]+=1
        if item["comparison"].get("setId"): by_set[item["comparison"]["setId"]]+=1
        for year in ERAS:
            if item["requirements"].get("startYear",1450)<=year<=item["requirements"].get("endYear",1820): by_era[str(year)]+=1
    return {"schemaVersion":1,"status":"pass","catalogueTargetComplete":False,"itemCount":len(items),"uniqueCount":sum(x["unique"] for x in items),"byRegion":dict(sorted(by_region.items())),"bySubregion":dict(sorted(by_subregion.items())),"byEra":dict(sorted(by_era.items())),"byArchetype":dict(sorted(by_arch.items())),"bySlot":dict(sorted(by_slot.items())),"byCategory":dict(sorted(by_category.items())),"byRarity":dict(sorted(by_rarity.items())),"byLevelBand":dict(sorted(by_level.items())),"byProvenance":dict(sorted(by_prov.items())),"bySet":dict(sorted(by_set.items())),"byHistoricalItemClass":dict(sorted(by_historical_class.items()))}

def main():
    source=ROOT/"scenario/inventory/player-use-catalog.json"; report=ROOT/"scenario/inventory/reports/catalogue-coverage.json"
    data=json.loads(source.read_text()); built=build_report(data); report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(built,indent=2,sort_keys=True)+"\n"); print(json.dumps(built,sort_keys=True))
if __name__=="__main__": main()

#!/usr/bin/env python3
"""Compose and report authoritative release-scale hero progression."""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine")); sys.path.insert(0,str(ROOT/"tooling"))
from hero_progression import HeroProgressionRuntime
from global_characters import equipment_catalog, load_source

SOURCE=ROOT/"scenario/progression/hero-progression.json"
REPORT=ROOT/"scenario/characters/reports/progression-coverage.json"

def load_catalog():
    catalog=json.loads(SOURCE.read_text()); source=load_source()
    role_skill={"commander":"command","admiral":"navigation","navigator":"navigation","explorer":"navigation","diplomat":"diplomacy","governor":"administration","sovereign":"administration","engineer":"engineering","scholar":"scholarship","merchant":"commerce","adviser":"diplomacy"}
    role_mastery={"commander":"land_warfare","admiral":"sea_command","navigator":"wayfinding","explorer":"wayfinding","diplomat":"statecraft","governor":"statecraft","sovereign":"statecraft","engineer":"learned_arts","scholar":"learned_arts","merchant":"enterprise","adviser":"statecraft"}
    for character in source["characters"]:
        start=int(character["availabilityWindow"]["startDate"][:4]); career=max(1,int(character["availabilityWindow"]["endDate"][:4])-start+1)
        # Accomplished later entrants start higher, using date, career span, role breadth,
        # reputation (authored historical status), and campaign-era advancement.
        level=min(180,20+(start-1450)*22//100+min(50,career//2)+5*len(character["roleIds"]))
        skills=[]; masteries=[]
        for role in character["roleIds"]:
            sid=role_skill[role]; mid=role_mastery[role]
            if sid not in {x["skillId"] for x in skills}: skills.append({"skillId":sid,"rank":min(90,25+level//2)})
            if mid not in {x["masteryId"] for x in masteries}: masteries.append({"masteryId":mid,"rank":min(75,15+level//3)})
        martial=bool(set(character["roleIds"])&{"commander","admiral"}); discovery=bool(set(character["roleIds"])&{"navigator","explorer","engineer","scholar"})
        unlocks=[{"kind":"quest","id":character["questHookIds"][0]}]
        unlocks += [{"kind":"event","id":x} for x in character["eventHookIds"]]
        unlocks += [{"kind":"item","id":x} for x in character["equipmentIds"]]
        unlocks += [{"kind":"office","id":x} for x in character["officeEligibility"]]
        unlocks += [{"kind":"command","id":x} for x in character["commandEligibility"]]
        catalog["characterProfiles"].append({"id":character["id"],"startingLevel":level,"startingSkills":skills,"startingMasteries":masteries,
            "personalTreeId":"martial_signature" if martial else "discovery_signature" if discovery else "civic_signature",
            "startingLocationId":character["locationRules"][0]["locationId"],"scenarioUnlocks":unlocks,
            "startingBasis":{"campaignYear":start,"careerYears":career,"roleIds":character["roleIds"],"reputationClass":"authored_historical"}})
    return catalog,source

def build_report(catalog,source):
    profiles={x["id"]:x for x in catalog["characterProfiles"]}; chars={x["id"]:x for x in source["characters"]}
    band=lambda n: "001_049" if n<50 else "050_099" if n<100 else "100_199" if n<200 else "200_300"
    dimensions={"region":Counter(),"era":Counter(),"role":Counter(),"levelBand":Counter(),"skill":Counter(),"mastery":Counter(),"personalTree":Counter(),"assignment":Counter({"reserve":len(profiles)}),"evidenceClass":Counter({"authored_historical":len(profiles)})}
    for ident,p in profiles.items():
        c=chars[ident]; dimensions["region"][c["regionId"]]+=1; dimensions["era"][c["availabilityWindow"]["startDate"][:2]+"00s"]+=1; dimensions["levelBand"][band(p["startingLevel"])]+=1; dimensions["personalTree"][p["personalTreeId"]]+=1
        for x in c["roleIds"]: dimensions["role"][x]+=1
        for x in p["startingSkills"]: dimensions["skill"][x["skillId"]]+=1
        for x in p["startingMasteries"]: dimensions["mastery"][x["masteryId"]]+=1
    return {"format":"warcraftmap_hero_progression_coverage_v1","status":"pass","characterCount":len(profiles),"levelCap":catalog["levelCap"],"localFieldBudget":32,"dimensions":{k:dict(sorted(v.items())) for k,v in dimensions.items()}}

def main(argv=None):
    catalog,source=load_catalog(); quests={q["id"] for q in source["personalQuests"]}; world=json.loads((ROOT/"scenario/world/world.json").read_text())
    HeroProgressionRuntime(catalog,[x["id"] for x in source["characters"]],quest_ids=quests,
        event_ids={x["id"] for x in world["events"]},item_ids=equipment_catalog(),
        office_ids={"sovereign","settlement_administrator","province_governor","army_commander","fleet_commander"},command_ids={"army","fleet"})
    report=build_report(catalog,source)
    if argv is None: argv=sys.argv[1:]
    if argv==["--write"]: REPORT.write_text(json.dumps(report,indent=2)+"\n")
    elif argv: raise SystemExit("usage: hero_progression_catalog.py [--write]")
    elif not REPORT.exists() or json.loads(REPORT.read_text())!=report: raise SystemExit("progression report is stale; run --write")
    print(f"Hero progression valid: {len(catalog['characterProfiles'])} characters, level cap 300")

if __name__=="__main__": main()

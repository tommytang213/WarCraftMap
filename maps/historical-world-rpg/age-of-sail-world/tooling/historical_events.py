#!/usr/bin/env python3
"""Validate and deterministically project Age of Sail historical event data."""
from __future__ import annotations
import argparse, copy, json, re
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"scenario"/"historical-events.json"
WORLD=ROOT/"scenario"/"world"/"world.json"
ID=re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
KINDS={"polity":"polities","province":"provinces","settlement":"settlements","technology":"technologies","institution":"institutions","character":"characters","navigation_zone":"navigationZones"}
CATEGORIES={"political","diplomatic","military","exploration","commercial","institutional","technological","religious","environmental","social","succession"}
CONDITIONS={"entity_exists","entity_absent","owner_is","war_active","war_inactive","research_completed","research_missing"}
EFFECTS={"adjust_treasury","adjust_relations","set_controller","complete_research","set_flag","adjust_prosperity"}

def load(path): return json.loads(path.read_text(encoding="utf-8"))
def validate(source,world):
    assert source.get("schemaVersion")==1 and source.get("campaignRange")==["1450-01-01","1820-12-31"]
    indexes={k:{x["id"] for x in world[v]} for k,v in KINDS.items()}
    all_entities=set().union(*indexes.values())
    ids=set()
    for event in source["events"]:
        ident=event["id"]; assert ID.fullmatch(ident) and ident not in ids; ids.add(ident)
        when=date.fromisoformat(event["date"]); assert date(1450,1,1)<=when<=date(1820,12,31)
        assert isinstance(event["priority"],int) and event["categories"] and set(event["categories"])<=CATEGORIES
        assert event["evidence"].strip() and event["region"] in {"global","europe","africa","middle_east_india","southeast_asia","east_asia","americas_caribbean","pacific"}
        seen=set()
        for kind,ref in event["refs"]:
            assert kind in indexes and ref in indexes[kind] and (kind,ref) not in seen; seen.add((kind,ref))
        alternatives=event["alternatives"]; assert alternatives and len({x["id"] for x in alternatives})==len(alternatives)
        for alt in alternatives:
            assert ID.fullmatch(alt["id"]) and isinstance(alt["weight"],int) and alt["weight"]>0 and alt["effects"]
            assert all(x["kind"] in CONDITIONS for x in alt["conditions"])
            assert all(x["kind"] in EFFECTS for x in alt["effects"])
            for condition in alt["conditions"]:
                kind,target=condition["kind"],condition.get("entityId")
                if kind in {"entity_exists","entity_absent"}: assert target in all_entities
                elif kind=="owner_is": assert target in indexes["province"] and condition.get("valueId") in indexes["polity"]
                elif kind in {"research_completed","research_missing"}: assert target in indexes["technology"]|indexes["institution"]
                else: assert ID.fullmatch(condition.get("valueId", ""))
            for effect in alt["effects"]:
                kind,target=effect["kind"],effect.get("targetId")
                if kind in {"adjust_prosperity","set_controller"}: assert target in indexes["province"]
                if kind=="set_controller": assert effect.get("value") in indexes["polity"]
                if kind=="adjust_treasury": assert target in indexes["polity"]
                if kind=="adjust_relations": assert len(effect.get("targetIds",[]))==2 and all(x in indexes["polity"] for x in effect["targetIds"])
                if kind=="complete_research": assert target in indexes["technology"]|indexes["institution"]
                if kind=="set_flag": assert ID.fullmatch(target or "")
        rule=event.get("recurrence")
        if rule: assert rule["unit"] in {"days","months","years"} and rule["interval"]>0 and when<=date.fromisoformat(rule["untilDate"])<=date(1820,12,31)
    # Selective coverage: every pressure class, represented region, and century.
    assert CATEGORIES<=set().union(*(set(x["categories"]) for x in source["events"]))
    required_regions={"europe","africa","middle_east_india","southeast_asia","east_asia","americas_caribbean","pacific"}
    assert required_regions<={x["region"] for x in source["events"]}
    assert all(sum(x["region"]==region for x in source["events"])>=4 for region in required_regions)
    assert len(source["events"])>=36
    assert {14,15,16,17,18}<={date.fromisoformat(x["date"]).year//100 for x in source["events"]}

def project(source,world):
    result=copy.deepcopy(world)
    result["events"]=[]; definitions=[]; schedules=[]
    for item in source["events"]:
        refs=[{"kind":kind,"id":ident} for kind,ident in item["refs"]]
        historical={k:copy.deepcopy(v) for k,v in item.items() if k not in {"id","date","priority","recurrence","refs"}}
        result["events"].append({"id":item["id"],"title":item["id"].replace("_"," ").title(),"repeatable":"recurrence" in item,
          "triggers":[{"id":"scheduled","conditionId":"historical_state_allows","entityRefs":refs}],"prerequisites":[],
          "outcomes":[{"id":"apply_pressure","kind":"scenario_outcome","outcomeId":"resolve_historical_pressure","entityRefs":refs}],"historical":historical})
        definitions.append({"id":item["id"]})
        schedule={"id":f"schedule_{item['id']}","eventId":item["id"],"firstDate":item["date"],"priority":item["priority"],"eraId":"early_modern"}
        if "recurrence" in item: schedule["recurrence"]=copy.deepcopy(item["recurrence"])
        schedules.append(schedule)
    result["events"].sort(key=lambda x:x["id"]); result["timeline"]["eventDefinitions"]=definitions; result["timeline"]["schedules"]=schedules
    return result

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--write",action="store_true"); args=parser.parse_args()
    source,world=load(SOURCE),load(WORLD); validate(source,world); expected=project(source,world)
    if args.write: WORLD.write_text(json.dumps(expected,indent=2)+"\n",encoding="utf-8")
    elif expected!=world: raise SystemExit("historical event projection is stale; run tooling/historical_events.py --write")
    print(f"validated {len(source['events'])} historical events")
if __name__=="__main__": main()

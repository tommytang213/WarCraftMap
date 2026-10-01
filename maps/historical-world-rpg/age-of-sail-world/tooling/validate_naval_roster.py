#!/usr/bin/env python3
"""Validate Phase 8 naval coverage, fleet fixtures, integrations and budgets."""
import argparse, json, sys
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"tooling"))
from validate_unit_roster import load_catalog
class NavalError(ValueError): pass
def read(path): return json.loads(path.read_text(encoding="utf-8"))
def validate(output=None):
    cfg=read(ROOT/"scenario/naval/phase8.json"); exp=read(ROOT/"scenario/rosters/naval-expansion.json"); cat=load_catalog()
    if cfg.get("format")!="age_of_sail_naval_phase8_v1": raise NavalError("unsupported format")
    naval={i:x for i,x in cat.archetypes.items() if x.get("category") in {"transport","merchant","warship"}}
    added={x["id"] for x in exp["archetypes"]}; hulls={x["id"] for x in exp["ships"]}; assigned=defaultdict(set)
    for polity,unit in cat.assignments:
        if unit in naval: assigned[polity].add(unit)
    required={"merchant","transport","patrol","raiding","boarding","coastal","riverine","galley_oared","sailing_warship","frigate_cruiser","line_of_battle","junk","dhow","canoe_proa_pirogue"}
    if set(cfg["families"])!=required: raise NavalError("incomplete family coverage")
    for key,ids in cfg["families"].items():
        if not ids or not set(ids)<=set(naval): raise NavalError(f"{key}: broken vessel reference")
    if not cfg["exceptions"]: raise NavalError("missing explicit exceptions")
    for region in cfg["regions"]:
        if not set(region["archetypeIds"])<=set(naval): raise NavalError(f"{region['id']}: broken vessel reference")
    for polity in cfg["majorPowers"]:
        if len(assigned[polity])<3: raise NavalError(f"{polity}: fewer than three naval vessels")
    supported=set()
    for evidence in exp["historicalEvidence"]:
        refs=set(evidence["supports"])
        if not refs<=added: raise NavalError(f"{evidence['id']}: broken evidence reference")
        supported|=refs
    sources={x["id"]:x for x in exp["archetypes"]}
    for unit in added:
        cursor=unit; seen=set()
        while cursor in sources and cursor not in seen and cursor not in supported:
            seen.add(cursor); cursor=sources[cursor].get("extends")
        if cursor not in supported: raise NavalError(f"{unit}: added vessel without direct or family evidence")
    fleet_report=[]
    for fleet in cfg["fleets"]:
        if not set(fleet["ships"])<=assigned[fleet["polityId"]]: raise NavalError(f"{fleet['id']}: unassigned vessel")
        objects=0
        for unit in fleet["ships"]:
            ok=cat.availability(unit,fleet["year"],set(fleet["technologies"]),country_id=fleet["polityId"],established_institution_ids=set(fleet.get("institutions",[])),equipment_ids=set(fleet.get("equipment",[])),reform_ids=set(fleet.get("reforms",[])),resource_ids=set(fleet.get("resources",[])),has_port=True)
            if not ok.available: raise NavalError(f"{fleet['id']}: {unit} unavailable")
            objects+=cat.templates[naval[unit]["runtimeTemplateId"]]["maxActiveObjects"]
        if objects>cfg["budgets"]["fleetObjects"]: raise NavalError(f"{fleet['id']}: object budget exceeded")
        fleet_report.append({"id":fleet["id"],"polityId":fleet["polityId"],"year":fleet["year"],"vessels":len(fleet["ships"]),"maximumRuntimeObjects":objects})
    refs=set(sum((cfg["integration"][k] for k in ("settlementDefense","trade","transport")),[]))
    if not refs<=set(naval): raise NavalError("broken integration vessel reference")
    traditions={x["id"] for x in read(ROOT/"scenario/military-traditions.json")["traditions"]}
    audio={x["id"] for x in read(ROOT/"scenario/audio/profiles.json")["profiles"]}
    if not set(cfg["integration"]["traditions"])<=traditions or not set(cfg["integration"]["audio"])<=audio: raise NavalError("broken integration reference")
    budget=cfg["budgets"]
    if len(added)>budget["addedArchetypes"] or len(hulls)>budget["addedHulls"] or len(cat.templates)>budget["runtimeTemplates"] or budget["addedImports"]!=0: raise NavalError("content budget exceeded")
    if {naval[x]["shipId"] for x in added}!=hulls: raise NavalError("unused added hull")
    report={"format":"age_of_sail_naval_coverage_report_v1","counts":{"navalArchetypes":len(naval),"addedArchetypes":len(added),"addedHulls":len(hulls),"runtimeTemplates":len(cat.templates),"addedImports":0},"families":cfg["families"],"regions":cfg["regions"],"exceptions":cfg["exceptions"],"majorPowers":{x:sorted(assigned[x]) for x in cfg["majorPowers"]},"fleets":fleet_report,"integration":cfg["integration"],"budgets":budget}
    if output: output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return report
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--output",type=Path); args=parser.parse_args()
    try: report=validate(args.output); print(f"Naval roster valid: {report['counts']['navalArchetypes']} vessels; {len(report['fleets'])} fleet fixtures")
    except (OSError,KeyError,TypeError,ValueError,json.JSONDecodeError) as error: print(f"Naval roster validation failed: {error}",file=sys.stderr); return 1
    return 0
if __name__=="__main__": raise SystemExit(main())

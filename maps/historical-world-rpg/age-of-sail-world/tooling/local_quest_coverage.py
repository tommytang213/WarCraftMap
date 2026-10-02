#!/usr/bin/env python3
"""Validate and report release-scale settlement-local random quest coverage."""
from __future__ import annotations
import argparse, json, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from local_quest import LocalQuestRuntime

SOURCE=ROOT/"scenario/local-random-quests.json"; WORLD=ROOT/"scenario/world/world.json"
REPORT=ROOT/"reports/local-quest-coverage.json"; HUMAN=ROOT/"reports/local-quest-coverage.md"
REGIONS=("americas_caribbean","middle_east_india","southeast_asia","east_asia","europe","africa","pacific")

def load(path): return json.loads(path.read_text())
def tier(row):
    n=LocalQuestRuntime.slot_count(row)
    return "remote" if n==1 else "small" if n==2 else "town" if n<=4 else "major_city" if n<=7 else "metropolis"

def build(seed="phase8_release_seed"):
    source=load(SOURCE); world=load(WORLD); settlements=world["settlements"]
    physical=load(ROOT/"physical-maps.json"); instance_region={}; instance_map={}
    for map_row in physical["physicalMaps"]:
        logical=map_row["assignments"].get("logicalRegionIds",[])
        for instance in map_row["assignments"].get("regionalInstanceIds",[]):
            instance_region[instance]=logical[0] if logical else "unknown"; instance_map[instance]=map_row["id"]
    runtime=LocalQuestRuntime(source,settlements,campaign_seed=seed)
    identical=LocalQuestRuntime(source,settlements,campaign_seed=seed).snapshot()==runtime.snapshot()
    alternate=LocalQuestRuntime(source,settlements,campaign_seed=seed+"_alternate").snapshot()
    current=runtime.snapshot(); changed=sum(a["familyId"]!=b["familyId"] or a["variantId"]!=b["variantId"] for a,b in zip(current["offers"],alternate["offers"]))
    by_id={x["id"]:x for x in settlements}; families={x["id"] for x in source["families"]}
    dimensions={name:defaultdict(lambda:{"settlements":set(),"offers":0}) for name in ("tier","region","polity","physicalMap","portFrontier","family")}
    failures=[]
    for settlement in settlements:
        board=runtime.board(settlement["id"]); expected=LocalQuestRuntime.slot_count(settlement)
        if len(board)!=expected: failures.append(f"{settlement['id']} has {len(board)} offers; expected {expected}")
        if not board: failures.append(f"ordinary playable settlement lacks an initial offer: {settlement['id']}")
        tags=LocalQuestRuntime.settlement_context(settlement)
        instance=settlement.get("regionalInstanceId","none")
        labels={"tier":tier(settlement),"region":instance_region.get(instance,"unknown"),"polity":settlement.get("controllerPolityId","none"),
                "physicalMap":instance_map.get(instance,"unknown"),"portFrontier":"port" if "port" in tags else "frontier" if "frontier" in tags else "inland"}
        for dimension,label in labels.items():
            dimensions[dimension][label]["settlements"].add(settlement["id"]); dimensions[dimension][label]["offers"]+=len(board)
        for offer in board:
            dimensions["family"][offer["familyId"]]["settlements"].add(settlement["id"]); dimensions["family"][offer["familyId"]]["offers"]+=1
    if not identical: failures.append("identical seeds do not reproduce allocations")
    if changed < len(settlements)//2: failures.append("different seeds produce suspiciously little bounded variety")
    used={x["familyId"] for x in current["offers"]}
    if used!=families: failures.append(f"families absent from campaign-start allocation: {sorted(families-used)}")
    rendered={}
    for dimension,rows in dimensions.items():
        rendered[dimension]={k:{"settlements":len(v["settlements"]),"offers":v["offers"],"average":round(v["offers"]/len(v["settlements"]),2)} for k,v in sorted(rows.items())}
    return {"schemaVersion":1,"status":"pass" if not failures else "fail","campaignSeed":seed,
      "catalogue":{"families":len(source["families"]),"variants":sum(len(x["variants"]) for x in source["families"]),
                   "categories":sorted({x["category"] for x in source["families"]})},
      "allocation":{"settlements":len(settlements),"offers":len(current["offers"]),"identicalSeedStable":identical,
                    "differentSeedChangedOffers":changed,"minimumPerOrdinarySettlement":1},
      "density":rendered,"failures":failures}

def markdown(r):
    lines=["# Settlement-local random quest coverage","",f"Result: **{r['status'].upper()}**","",
      "This report counts settlement-local authored families separately from campaign, regional, personal, polity, event-linked, treasure, and discovery content.","",
      f"{r['catalogue']['families']} families / {r['catalogue']['variants']} authored variants; {r['allocation']['offers']} persistent campaign-start offers across {r['allocation']['settlements']} settlements.","",
      "## Density by settlement tier","","| Tier | Settlements | Offers | Average |","|---|---:|---:|---:|"]
    for key,row in r["density"]["tier"].items(): lines.append(f"| {key} | {row['settlements']} | {row['offers']} | {row['average']} |")
    lines += ["","## Determinism and gates","",f"- Same-seed allocation stable: {r['allocation']['identicalSeedStable']}",f"- Offers changed under alternate seed: {r['allocation']['differentSeedChangedOffers']}"]
    lines += [f"- FAIL: {x}" for x in r["failures"]] or ["- Every ordinary settlement meets its contextual minimum; no exception allowlist is required."]
    return "\n".join(lines)+"\n"

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--write",action="store_true"); args=parser.parse_args()
    report=build(); human=markdown(report)
    if report["failures"]: raise SystemExit("local quest gate failed:\n- "+"\n- ".join(report["failures"]))
    if args.write: REPORT.write_text(json.dumps(report,indent=2)+"\n"); HUMAN.write_text(human)
    elif not REPORT.exists() or load(REPORT)!=report or not HUMAN.exists() or HUMAN.read_text()!=human: raise SystemExit("local quest reports are stale; run with --write")
    print(f"validated {report['allocation']['offers']} persistent local offers across {report['allocation']['settlements']} settlements")
if __name__=="__main__": main()

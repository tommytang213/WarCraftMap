#!/usr/bin/env python3
"""Validate and report the Phase 8 Europe/Africa historical-density pass."""
from __future__ import annotations
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/"reports/europe-africa-settlement-density.json"
HUMAN=ROOT/"reports/europe-africa-settlement-density.md"
LIMITS={"europe":{"minimum":150,"maximum":180,"maxPerPhysicalMap":110},"africa":{"minimum":80,"maximum":110,"maxPerPhysicalMap":110}}

class DensityError(ValueError): pass

def audit():
    result={"schemaVersion":1,"campaignStartDate":"1450-01-01","status":"complete","regions":{},"globalRoadmapComplete":False}
    all_ids=set(); all_names=set()
    for region in ("europe","africa"):
        source=json.loads((ROOT/f"scenario/settlements/{region}-1450.json").read_text())
        politics=json.loads((ROOT/f"scenario/politics/{region}-1450.json").read_text())
        rows=source["settlements"]; evidence={x["id"] for x in source.get("historicalEvidence",[])}
        by_instance=Counter(); by_map=Counter(); by_role=Counter(); by_polity=Counter(); source_positions=set()
        for row in rows:
            if row["id"] in all_ids: raise DensityError(f"duplicate global settlement ID: {row['id']}")
            folded=row["name"].casefold()
            if folded in all_names: raise DensityError(f"duplicate historical location name: {row['name']}")
            all_ids.add(row["id"]); all_names.add(folded)
            if not set(row.get("historicalEvidenceIds",[])) or not set(row["historicalEvidenceIds"])<=evidence: raise DensityError(f"{row['id']}: invalid historical evidence")
            control=row.get("controlContext",{})
            if control.get("date")!="1450-01-01" or control.get("status")!="legal_and_effective_control": raise DensityError(f"{row['id']}: invalid control context")
            expected="africa" if region=="africa" else "europe_west" if row["regionalInstanceId"] in {"europe_atlantic_isles","europe_iberia_western_med","europe_france_low_countries"} else "europe_central_east"
            if row.get("physicalMapId")!=expected: raise DensityError(f"{row['id']}: invalid physical-map assignment")
            pos=tuple(row.get("sourcePosition",()))
            if len(pos)!=2 or pos in source_positions: raise DensityError(f"{row['id']}: duplicate or missing historical coordinates")
            source_positions.add(pos); by_instance[row["regionalInstanceId"]]+=1; by_map[row["physicalMapId"]]+=1; by_polity[row["polityId"]]+=1; by_role.update(row["roles"])
        limits=LIMITS[region]
        if not limits["minimum"]<=len(rows)<=limits["maximum"]: raise DensityError(f"{region}: settlement count outside release-pass budget")
        if max(by_map.values())>limits["maxPerPhysicalMap"]: raise DensityError(f"{region}: active physical-map density budget exceeded")
        represented=set(by_polity)|{x.get("polityId") for x in source.get("abstractCommunities",[])}
        missing={p["id"] for p in politics["polities"]}-represented
        # Every polity needs at least one physical center; mobile/decentralized depth is
        # then represented by the explicit abstract-community records.
        if missing: raise DensityError(f"{region}: unjustified polity coverage gap: {sorted(missing)}")
        result["regions"][region]={"settlementCount":len(rows),"portCount":sum("port" in x for x in rows),"abstractCommunityCount":len(source.get("abstractCommunities",[])),"bySubregion":dict(sorted(by_instance.items())),"byPhysicalMap":dict(sorted(by_map.items())),"byRole":dict(sorted(by_role.items())),"byPolityImportance":[{"polityId":k,"settlementCount":v,"importance":"major" if v>=5 else "regional" if v>=2 else "localized"} for k,v in sorted(by_polity.items())],"budgets":{"catalogueLimit":limits["maximum"],"physicalMapLimit":limits["maxPerPhysicalMap"],"runtimePolicy":"abstract_until_regional_activation"}}
    return result

def markdown(report):
    lines=["# Europe and Africa settlement-density report","","Status: **COMPLETE**","","This regional Phase 8 pass preserves the global settlement-density roadmap item as incomplete. Counts follow historical density, not equal polity quotas; inactive settlements remain authoritative abstract state.",""]
    for region,data in report["regions"].items():
        lines += [f"## {region.title()}","",f"{data['settlementCount']} physical settlements, {data['portCount']} ports, and {data['abstractCommunityCount']} explicit abstract-community groups.","","| Subregion | Settlements |","|---|---:|"]+[f"| {k} | {v} |" for k,v in data["bySubregion"].items()]+["","| Role | Count |","|---|---:|"]+[f"| {k} | {v} |" for k,v in data["byRole"].items()]+[""]
    return "\n".join(lines)+"\n"

def main(argv=None):
    argv=sys.argv[1:] if argv is None else argv
    try: report=audit(); human=markdown(report)
    except (OSError,json.JSONDecodeError,DensityError) as e: print(f"Europe/Africa density validation failed: {e}",file=sys.stderr); return 1
    if argv==["--write"]: REPORT.write_text(json.dumps(report,indent=2)+"\n"); HUMAN.write_text(human)
    elif argv: print("usage: europe_africa_density.py [--write]",file=sys.stderr); return 1
    elif not REPORT.exists() or json.loads(REPORT.read_text())!=report or not HUMAN.exists() or HUMAN.read_text()!=human: print("Europe/Africa density reports are stale; run with --write",file=sys.stderr); return 1
    print(f"Europe/Africa density valid: {sum(x['settlementCount'] for x in report['regions'].values())} settlements")
    return 0
if __name__=="__main__": raise SystemExit(main())

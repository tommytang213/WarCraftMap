#!/usr/bin/env python3
"""Audit and report the release-scale Pacific settlement catalogue."""
import json,sys
from collections import Counter
from pathlib import Path
from pacific_content import validate
ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/"reports/pacific-settlement-density.json"; HUMAN=ROOT/"reports/pacific-settlement-density.md"
class DensityError(ValueError): pass
def audit():
 source,politics,_,_=validate(); rows=source["settlements"]
 if not 36<=len(rows)<=48: raise DensityError("Pacific catalogue is outside the reviewed sparse-island density budget")
 if len({x["name"].casefold() for x in rows})!=len(rows): raise DensityError("duplicate Pacific location name")
 centers={x["id"] for x in rows if "political_center" in x["roles"]}
 if {x["capitalSettlementId"] for x in politics["polities"]}-centers: raise DensityError("authority exception lacks a political center")
 by_group=Counter(x["regionalInstanceId"] for x in rows); by_map=Counter(x["physicalMapId"] for x in rows); by_role=Counter(r for x in rows for r in x["roles"]); by_authority=Counter(x["authorityType"] for x in rows); by_importance=Counter(x["routeImportance"] for x in rows)
 if max(by_group.values())>10 or max(by_map.values())>14: raise DensityError("island-map catalogue budget exceeded")
 if any(v<2 for v in by_group.values()): raise DensityError("island-group coverage gap")
 return {"schemaVersion":1,"campaignStartDate":"1450-01-01","status":"complete","globalRoadmapComplete":False,"settlementCount":len(rows),"portCount":sum("port" in x for x in rows),"abstractCommunityCount":len(source["abstractCommunities"]),"byIslandGroup":dict(sorted(by_group.items())),"byAuthorityType":dict(sorted(by_authority.items())),"bySettlementRole":dict(sorted(by_role.items())),"byRouteImportance":dict(sorted(by_importance.items())),"byPhysicalMap":dict(sorted(by_map.items())),"budgets":{"catalogueMaximum":48,"perIslandGroupMaximum":10,"perPhysicalMapMaximum":14,"runtimePolicy":"authoritative_abstract_until_local_region_activation"}}
def markdown(r):
 lines=["# Pacific settlement-density report","","Status: **COMPLETE**","","This regional Phase 8 pass preserves the global settlement-density roadmap item as incomplete. Physical locations follow island geography, voyaging networks, and historically appropriate authority structures; minor communities remain authoritative abstract state.","",f"{r['settlementCount']} locations, {r['portCount']} ports or anchorages, and {r['abstractCommunityCount']} abstract-community groups."]
 for title,key in (("Island group","byIslandGroup"),("Authority type","byAuthorityType"),("Settlement role","bySettlementRole"),("Route importance","byRouteImportance"),("Physical map","byPhysicalMap")):
  lines += ["",f"## By {title.lower()}","",f"| {title} | Count |","|---|---:|"]+[f"| {k} | {v} |" for k,v in r[key].items()]
 lines += ["","Runtime representation is local and bounded: inactive communities retain authoritative state without Warcraft objects, while regional activation reconstructs stable-ID representations.",""]
 return "\n".join(lines)
def main(argv=None):
 argv=sys.argv[1:] if argv is None else argv
 try: r=audit(); text=markdown(r)
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e: print(f"Pacific density validation failed: {e}",file=sys.stderr); return 1
 if argv==["--write"]: REPORT.write_text(json.dumps(r,indent=2)+"\n"); HUMAN.write_text(text)
 elif argv: print("usage: pacific_density.py [--write]",file=sys.stderr); return 1
 elif not REPORT.exists() or json.loads(REPORT.read_text())!=r or not HUMAN.exists() or HUMAN.read_text()!=text: print("Pacific density reports are stale; run with --write",file=sys.stderr); return 1
 print(f"Pacific density valid: {r['settlementCount']} locations"); return 0
if __name__=="__main__": raise SystemExit(main())

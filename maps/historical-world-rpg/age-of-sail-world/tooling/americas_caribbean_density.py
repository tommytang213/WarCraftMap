#!/usr/bin/env python3
"""Validate and report the Phase 8 Americas/Caribbean settlement-density pass."""
from __future__ import annotations
import json, sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/"reports/americas-caribbean-settlement-density.json"
HUMAN=ROOT/"reports/americas-caribbean-settlement-density.md"
class DensityError(ValueError): pass

def audit():
 source=json.loads((ROOT/"scenario/settlements/americas-caribbean-1450.json").read_text()); politics=json.loads((ROOT/"scenario/politics/americas-caribbean-1450.json").read_text())
 rows=source["settlements"]; polities={x["id"]:x for x in politics["polities"]}; by_sub=Counter(); by_map=Counter(); by_role=Counter(); by_polity=Counter(); by_authority=Counter(); by_era=Counter(); identities=set()
 if not 140<=len(rows)<=190: raise DensityError("catalogue is outside the locked release-scale range")
 for row in rows:
  identity=(row["name"].casefold(),tuple(row["sourcePosition"]));
  if identity in identities: raise DensityError(f"duplicate identity: {row['id']}")
  identities.add(identity); by_sub[row["regionalInstanceId"]]+=1; by_map[row["physicalMapId"]]+=1; by_role.update(row["roles"]); by_polity[row["polityId"]]+=1
  polity=polities[row["polityId"]]; by_authority[polity.get("structure","centralized")]+=1; by_era["available_1450" if row["availability"]["from"]<="1450-01-01" else "introduced_later"]+=1
 missing=set(polities)-set(by_polity)
 if missing: raise DensityError(f"missing polity/authority coverage: {sorted(missing)}")
 if max(by_map.values())>42: raise DensityError("physical-map settlement budget exceeded")
 if source.get("coverageRule")!="release_scale_historical_density_with_bounded_runtime_representation" or not source.get("abstractCommunities"): raise DensityError("inactive authoritative representation contract is missing")
 return {"schemaVersion":1,"campaignStartDate":"1450-01-01","status":"complete","globalRoadmapComplete":False,"settlementCount":len(rows),"portAndAnchorageCount":sum("port" in x for x in rows),"abstractCommunityCount":len(source["abstractCommunities"]),"bySubregion":dict(sorted(by_sub.items())),"byPolity":dict(sorted(by_polity.items())),"byAuthorityType":dict(sorted(by_authority.items())),"byRole":dict(sorted(by_role.items())),"byEraAvailability":dict(sorted(by_era.items())),"byPhysicalMap":dict(sorted(by_map.items())),"budgets":{"catalogueMaximum":190,"physicalMapMaximum":42,"activationPolicy":"abstract_until_regional_activation"}}

def markdown(r):
 lines=["# Americas and Caribbean settlement-density report","","Status: **COMPLETE**","","This regional release-scale pass preserves the global settlement-density roadmap item as incomplete. Counts represent Indigenous political, ceremonial, riverine, maritime, island, fortified, and production networks rather than modern borders or a uniform European city model.","",f"{r['settlementCount']} settlements, {r['portAndAnchorageCount']} ports/anchorages, and {r['abstractCommunityCount']} compressed community group.","","| Subregion / physical map | Count |","|---|---:|"]
 lines += [f"| {k} | {v} |" for k,v in r["bySubregion"].items()]+["","| Authority type | Count |","|---|---:|"]+[f"| {k} | {v} |" for k,v in r["byAuthorityType"].items()]+["","| Settlement role | Count |","|---|---:|"]+[f"| {k} | {v} |" for k,v in r["byRole"].items()]+[""]
 return "\n".join(lines).rstrip()+"\n"

def main(argv=None):
 argv=sys.argv[1:] if argv is None else argv
 try: report=audit(); human=markdown(report)
 except (OSError,json.JSONDecodeError,DensityError,KeyError) as e: print(f"Americas/Caribbean density validation failed: {e}",file=sys.stderr); return 1
 if argv==["--write"]: REPORT.write_text(json.dumps(report,indent=2)+"\n"); HUMAN.write_text(human)
 elif argv: print("usage: americas_caribbean_density.py [--write]",file=sys.stderr); return 1
 elif not REPORT.exists() or json.loads(REPORT.read_text())!=report or not HUMAN.exists() or HUMAN.read_text()!=human: print("Americas/Caribbean reports are stale; run with --write",file=sys.stderr); return 1
 print(f"Americas/Caribbean density valid: {report['settlementCount']} settlements")
 return 0
if __name__=="__main__": raise SystemExit(main())

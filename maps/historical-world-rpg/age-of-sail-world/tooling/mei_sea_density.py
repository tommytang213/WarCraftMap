#!/usr/bin/env python3
"""Validate and report the Middle East/India and Southeast Asia density pass."""
from __future__ import annotations
import json, sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/"reports/middle-east-india-southeast-asia-settlement-density.json"
HUMAN=ROOT/"reports/middle-east-india-southeast-asia-settlement-density.md"
REGIONS={"middle-east-india":(155,225),"southeast-asia":(85,130)}
class DensityError(ValueError): pass

def audit():
 result={"schemaVersion":1,"campaignStartDate":"1450-01-01","status":"complete","globalRoadmapComplete":False,"regions":{}}
 ids=set()
 for region,(minimum,maximum) in REGIONS.items():
  source=json.loads((ROOT/f"scenario/settlements/{region}-1450.json").read_text()); politics=json.loads((ROOT/f"scenario/politics/{region}-1450.json").read_text())
  rows=source["settlements"]; evidence={x["id"] for x in source.get("historicalEvidence",[])}; by_sub=Counter(); by_map=Counter(); by_role=Counter(); by_polity=Counter(); networks=Counter()
  if not minimum<=len(rows)<=maximum: raise DensityError(f"{region}: outside locked release-scale range")
  for row in rows:
   if row["id"] in ids: raise DensityError(f"duplicate stable ID: {row['id']}")
   ids.add(row["id"])
   if not set(row.get("historicalEvidenceIds",[])) or not set(row["historicalEvidenceIds"])<=evidence: raise DensityError(f"{row['id']}: invalid evidence")
   if row.get("controlContext",{}).get("date")!="1450-01-01": raise DensityError(f"{row['id']}: invalid control context")
   if row.get("physicalMapId")!=row["regionalInstanceId"]: raise DensityError(f"{row['id']}: physical map mismatch")
   if len(row.get("sourcePosition",[]))!=2: raise DensityError(f"{row['id']}: missing geographic source position")
   by_sub[row["regionalInstanceId"]]+=1; by_map[row["physicalMapId"]]+=1; by_role.update(row["roles"]); by_polity[row["polityId"]]+=1
   networks.update(["maritime" if "port" in row else "caravan_or_market" if set(row["roles"])&{"trade_center","caravan_center"} else "administrative"])
  represented=set(by_polity)|{x.get("polityId") for x in source.get("abstractCommunities",[])}
  missing={x["id"] for x in politics["polities"]}-represented
  if missing: raise DensityError(f"{region}: missing polity coverage: {sorted(missing)}")
  if max(by_map.values())>70: raise DensityError(f"{region}: physical-map object budget exceeded")
  result["regions"][region.replace('-','_')]={"settlementCount":len(rows),"portAndAnchorageCount":sum("port" in x for x in rows),"abstractCommunityCount":len(source.get("abstractCommunities",[])),"bySubregion":dict(sorted(by_sub.items())),"byPhysicalMap":dict(sorted(by_map.items())),"byRole":dict(sorted(by_role.items())),"byHistoricalNetwork":dict(sorted(networks.items())),"byPolityImportance":[{"polityId":k,"settlementCount":v,"importance":"major" if v>=6 else "regional" if v>=3 else "localized"} for k,v in sorted(by_polity.items())],"budgets":{"catalogueMaximum":maximum,"physicalMapMaximum":70,"activationPolicy":"abstract_until_regional_activation"}}
 return result

def markdown(report):
 lines=["# Middle East, India, and Southeast Asia settlement-density report","","Status: **COMPLETE**","","The regional release-scale pass is complete; the global settlement-density roadmap item remains open. Counts reflect historical networks and map compression rather than equal polity quotas.",""]
 for key,data in report["regions"].items():
  lines += [f"## {key.replace('_',' ').title()}","",f"{data['settlementCount']} settlements, {data['portAndAnchorageCount']} ports/anchorages, and {data['abstractCommunityCount']} compressed community groups.","","| Subregion / physical map | Count |","|---|---:|"]+[f"| {k} | {v} |" for k,v in data["bySubregion"].items()]+["","| Role | Count |","|---|---:|"]+[f"| {k} | {v} |" for k,v in data["byRole"].items()]+[""]
 return "\n".join(lines).rstrip()+"\n"

def main(argv=None):
 argv=sys.argv[1:] if argv is None else argv
 try: report=audit(); human=markdown(report)
 except (OSError,json.JSONDecodeError,DensityError) as e: print(f"MEI/SEA density validation failed: {e}",file=sys.stderr); return 1
 if argv==["--write"]: REPORT.write_text(json.dumps(report,indent=2)+"\n"); HUMAN.write_text(human)
 elif argv: print("usage: mei_sea_density.py [--write]",file=sys.stderr); return 1
 elif not REPORT.exists() or json.loads(REPORT.read_text())!=report or not HUMAN.exists() or HUMAN.read_text()!=human: print("MEI/SEA reports are stale; run with --write",file=sys.stderr); return 1
 print(f"MEI/SEA density valid: {sum(x['settlementCount'] for x in report['regions'].values())} settlements")
 return 0
if __name__=="__main__": raise SystemExit(main())

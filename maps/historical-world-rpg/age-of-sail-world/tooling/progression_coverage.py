#!/usr/bin/env python3
"""Validate release breadth and emit deterministic progression coverage reports."""
from __future__ import annotations
import collections, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tooling"))
import progression_catalog

ERAS=((1450,1499),(1500,1599),(1600,1699),(1700,1749),(1750,1799),(1800,1820))

def build():
 data=progression_catalog.validate(); nodes=data["technologies"]+data["institutions"]
 index={x["id"]:x for x in nodes}; depths={}
 def depth(ident):
  if ident not in depths: depths[ident]=1+max((depth(x) for x in index[ident]["prerequisiteIds"]),default=-1)
  return depths[ident]
 for ident in index: depth(ident)
 by_branch=collections.Counter(x["branchId"] for x in nodes)
 by_unlock=collections.Counter(u[0] for x in nodes for u in x["unlocks"])
 by_era={f"{lo}-{hi}":sum(lo<=x["preferredYear"]<=hi for x in nodes) for lo,hi in ERAS}
 origins=collections.Counter(r for x in data["institutions"] for r in x["origin"]["regionIds"])
 evidence=collections.Counter(e for x in nodes for e in x["evidenceIds"])
 cross=sum(any(index[p]["branchId"]!=x["branchId"] for p in x["prerequisiteIds"]) for x in nodes)
 return {"format":"age_of_sail_progression_coverage_v1","counts":{"technologies":len(data["technologies"]),"institutionsAndReforms":len(data["institutions"]),"crossTreeNodes":cross,"maximumPrerequisiteDepth":max(depths.values())},"byBranch":dict(sorted(by_branch.items())),"byEra":by_era,"byOriginRegion":dict(sorted(origins.items())),"byUnlockCategory":dict(sorted(by_unlock.items())),"byEvidence":dict(sorted(evidence.items())),"prerequisiteDepth":{str(k):v for k,v in sorted(collections.Counter(depths.values()).items())}}

def main():
 report=build(); out=ROOT/"reports/progression-coverage.json"
 out.write_text(json.dumps(report,indent=2)+"\n")
 lines=["# Progression coverage","",f"- Technologies: {report['counts']['technologies']}",f"- Institutions/reforms: {report['counts']['institutionsAndReforms']}",f"- Cross-tree nodes: {report['counts']['crossTreeNodes']}",f"- Maximum prerequisite depth: {report['counts']['maximumPrerequisiteDepth']}","","## Branch and era coverage","","| Dimension | Node count |","|---|---:|"]
 lines += [f"| Branch: {k} | {v} |" for k,v in report["byBranch"].items()]
 lines += [f"| Era: {k} | {v} |" for k,v in report["byEra"].items()]
 (ROOT/"reports/progression-coverage.md").write_text("\n".join(lines)+"\n")
 print(f"Progression coverage valid: {report['counts']['technologies']} technologies, {report['counts']['institutionsAndReforms']} institutions/reforms")

if __name__=="__main__": main()

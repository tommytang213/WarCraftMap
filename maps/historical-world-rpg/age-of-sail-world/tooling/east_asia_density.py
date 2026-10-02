#!/usr/bin/env python3
"""Deterministic Phase 8 East Asia historical-density audit and report."""
from __future__ import annotations
import json, sys
from collections import Counter
from pathlib import Path

from east_asia_content import validate

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/"reports/east-asia-settlement-density.json"; HUMAN=ROOT/"reports/east-asia-settlement-density.md"

class DensityError(ValueError): pass

def _reachable(edges,start):
 graph={}
 for a,b in edges: graph.setdefault(a,set()).add(b); graph.setdefault(b,set()).add(a)
 seen=set(); pending=[start]
 while pending:
  node=pending.pop()
  if node not in seen: seen.add(node); pending.extend(graph.get(node,()))
 return seen

def audit():
 source,politics,_,_=validate(); rows=source["settlements"]
 if not 110<=len(rows)<=135: raise DensityError("East Asia catalogue is outside the reviewed release-density budget")
 ids={x["id"] for x in rows}; names=[x["name"].casefold() for x in rows]; coords=[tuple(x["sourcePosition"]) for x in rows]
 if len(ids)!=len(rows) or len(set(names))!=len(names) or len(set(coords))!=len(coords): raise DensityError("duplicate settlement ID, historical name, or source coordinate")
 provinces={p["id"] for polity in politics["polities"] for p in polity["provinces"]}
 represented={x["provinceId"] for x in rows}
 if provinces-represented: raise DensityError(f"unexplained province coverage gaps: {sorted(provinces-represented)}")
 land=[(x["fromSettlementId"],x["toSettlementId"]) for x in source["tradeRoutes"] if x["kind"]!="maritime"]
 sea=[(x["fromSettlementId"],x["toSettlementId"]) for x in source["tradeRoutes"] if x["kind"]=="maritime"]
 # Each physical-map land catalogue must be reachable from one of its established
 # priority settlements; the maritime graph independently covers every port.
 for instance in sorted({x["regionalInstanceId"] for x in rows}):
  group={x["id"] for x in rows if x["regionalInstanceId"]==instance}
  start=next(iter(group)); reached=_reachable(land+sea,start)
  if group-reached: raise DensityError(f"inaccessible settlement network on {instance}: {sorted(group-reached)}")
 ports={x["id"] for x in rows if "port" in x}
 if ports-_reachable(sea,next(iter(ports))): raise DensityError("maritime network does not connect every port")
 by_map=Counter(x["physicalMapId"] for x in rows); by_role=Counter(r for x in rows for r in x["roles"]); by_polity=Counter(x["polityId"] for x in rows)
 if max(by_map.values())>55: raise DensityError("finalized per-map settlement catalogue budget exceeded")
 networks={
  "grand_canal_and_yellow_river":sum(bool(set(x["roles"])&{"canal_node","river_node"}) and x["polityId"]=="ming_empire" for x in rows),
  "china_seas_and_ryukyu":sum("port" in x and x["regionalInstanceId"] in {"east_asia_china_north","east_asia_china_south"} for x in rows),
  "korea_strait_and_japanese_coasts":sum("port" in x and x["regionalInstanceId"] in {"east_asia_korea","east_asia_japan"} for x in rows),
  "silk_road_steppe_and_tibetan_routes":sum(x["regionalInstanceId"]=="east_asia_interior" for x in rows),
  "amur_okhotsk_frontier":sum(x["regionalInstanceId"]=="east_asia_northeast_pacific" or x["polityId"] in {"jianzhou_jurchen","haixi_jurchen","wild_jurchen_confederacies","sakhalin_communities"} for x in rows),
 }
 if min(networks.values())<3: raise DensityError("material historical-network density gap")
 return {"schemaVersion":1,"campaignStartDate":"1450-01-01","status":"complete","globalRoadmapComplete":False,"settlementCount":len(rows),"portCount":len(ports),"abstractCommunityCount":len(source["abstractCommunities"]),"bySubregion":dict(sorted(by_map.items())),"byPhysicalMap":dict(sorted(by_map.items())),"byRole":dict(sorted(by_role.items())),"byHistoricalNetwork":networks,"byPolityImportance":[{"polityId":k,"settlementCount":v,"importance":"major" if v>=12 else "regional" if v>=3 else "localized_or_mobile"} for k,v in sorted(by_polity.items())],"budgets":{"catalogueMaximum":135,"perPhysicalMapMaximum":55,"runtimePolicy":"authoritative_abstract_until_regional_activation"}}

def markdown(r):
 lines=["# East Asia settlement-density report","","Status: **COMPLETE**","","This Phase 8 regional pass extends the stable priority catalogue to historically grounded release-scale density. It preserves the global settlement-density roadmap item as incomplete. Density follows administrative, agricultural, riverine, coastal, and commercial geography rather than modern borders or equal polity quotas; sparse frontier, steppe, forest, island, and highland coverage is intentional and supplemented by authoritative abstract communities.","",f"{r['settlementCount']} settlements, {r['portCount']} ports, and {r['abstractCommunityCount']} abstract-community groups.","","## Coverage by subregion and physical map","","| Subregion / physical map | Settlements |","|---|---:|"]
 lines += [f"| {k} | {v} |" for k,v in r["bySubregion"].items()]
 lines += ["","## Coverage by role","","| Role | Count |","|---|---:|"]+[f"| {k} | {v} |" for k,v in r["byRole"].items()]
 lines += ["","## Historical networks","","| Network | Nodes |","|---|---:|"]+[f"| {k} | {v} |" for k,v in r["byHistoricalNetwork"].items()]
 lines += ["","Significant local displacement is recorded per settlement in `declaredDistortion`; these bounded offsets separate compressed sites, avoid blocked terrain and entry anchors, and retain each real EPSG:4326 source coordinate.",""]
 return "\n".join(lines)

def main(argv=None):
 argv=sys.argv[1:] if argv is None else argv
 try: report=audit(); human=markdown(report)
 except (OSError,json.JSONDecodeError,DensityError,ValueError) as e: print(f"East Asia density validation failed: {e}",file=sys.stderr); return 1
 if argv==["--write"]: REPORT.write_text(json.dumps(report,indent=2)+"\n"); HUMAN.write_text(human)
 elif argv: print("usage: east_asia_density.py [--write]",file=sys.stderr); return 1
 elif not REPORT.exists() or json.loads(REPORT.read_text())!=report or not HUMAN.exists() or HUMAN.read_text()!=human: print("East Asia density reports are stale; run with --write",file=sys.stderr); return 1
 print(f"East Asia density valid: {report['settlementCount']} settlements")
 return 0
if __name__=="__main__": raise SystemExit(main())

#!/usr/bin/env python3
"""Build and validate the deterministic release-scale settlement baseline report."""
from __future__ import annotations
import argparse, json, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; SHARED=ROOT.parent/"_shared"/"engine"
sys.path.insert(0,str(SHARED))
from settlement_catalogue import CatalogueError, grouped_counts, validate_catalogue

SOURCES=ROOT/"scenario"/"settlements"; POLITICS=ROOT/"scenario"/"politics"
PROFILE=SOURCES/"release-scale-coverage.json"; REPORT=ROOT/"reports"/"settlement-coverage-baseline.json"
ROLE_CLASS={"capital":"capital","fortified_town":"fort","fortified_settlement":"fort","major_port":"city"}

def read(p): return json.loads(p.read_text(encoding="utf-8"))
def region_for(path): return path.stem.removesuffix("-1450").replace("-","_")

def load():
    mapdoc=read(ROOT/"scenario/maps/world-map.json"); maps=set(mapdoc["regionalInstanceRegions"]); bounds={}
    # Physical-map packages are distinct from logical regional instances.  The
    # release-scale sources name the package that owns each concrete placement,
    # so both namespaces are valid catalogue references.
    physical_maps=read(ROOT/"physical-maps.json")["physicalMaps"]
    maps.update(x["id"] for x in physical_maps)
    regions=set(mapdoc["regionalInstanceRegions"].values()); polities=set(); provinces=set(); owners={}
    for path in sorted(POLITICS.glob("*-1450.json")):
        for polity in read(path)["polities"]:
            polities.add(polity["id"])
            for province in polity["provinces"]: provinces.add(province["id"]); owners[province["id"]]=polity["id"]
    for path in sorted((ROOT/"scenario/geography").glob("*.json")):
        doc=read(path)
        for instance in doc.get("instances",[]):
            mid=instance.get("physicalMapId",instance["id"]); maps.update((mid,instance["id"]))
            if "localBounds" in instance:
                bounds[instance["id"]]=instance["localBounds"]
                old=bounds.get(mid,instance["localBounds"]); new=instance["localBounds"]
                bounds[mid]={"minX":min(old["minX"],new["minX"]),"minY":min(old["minY"],new["minY"]),"maxX":max(old["maxX"],new["maxX"]),"maxY":max(old["maxY"],new["maxY"])}
    raw=[]; route_ids=set(); terrain=set(); navigation=set(maps)
    for path in sorted(SOURCES.glob("*-1450.json")):
        doc=read(path); reg=region_for(path)
        for route in doc.get("tradeRoutes",[]):
            route_ids.add(route["id"])
        for s in doc["settlements"]:
            terrain.add(s["terrainClass"]); navigation.add(s.get("navigationZoneId",s["regionalInstanceId"]))
    refs={"regions":regions,"maps":maps,"mapBounds":bounds,"polities":polities,"provinces":provinces,"provinceOwners":owners,"terrain":terrain,"navigation":navigation,"routes":route_ids}
    for path in sorted(SOURCES.glob("*-1450.json")):
        doc=read(path); reg=region_for(path)
        endpoints=defaultdict(list)
        for route in doc.get("tradeRoutes",[]):
            for key in ("fromSettlementId","toSettlementId"):
                if route.get(key): endpoints[route[key]].append(route["id"])
        for s in doc["settlements"]:
            roles=sorted(set(s.get("roles",[]))); pos=s.get("sourcePosition",s.get("position")); nav=s.get("navigationZoneId",s["regionalInstanceId"])
            cls=next((ROLE_CLASS[x] for x in roles if x in ROLE_CLASS),"town")
            importance="global" if "capital" in roles and ("trade_center" in roles or "major_port" in roles) else "regional" if set(roles)&{"capital","trade_center","major_port","political_center"} else "local"
            port=s.get("port")
            if port: port={"kind":"port" if "major_port" in roles else "anchorage","navigationZoneId":port["maritimeZoneId"],**port}; navigation.add(port["navigationZoneId"])
            row={"id":s["id"],"names":{"display":s["name"]},"regionId":reg,"polityId":s["polityId"],"provinceId":s["provinceId"],"controllerPolityId":s["polityId"],"settlementClass":cls,"roles":roles,"representation":"physical","physicalMapId":s.get("physicalMapId",s["regionalInstanceId"]),"placement":{"basis":"longitude_latitude" if "sourcePosition" in s else "regional_map","x":pos[0],"y":pos[1],"terrainClass":s["terrainClass"],"navigationZoneId":nav},"routeIds":sorted(endpoints[s["id"]]),"historicalImportance":importance,"evidence":[{"sourceId":str(path.relative_to(ROOT)),"claim":claim} for claim in ("identity","placement","ownership","importance")]}
            if port: row["port"]=port
            raw.append(row)
    # The projected world also contains authoritative minor centres introduced by
    # polity projection. Keep them visible as abstract catalogue records until a
    # regional evidence pass authors precise physical placement.
    world=read(ROOT/"scenario/world/world.json"); existing={x["id"] for x in raw}; terrain.add("abstract")
    navigation.update(x["id"] for x in world["navigationZones"])
    for s in world["settlements"]:
        if s["id"] in existing: continue
        instance=s.get("regionalInstanceId"); reg=mapdoc["regionalInstanceRegions"].get(instance)
        roles=sorted(set(s.get("roleIds",[]))); importance="regional" if s.get("kind") in {"capital","major_city","port"} else "supporting"
        raw.append({"id":s["id"],"names":{"display":s["name"]},"regionId":reg,"polityId":s["legalOwnerPolityId"],"provinceId":s["provinceId"],"controllerPolityId":s["controllerPolityId"],"settlementClass":s["kind"] if s["kind"] in {"capital","city","town","village","fort","trading_post"} else "community","roles":roles,"representation":"abstract_minor","placement":{"basis":"regional_centroid","terrainClass":"abstract","navigationZoneId":s.get("navigationZoneId",instance)},"routeIds":[],"historicalImportance":importance,"compressionRationale":"Existing authoritative minor centre retained abstract until regional evidence supports precise physical placement.","evidence":[{"sourceId":"scenario/world/world.json","claim":claim} for claim in ("identity","placement","ownership","importance")]})
    refs["terrain"]=terrain
    refs["navigation"] |= navigation
    return validate_catalogue(raw,refs),refs

def build_report():
    rows,_=load(); profile=read(PROFILE); targets={x["regionId"]:x["target"] for x in profile["regions"]}
    by_region=grouped_counts(rows,"regionId"); gaps={r:{"current":by_region.get(r,0),"minimum":t["minimum"],"planningMaximum":t["planningMaximum"],"gapToMinimum":max(0,t["minimum"]-by_region.get(r,0))} for r,t in sorted(targets.items())}
    by_polity=Counter(r["polityId"] for r in rows); importance=defaultdict(Counter)
    for r in rows: importance[r["polityId"]][r["historicalImportance"]]+=1
    polity=[{"polityId":p,"current":n,"importanceSignals":dict(sorted(importance[p].items())),"expectationClass":"major" if importance[p]["global"] else "regional" if importance[p]["regional"] else "local"} for p,n in sorted(by_polity.items())]
    return {"format":"settlement_coverage_baseline_v1","status":"foundation_only_not_density_complete","policy":profile["policy"],"global":{"current":len(rows),**profile["globalTarget"],"gapToMinimum":max(0,profile["globalTarget"]["minimum"]-len(rows))},"byRegion":gaps,"byPolityImportance":polity,"byProvince":grouped_counts(rows,"provinceId"),"bySettlementRole":dict(sorted(Counter(x for r in rows for x in r["roles"]).items())),"byPhysicalMap":grouped_counts(rows,"physicalMapId"),"byHistoricalImportance":grouped_counts(rows,"historicalImportance"),"byRepresentation":grouped_counts(rows,"representation"),"settlements":rows}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--write",action="store_true"); args=ap.parse_args(); report=build_report(); text=json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n"
    if args.write: REPORT.write_text(text,encoding="utf-8")
    elif not REPORT.exists() or REPORT.read_text(encoding="utf-8")!=text: raise CatalogueError("settlement baseline report is stale; run tooling/settlement_catalogue.py --write")
    print(f"settlement catalogue foundation valid: {report['global']['current']} stable settlements; gap {report['global']['gapToMinimum']}")
if __name__=="__main__": main()

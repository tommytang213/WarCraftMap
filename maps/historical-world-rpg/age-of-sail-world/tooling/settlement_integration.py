#!/usr/bin/env python3
"""Build the deterministic release-scale settlement integration manifest/report."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; ENGINE=ROOT.parent/"_shared"/"engine"
sys.path.insert(0,str(ENGINE))
from settlement_integration import REQUIRED_ROLES, validate_manifest

MANIFEST=ROOT/"scenario/integration/release-scale-settlements.json"
REPORT=ROOT/"reports/settlement-integration.json"
REGION_FILE={"middle_east_india":"middle-east-india","southeast_asia":"southeast-asia","east_asia":"east-asia","americas_caribbean":"americas-caribbean"}
NAME_POOLS={
 "europe":(["Martin","Thomas","Jakob","Nicolas"],["Mercer","Fischer","Costa","Dubois"]),
 "africa":(["Amari","Bakari","Idris","Kwame"],["Keita","Mensah","Diallo","Toure"]),
 "middle_east_india":(["Ali","Hasan","Arjun","Ravi"],["Khan","Shah","Rao","Das"]),
 "southeast_asia":(["Adi","Budi","Minh","Suri"],["Wijaya","Tran","Laksana","Phan"]),
 "east_asia":(["Wei","Jun","Haru","Seong"],["Li","Wang","Sato","Kim"]),
 "americas_caribbean":(["Acolmiztli","Inti","Amaru","Tupac"],["Xochitl","Yupanqui","Condori","Anacaona"]),
 "pacific":(["Aho","Ikaika","Mana","Tui"],["Keawe","Mata","Rangi","Vaka"]),
}

def read(p): return json.loads(p.read_text(encoding="utf-8"))
def pick(seed, values): return values[int.from_bytes(hashlib.sha256(seed.encode()).digest()[:8],"big")%len(values)]

def load_sources():
 spec=importlib.util.spec_from_file_location("catalogue_tool",ROOT/"tooling/settlement_catalogue.py")
 cat=importlib.util.module_from_spec(spec); spec.loader.exec_module(cat); rows,_=cat.load()
 authored={}; routes={}; route_endpoints=defaultdict(list)
 for path in sorted((ROOT/"scenario/settlements").glob("*-1450.json")):
  doc=read(path)
  for x in doc["settlements"]: authored[x["id"]]=x
  for x in doc.get("tradeRoutes",[]):
   routes[x["id"]]=x
   for key in ("fromSettlementId","toSettlementId"):
    if x.get(key): route_endpoints[x[key]].append(x["id"])
 goods=read(ROOT/"scenario/economy/global-goods.json")
 visuals=read(ROOT/"scenario/visuals/settlement-building-sets.json")
 assignments={x["settlementId"]:x for x in visuals["settlementAssignments"]}
 layouts={x["settlementId"]:x for x in visuals["defenseLayoutAssignments"]}
 world=read(ROOT/"scenario/world/world.json"); world_rows={x["id"]:x for x in world["settlements"]}
 return rows,authored,routes,route_endpoints,goods,assignments,layouts,world_rows

def build_manifest():
 rows,authored,routes,endpoints,goods,visuals,layouts,world=load_sources(); defaults=goods["regionalDefaults"]
 entries=[]
 for row in sorted(rows,key=lambda x:x["id"]):
  sid=row["id"]; region=row["regionId"]; source=authored.get(sid,{}); wr=world[sid]
  region_key=REGION_FILE.get(region,region); default=defaults[region_key]
  econ=source.get("economy",{}); production=list(econ.get("production",default["stapleGoodIds"][:2])); imports=list(econ.get("imports",default["tradeGoodIds"][:2])); shortages=list(econ.get("shortages",default["stapleGoodIds"][-1:]))
  available=list(dict.fromkeys(production+imports+shortages+default["stapleGoodIds"]))[:goods["performanceBudgets"]["maximumGoodsPerSettlement"]]
  services=source.get("services",wr.get("serviceIds",["market","quest_hub"])); routes_here=sorted(set(endpoints[sid]+econ.get("tradeEndpointIds",[])+row.get("routeIds",[])))
  # Endpoint IDs may describe abstract networks rather than authored edge IDs; both are stable route hooks.
  given,family=NAME_POOLS[region]
  # The locative is both culturally neutral and guarantees that two officials
  # selected from a deliberately small regional name pool never become the
  # same persistent character identity in player-facing records.
  display=f"{pick(sid+'|given',given)} {pick(sid+'|family',family)} of {row['names']['display']}"
  capturable=source.get("captureModel", "city_core" if wr.get("capturable",True) else "non_capturable_community") not in {"non_capturable_community","non_capturable"}
  visual=visuals[sid]; layout=layouts.get(sid)
  role_model={
   "administration":"generated_minor_official_v1", "defense":"local_garrison_v1" if capturable else "community_watch_v1",
   "economy":"settlement_market_v1", "services":"service_registry_v1", "visuals":visual["visualSetId"],
   "discovery":"stable_location_discovery_v1", "routes":"authored_or_regional_trade_graph_v1", "physicalMap":row.get("physicalMapId","abstract_regional_projection"),
   "persistence":"settlement_integration_state_v1", "quests":"stable_settlement_target_v1", "events":"stable_settlement_scope_v1",
   "characters":"stable_location_and_office_v1", "technology":"polity_province_market_modifier_v1", "institutions":"province_adoption_modifier_v1",
   "ai":"territorial_settlement_target_v1", "diplomacy":"controller_legal_owner_scope_v1", "war":"validated_conflict_target_v1",
   "capture":"city_core_capture_v1" if capturable else "validated_non_capturable_community_v1", "historicalLocations":"catalogue_location_v1",
  }
  objects=["discovery_marker"]
  if row["representation"]=="physical": objects += ["city_core" if capturable else "community_marker"]
  if source.get("port") or row.get("port"): objects += ["port_anchor"]
  entries.append({"settlementId":sid,"regionId":region,"provinceId":row["provinceId"],"legalOwnerPolityId":row["polityId"],"controllerPolityId":row["controllerPolityId"],
   "runtimePolicy":"authoritative_abstract_reconstruct_on_demand","physicalRepresentationKinds":objects,"captureModel":"city_core" if capturable else "non_capturable",
   "governanceExceptionId":None if capturable else "community_collective_authority","official":{"characterId":f"official_{sid}","displayName":display,"culturePoolId":region,"generationKey":f"{sid}:administrator:v1"},
   "defense":{"profileId":"fortified_garrison" if layout else "local_militia","layoutId":layout["defenseLayoutId"] if layout else None,"bounded":True},
   "economy":{"productionGoodIds":production,"demandGoodIds":imports,"importGoodIds":imports,"shortageGoodIds":shortages,"availableGoodIds":available,"storageCapacityUnits":36000 if "warehouse" in services else 12000,"merchantHookId":"regional_merchant_market","serviceHookIds":services},
   "routeIds":routes_here or [f"regional_access_{region}"],"visualSetId":visual["visualSetId"],"buildingRoleIds":visual["requiredVisualRoles"],
   "gameplayRoles":{k:{"modelId":v} for k,v in role_model.items()}})
 manifest={"schemaVersion":1,"id":"release_scale_settlement_integration","catalogueStatus":"integration_complete_density_audit_pending","stateSchemaVersion":1,
  "performanceBudgets":{"maximumActiveSettlementObjects":512,"globalRuntimeObjectPolicy":"no_objects_for_inactive_settlements"},"settlements":entries}
 validate_manifest(manifest); return manifest

def build_report(manifest=None):
 manifest=manifest or build_manifest(); rows=validate_manifest(manifest); missing=[]
 for sid,row in rows.items():
  absent=sorted(REQUIRED_ROLES-set(row["gameplayRoles"]));
  if absent: missing.append({"settlementId":sid,"missingRoles":absent})
 regions=Counter(x["regionId"] for x in rows.values()); exceptions=sum(x["captureModel"]=="non_capturable" for x in rows.values())
 return {"schemaVersion":1,"status":"pass" if not missing else "fail","catalogueStatus":"integration_complete_density_audit_pending","settlementCount":len(rows),"byRegion":dict(sorted(regions.items())),
  "validatedGovernanceExceptions":exceptions,"validatedNonCapturableModels":exceptions,"generatedOfficials":len(rows),"garrisonProfiles":len(rows),"inertSettlements":len(missing),"missingGameplayRoles":missing,
  "unresolvedReferences":0,"impossibleMarkets":0,"invalidPorts":0,"missingServices":0,"duplicatedCharacters":0,"unboundedGarrisons":0,"activeObjectLeakage":0,
  "runtimePolicy":manifest["performanceBudgets"]["globalRuntimeObjectPolicy"],"roadmapDensityComplete":False}

def main(argv=None):
 ap=argparse.ArgumentParser(); ap.add_argument("--write",action="store_true"); args=ap.parse_args(argv); manifest=build_manifest(); report=build_report(manifest)
 m=json.dumps(manifest,indent=2,ensure_ascii=False,sort_keys=True)+"\n"; r=json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n"
 if args.write: MANIFEST.parent.mkdir(parents=True,exist_ok=True); MANIFEST.write_text(m,encoding="utf-8"); REPORT.write_text(r,encoding="utf-8")
 elif not MANIFEST.exists() or MANIFEST.read_text(encoding="utf-8")!=m or not REPORT.exists() or REPORT.read_text(encoding="utf-8")!=r: raise SystemExit("settlement integration outputs are stale; run with --write")
 print(f"settlement integration valid: {report['settlementCount']} settlements, {report['inertSettlements']} inert")
 return 0
if __name__=="__main__": raise SystemExit(main())

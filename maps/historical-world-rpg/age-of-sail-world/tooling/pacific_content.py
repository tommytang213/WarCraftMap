#!/usr/bin/env python3
"""Validate and project authoritative Pacific settlement and route content."""
from __future__ import annotations
import copy, json, math, re, sys
from pathlib import Path
from pacific_politics import project as project_politics

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"scenario/settlements/pacific-1450.json"; POLITICS=ROOT/"scenario/politics/pacific-1450.json"; GEOGRAPHY=ROOT/"scenario/geography/pacific.json"; TERRAIN=ROOT/"scenario/terrain/pacific.json"; WORLD=ROOT/"scenario/world/world.json"; ECONOMY=ROOT/"scenario/economy/economy.json"; MAPS=ROOT/"scenario/maps/world-map.json"
ID=re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
ROLES={"political_center","major_port","anchorage","trade_center","voyaging_center","fortified_settlement","transition_location","historical_location","religious_location"}
WATER={"node_north_pacific","node_hawaii_coast","node_micronesia_sea","node_micronesia_islands","node_melanesia_sea","node_west_polynesia_sea","node_fiji_coast","node_east_polynesia_sea","node_tahiti_coast","node_new_zealand_sea","node_americas_approach"}
class PacificContentError(ValueError): pass
def _index(rows,label):
 out={}
 if not isinstance(rows,list): raise PacificContentError(f"{label} must be an array")
 for x in rows:
  ident=x.get("id") if isinstance(x,dict) else None
  if not isinstance(ident,str) or not ID.fullmatch(ident) or ident in out: raise PacificContentError(f"{label}: invalid or duplicate stable ID {ident!r}")
  out[ident]=x
 return out
def _inside(point,poly):
 x,y=point; inside=False
 for n,(x1,y1) in enumerate(poly):
  x2,y2=poly[n-1]
  if (y1>y)!=(y2>y) and x<(x2-x1)*(y-y1)/(y2-y1)+x1: inside=not inside
 return inside
def _reachable(edges,start):
 graph={}
 for a,b in edges: graph.setdefault(a,set()).add(b); graph.setdefault(b,set()).add(a)
 seen=set(); pending=[start]
 while pending:
  x=pending.pop()
  if x not in seen: seen.add(x); pending.extend(graph.get(x,()))
 return seen

def validate(source_path=SOURCE,politics_path=POLITICS):
 source=json.loads(Path(source_path).read_text()); politics=json.loads(Path(politics_path).read_text()); geography=json.loads(GEOGRAPHY.read_text()); terrain=json.loads(TERRAIN.read_text()); maps=json.loads(MAPS.read_text()); world=json.loads(WORLD.read_text())
 if source.get("schemaVersion")!=1 or source.get("campaignStartDate")!="1450-01-01" or source.get("coverageRule")!="selective_global_importance_gameplay_navigation_performance": raise PacificContentError("invalid Pacific content baseline")
 rules=source.get("stateProjectionRules",{})
 if set(rules)!={"activation","retirement","reconstruction","capture","inactiveMutation","saveProjection"} or any(not isinstance(v,str) or not v for v in rules.values()): raise PacificContentError("incomplete authoritative state projection rules")
 settlements=_index(source.get("settlements"),"settlements"); polities=_index(politics.get("polities"),"polities"); provinces={p["id"]:(q["id"],p) for q in polities.values() for p in q["provinces"]}; instances=_index(geography["instances"],"instances"); nodes=_index(geography["navigationTopology"]["nodes"],"nodes"); anchors=_index(geography["boundaryAnchors"],"anchors"); policies={x["id"]:x for x in terrain["instancePolicies"]}; positions={}
 for sid,x in settlements.items():
  if x.get("polityId") not in polities or x.get("provinceId") not in provinces or provinces[x["provinceId"]][0]!=x["polityId"]: raise PacificContentError(f"settlement {sid}: polity/province mismatch")
  instance=x.get("regionalInstanceId"); pos=x.get("position"); bounds=instances.get(instance,{}).get("localBounds",{})
  if x.get("physicalMapId")!=instances.get(instance,{}).get("physicalMapId") or maps["regionalInstanceRegions"].get(instance)!="pacific": raise PacificContentError(f"settlement {sid}: invalid physical-map assignment")
  if not isinstance(pos,list) or len(pos)!=2 or not bounds.get("minX",1)<=pos[0]<=bounds.get("maxX",0) or not bounds.get("minY",1)<=pos[1]<=bounds.get("maxY",0): raise PacificContentError(f"settlement {sid}: position outside local bounds")
  policy=policies.get(instance)
  if policy is None or not any(_inside(pos,m) for m in policy["landMasks"]) or any(_inside(pos,m) for m in policy["decorativeWaterMasks"]): raise PacificContentError(f"settlement {sid}: position is not valid land terrain")
  if x.get("navigationZoneId") not in nodes or nodes[x["navigationZoneId"]]["instanceId"]!=instance or nodes[x["navigationZoneId"]]["class"] in {"impassable_barrier","decorative_water"}: raise PacificContentError(f"settlement {sid}: invalid navigation zone")
  if not x.get("roles") or not set(x["roles"])<=ROLES or len(x["roles"])!=len(set(x["roles"])): raise PacificContentError(f"settlement {sid}: invalid roles")
  econ=x.get("economy",{}); services=x.get("services",[])
  if set(econ)!={"production","imports","shortages","tradeEndpointIds"} or any(not isinstance(econ[k],list) or not econ[k] for k in econ) or set(econ["production"])&set(econ["shortages"]): raise PacificContentError(f"settlement {sid}: invalid economy profile")
  if not {"market","storage"}<=set(services): raise PacificContentError(f"settlement {sid}: missing market or storage service")
  model=x.get("captureModel"); capturable=model=="city_core"
  if model not in {"city_core","non_capturable_community"} or (capturable and not x.get("defenseLayoutRef")) or (not capturable and x.get("defenseLayoutRef") is not None): raise PacificContentError(f"settlement {sid}: invalid capture/defense model")
  port=x.get("port")
  if port and (x.get("terrainClass") not in {"coast","island","riverbank"} or not {"major_port","anchorage"}&set(x["roles"]) or port.get("maritimeZoneId") not in WATER or port.get("maritimeZoneId")!=x["navigationZoneId"] or "port_services" not in services): raise PacificContentError(f"settlement {sid}: invalid port access")
  if not port and ({"major_port","anchorage"}&set(x["roles"]) or "port_services" in services): raise PacificContentError(f"settlement {sid}: inland settlement exposes maritime access")
  positions[sid]={"x":pos[0],"y":pos[1]}
 ids=sorted(settlements); minimum=source["placementRules"]["minimumSeparationCells"]
 for n,a in enumerate(ids):
  for b in ids[n+1:]:
   if settlements[a]["regionalInstanceId"]==settlements[b]["regionalInstanceId"] and math.dist(tuple(positions[a].values()),tuple(positions[b].values()))<minimum: raise PacificContentError(f"settlements overlap: {a} and {b}")
 clearance=source["placementRules"]["entryAnchorClearanceCells"]
 for anchor in anchors.values():
  for sid,pos in positions.items():
   if settlements[sid]["regionalInstanceId"]==anchor["instanceId"] and "transition_location" not in settlements[sid]["roles"] and math.dist(tuple(pos.values()),tuple(anchor["local"]))<clearance: raise PacificContentError(f"settlement {sid}: obstructs entry anchor")
 routes=_index(source.get("tradeRoutes"),"routes"); maritime=[]
 for rid,r in routes.items():
  a,b=r.get("fromSettlementId"),r.get("toSettlementId")
  if a not in settlements or b not in settlements or a==b or r.get("contract")!="settlement_trade_endpoint" or r.get("kind") not in {"maritime","overland"}: raise PacificContentError(f"trade route {rid}: invalid endpoint contract")
  if r["kind"]=="maritime":
   if "port" not in settlements[a] or "port" not in settlements[b]: raise PacificContentError(f"trade route {rid}: inland maritime route")
   maritime.append((a,b))
 routed={x for e in maritime for x in e}; ports={x for x,v in settlements.items() if "port" in v}
 if ports-routed or ports-_reachable(maritime,next(iter(ports))): raise PacificContentError("maritime route endpoints are not connected")
 if set(source["requiredMaritimeZones"])-{settlements[x]["port"]["maritimeZoneId"] for x in ports}: raise PacificContentError("required maritime zones are not served")
 transitions=_index(source.get("transitions"),"transitions"); expected={"east_asia":"east_asia_pacific_crossing","southeast_asia":"southeast_asia_pacific_crossing","americas_caribbean":"pacific_americas_crossing"}; contracts={x["id"] for x in world["regionalGeography"]["routes"]}
 if {x.get("neighborRegionId") for x in transitions.values()}!=set(expected): raise PacificContentError("regional transitions are incomplete")
 for tid,t in transitions.items():
  sid=t.get("settlementId"); anchor=anchors.get(t.get("boundaryAnchorId"))
  if sid not in settlements or anchor is None or anchor["instanceId"]!=settlements[sid]["regionalInstanceId"] or t.get("routeContractId")!=expected[t.get("neighborRegionId")] or t.get("routeContractId") not in contracts or "transition_location" not in settlements[sid]["roles"]: raise PacificContentError(f"transition {tid}: invalid reference")
 return source,politics,geography,positions

def project(source,politics,geography,positions,world):
 world=project_politics(politics,copy.deepcopy(world)); sids={x["id"] for x in source["settlements"]}; vids={p["id"] for q in politics["polities"] for p in q["provinces"]}
 service_names={"storage":"Storage","crafting":"Crafting","ship_repair":"Ship Repair","ritual_services":"Ritual Services"}; known_services={x["id"] for x in world["settlementServiceDefinitions"]}
 for ident,name in service_names.items():
  if ident not in known_services: world["settlementServiceDefinitions"].append({"id":ident,"name":name})
 world["settlements"]=[x for x in world["settlements"] if x["id"] not in sids]; world["cityCores"]=[x for x in world["cityCores"] if x["id"] not in {"city_core_"+s for s in sids}]; world["defenseLayouts"]=[x for x in world["defenseLayouts"] if x["id"] not in {"defense_"+s for s in sids}]
 zones={x["id"]:x for x in world["navigationZones"]}
 for node in geography["navigationTopology"]["nodes"]:
  move=["flying"] if node["class"] in {"impassable_barrier","decorative_water"} else ["naval","amphibious","flying"] if node["class"] in {"navigable_sea","island_coast"} else ["land","amphibious","flying"]
  zones.setdefault(node["id"],{"id":node["id"],"movementClasses":move,"connections":{m:[] for m in move}})
 for edge in geography["navigationTopology"]["links"]:
  for m in edge["movementClasses"]:
   for a,b in ((edge["from"],edge["to"]),(edge["to"],edge["from"])):
    if m in zones[a]["connections"] and b not in zones[a]["connections"][m]: zones[a]["connections"][m].append(b)
 world["navigationZones"]=[zones[x] for x in sorted(zones)]
 for x in source["settlements"]:
  sid=x["id"]; cap=x["captureModel"]=="city_core"; record={"id":sid,"name":x["name"],"kind":"capital" if "political_center" in x["roles"] else "port" if "port" in x else "fort","provinceId":x["provinceId"],"legalOwnerPolityId":x["polityId"],"controllerPolityId":x["polityId"],"capturable":cap,"civilianFacilitiesInvulnerable":True,"navigationZoneId":x["navigationZoneId"],"serviceIds":x["services"],"regionalInstanceId":x["regionalInstanceId"],"physicalMapId":x["physicalMapId"],"localPosition":positions[sid],"terrainClass":x["terrainClass"],"roleIds":x["roles"],"activation":{"runtimeState":"abstract","representationTemplateId":"settlement_representation","deterministicKey":sid},"economicProfile":copy.deepcopy(x["economy"]),"productionRefs":x["economy"]["production"],"stateProjection":copy.deepcopy(source["stateProjectionRules"])}
  if x.get("port"): record["portAccess"]=copy.deepcopy(x["port"])
  if cap:
   record["cityCoreId"]="city_core_"+sid; record["defenseLayoutId"]="defense_"+sid; world["cityCores"].append({"id":"city_core_"+sid,"objectTemplateId":"capital_city_core"}); world["defenseLayouts"].append({"id":"defense_"+sid,"objectTemplateIds":[x["defenseLayoutRef"]]})
  world["settlements"].append(record)
 for p in world["provinces"]:
  if p["id"] in vids: p["settlementIds"]=[x["id"] for x in world["settlements"] if x.get("provinceId")==p["id"]]
 return world

def update_economy(source,economy):
 economy=copy.deepcopy(economy); c=economy["catalog"]; state=economy["state"]; keep=lambda rows:[x for x in rows if not x.get("id","").startswith("pac_")]
 for key in ("stores","markets","prices","producers"): c[key]=keep(c[key])
 state["storeBalances"]=keep(state["storeBalances"])
 for n,x in enumerate(source["settlements"]):
  sid="pac_"+x["id"]+"_store"; mid="pac_"+x["id"]+"_market"; port="port" in x
  c["stores"].append({"id":sid,"kind":"warehouse","owner":{"kind":"settlement","id":x["id"]},"capacityUnits":32000 if "trade_center" in x["roles"] else 16000,"allowedGoodIds":["grain","flour","ship_provisions"]}); c["markets"].append({"id":mid,"storeId":sid,"owner":{"kind":"settlement","id":x["id"]}}); c["producers"].append({"id":"pac_"+x["id"]+"_producer","storeId":sid,"recipeId":"prepare_ship_provisions" if port else "mill_grain_into_flour","owner":{"kind":"settlement","id":x["id"]}}); c["prices"].append({"id":"pac_"+x["id"]+"_grain_price","marketId":mid,"goodId":"grain","currencyId":"pound_sterling","quantityUnits":100,"amountMinor":11+(n*5)%13}); state["storeBalances"].append({"id":sid,"storeId":sid,"goods":[{"goodId":"grain","quantityUnits":650+n*67},{"goodId":"ship_provisions","quantityUnits":900+n*41}],"currencies":[{"currencyId":"pound_sterling","amountMinor":900+n*137}]})
 return economy
def main(argv=None):
 argv=sys.argv[1:] if argv is None else argv
 try:
  source,politics,geography,positions=validate()
  if argv==["--write"]: WORLD.write_text(json.dumps(project(source,politics,geography,positions,json.loads(WORLD.read_text())),ensure_ascii=False,indent=2)+"\n"); ECONOMY.write_text(json.dumps(update_economy(source,json.loads(ECONOMY.read_text())),ensure_ascii=False,indent=2)+"\n")
  elif argv: raise PacificContentError("usage: pacific_content.py [--write]")
  print(f"Pacific content valid: {len(source['settlements'])} settlements, {sum('port' in x for x in source['settlements'])} ports, {len(source['tradeRoutes'])} routes")
 except (OSError,json.JSONDecodeError,KeyError,PacificContentError) as e: print(f"Pacific content validation failed: {e}",file=sys.stderr); return 1
 return 0
if __name__=="__main__": raise SystemExit(main())

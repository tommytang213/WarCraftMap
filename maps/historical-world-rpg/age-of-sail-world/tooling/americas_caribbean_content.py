#!/usr/bin/env python3
"""Build, validate, and project the focused Americas/Caribbean content pass."""
from __future__ import annotations
import copy, json, math, re, sys
from pathlib import Path

from americas_caribbean_politics import project as project_politics

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"scenario/settlements/americas-caribbean-1450.json"; POLITICS=ROOT/"scenario/politics/americas-caribbean-1450.json"
GEOGRAPHY=ROOT/"scenario/geography/americas_caribbean.json"; TERRAIN=ROOT/"scenario/terrain/americas-caribbean.json"
WORLD=ROOT/"scenario/world/world.json"; ECONOMY=ROOT/"scenario/economy/economy.json"; MAPS=ROOT/"scenario/maps/world-map.json"
ID=re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
ROLES={"capital","major_port","trade_center","fortified_town","transition_location","historical_location","religious_location"}
WATER={"node_north_atlantic","node_great_lakes","node_mississippi","node_north_pacific","node_central_pacific","node_caribbean_sea","node_caribbean_islands","node_amazon_river","node_south_atlantic","node_magellan_sea","node_south_pacific"}
SEEDS=[
 ("haudenosaunee_council_fire","Haudenosaunee Council Fire","haudenosaunee_nations","haudenosaunee_homelands","americas_north_atlantic",[88,62],"forest","node_north_america_east_land",["capital","trade_center","historical_location"]),
 ("wendat_council_network","Wendat Council Network","wendat_confederacies","wendat_georgian_bay","americas_north_atlantic",[70,78],"forest","node_great_lakes",["capital","trade_center"]),
 ("anishinaabe_seasonal_council","Anishinaabe Seasonal Council","anishinaabe_networks","anishinaabe_upper_lakes","americas_north_atlantic",[48,86],"forest","node_great_lakes",["capital","trade_center"]),
 ("moundville","Moundville","cahokian_successor_centers","mississippi_southeast_centers","americas_north_atlantic",[82,22],"riverbank","node_mississippi",["capital","trade_center","religious_location"]),
 ("pueblo_council_network","Pueblo Council Network","pueblo_world","pueblo_rio_grande_mesa","americas_north_pacific",[78,35],"upland","node_north_america_west_land",["capital","trade_center","religious_location"]),
 ("northwest_coast_house_councils","Northwest Coast House Councils","northwest_coast_nations","northwest_coast_homelands","americas_north_pacific",[52,90],"coast","node_north_pacific",["capital","major_port","trade_center","transition_location"]),
 ("tenochtitlan","Tenochtitlan","mexica_tenochtitlan","tenochtitlan_domain","americas_mexico_central",[62,28],"plains","node_central_america_land",["capital","trade_center","fortified_town","religious_location"]),
 ("texcoco","Texcoco","acolhua_texcoco","texcoco_domain","americas_mexico_central",[69,30],"plains","node_central_america_land",["capital","trade_center"]),
 ("tlaxcallan_council","Tlaxcallan Council","tlaxcallan_confederation","tlaxcallan_four_altepetl","americas_mexico_central",[78,34],"upland","node_central_america_land",["capital","fortified_town"]),
 ("tzintzuntzan","Tzintzuntzan","purepecha_state","purepecha_michoacan","americas_mexico_central",[48,30],"upland","node_central_america_land",["capital","trade_center","fortified_town"]),
 ("yucatan_kuchkabal_courts","Yucatan Kuchkabal Courts","yucatan_maya_jurisdictions","yucatan_kuchkabal","americas_mexico_central",[104,24],"coast","node_caribbean_sea",["capital","major_port","trade_center"]),
 ("qumarkaj","Q'umarkaj","kiche_kingdom","kiche_highlands","americas_mexico_central",[91,18],"upland","node_central_america_land",["capital","fortified_town","religious_location"]),
 ("taino_cacique_seats","Taino Cacique Seats","taino_cacicazgos","taino_greater_antilles","americas_caribbean_islands",[72,52],"island","node_caribbean_islands",["capital","major_port","trade_center","transition_location"]),
 ("kalinago_council_network","Kalinago Council Network","kalinago_island_communities","kalinago_lesser_antilles","americas_caribbean_islands",[125,32],"island","node_caribbean_islands",["capital","major_port"]),
 ("bacata","Bacata","muisca_zipazgo","muisca_bacata","americas_north_south",[66,42],"upland","node_north_andes_land",["capital","trade_center","religious_location"]),
 ("hunza","Hunza","muisca_zacazgo","muisca_hunza","americas_north_south",[72,52],"upland","node_north_andes_land",["capital","trade_center"]),
 ("amazonian_earthwork_centers","Amazonian Earthwork Centers","amazonian_regional_societies","amazon_riverine_societies","americas_amazon_brazil",[52,62],"riverbank","node_amazon_river",["capital","major_port","trade_center","historical_location"]),
 ("tupi_village_councils","Tupi Village Councils","tupi_coastal_networks","tupi_atlantic_coast","americas_amazon_brazil",[94,42],"coast","node_south_atlantic",["capital","major_port","trade_center"]),
 ("cusco","Cusco","tawantinsuyu","inca_cusco_heartland","americas_andes_southern_cone",[54,70],"upland","node_southern_cone_land",["capital","trade_center","fortified_town","religious_location"]),
 ("chan_chan","Chan Chan","chimor_kingdom","chimor_north_coast","americas_andes_southern_cone",[36,92],"coast","node_south_pacific",["capital","major_port","trade_center","fortified_town"]),
 ("la_cent_in","La Centinela","chincha_lordship","chincha_valley","americas_andes_southern_cone",[48,82],"coast","node_south_pacific",["capital","major_port","trade_center"]),
 ("mapuche_rewe_assemblies","Mapuche Rewe Assemblies","mapuche_rewe_confederacies","mapuche_ngulumapu","americas_andes_southern_cone",[64,38],"forest","node_southern_cone_land",["capital","fortified_town"])
]

class AmericasContentError(ValueError): pass
def _index(rows,label):
 out={}
 if not isinstance(rows,list): raise AmericasContentError(f"{label} must be an array")
 for row in rows:
  ident=row.get("id") if isinstance(row,dict) else None
  if not isinstance(ident,str) or not ID.fullmatch(ident) or ident in out: raise AmericasContentError(f"{label}: invalid or duplicate ID {ident!r}")
  out[ident]=row
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
  n=pending.pop()
  if n not in seen: seen.add(n); pending.extend(graph.get(n,()))
 return seen
def seed_source():
 settlements=[]
 for n,(sid,name,pid,vid,rid,pos,terrain,zone,roles) in enumerate(SEEDS):
  port=zone in WATER and "major_port" in roles; services=["market","banking","warehouse"]+(["port_services"] if port else [])
  goods=[["maize","cotton","cacao"],["fish","timber","salt"],["potatoes","textiles","copper"]][n%3]
  item={"id":sid,"name":name,"polityId":pid,"provinceId":vid,"regionalInstanceId":rid,"physicalMapId":rid,"position":pos,"terrainClass":terrain,"navigationZoneId":zone,"roles":roles,"services":services,"economy":{"production":goods,"imports":["tools","iron_goods"],"shortages":["horses","gunpowder"]},"defenseClass":"capital" if "capital" in roles else "port" if port else "city"}
  if port: item["port"]={"maritimeZoneId":zone,"access":"river" if terrain=="riverbank" else "coastal"}
  settlements.append(item)
 routes=[]
 def add(a,b,k): routes.append({"id":f"route_{a}_{b}","fromSettlementId":a,"toSettlementId":b,"kind":k,"contract":"settlement_trade_endpoint"})
 land=["haudenosaunee_council_fire","wendat_council_network","anishinaabe_seasonal_council","moundville","pueblo_council_network","tenochtitlan","texcoco","tlaxcallan_council","tzintzuntzan","qumarkaj","bacata","hunza","cusco","mapuche_rewe_assemblies"]
 for a,b in zip(land,land[1:]): add(a,b,"overland")
 ports=[x[0] for x in SEEDS if "major_port" in x[-1]]
 for a,b in zip(ports,ports[1:]): add(a,b,"maritime")
 return {"schemaVersion":1,"id":"americas_caribbean_content_1450","campaignStartDate":"1450-01-01","coverageRule":"selective_global_importance_gameplay_navigation_performance","placementRules":{"minimumSeparationCells":5,"entryAnchorClearanceCells":5},"settlements":settlements,"tradeRoutes":routes,"requiredMainlandEndpoints":land,"requiredMaritimeZones":sorted({next(x for x in settlements if x['id']==p)['port']['maritimeZoneId'] for p in ports}),"transitions":[{"id":"transition_americas_europe","settlementId":"taino_cacique_seats","boundaryAnchorId":"americas_atlantic_entry","neighborRegionId":"europe","stub":True},{"id":"transition_americas_africa","settlementId":"taino_cacique_seats","boundaryAnchorId":"americas_atlantic_entry","neighborRegionId":"africa","stub":True},{"id":"transition_americas_east_asia","settlementId":"northwest_coast_house_councils","boundaryAnchorId":"americas_pacific_entry","neighborRegionId":"east_asia","stub":True},{"id":"transition_americas_pacific","settlementId":"northwest_coast_house_councils","boundaryAnchorId":"americas_pacific_entry","neighborRegionId":"pacific","stub":True}]}

def validate(source_path=SOURCE):
 source=json.loads(Path(source_path).read_text()); politics=json.loads(POLITICS.read_text()); geography=json.loads(GEOGRAPHY.read_text()); terrain=json.loads(TERRAIN.read_text()); maps=json.loads(MAPS.read_text())
 settlements=_index(source.get("settlements"),"settlements"); polities=_index(politics["polities"],"polities"); provinces={p["id"]:(x["id"],p) for x in polities.values() for p in x["provinces"]}; instances=_index(geography["instances"],"instances"); nodes=_index(geography["navigationTopology"]["nodes"],"navigation nodes"); anchors=_index(geography["boundaryAnchors"],"anchors"); policies={x["id"]:x for x in terrain["instancePolicies"]}
 if source.get("schemaVersion")!=1 or source.get("campaignStartDate")!="1450-01-01": raise AmericasContentError("invalid content version")
 positions={}
 for sid,x in settlements.items():
  if x.get("polityId") not in polities or x.get("provinceId") not in provinces or provinces[x["provinceId"]][0]!=x["polityId"]: raise AmericasContentError(f"settlement {sid}: polity/province mismatch")
  rid=x.get("regionalInstanceId"); pos=x.get("position"); bounds=instances.get(rid,{}).get("localBounds",{})
  if x.get("physicalMapId")!=rid or maps["regionalInstanceRegions"].get(rid)!="americas_caribbean": raise AmericasContentError(f"settlement {sid}: invalid physical-map assignment")
  if not isinstance(pos,list) or len(pos)!=2 or not bounds.get("minX",1)<=pos[0]<=bounds.get("maxX",0) or not bounds.get("minY",1)<=pos[1]<=bounds.get("maxY",0): raise AmericasContentError(f"settlement {sid}: position outside local bounds")
  masks=policies[rid]["landMasks"]
  if masks and not any(_inside(pos,m) for m in masks): raise AmericasContentError(f"settlement {sid}: position is not valid land terrain")
  if x.get("navigationZoneId") not in nodes or nodes[x["navigationZoneId"]]["class"] in {"impassable_barrier","decorative_water"}: raise AmericasContentError(f"settlement {sid}: invalid navigation zone")
  if not x.get("roles") or not set(x["roles"])<=ROLES or set(x.get("economy",{}))!={"production","imports","shortages"}: raise AmericasContentError(f"settlement {sid}: invalid roles or economy profile")
  if set(x["economy"]["production"])&set(x["economy"]["shortages"]): raise AmericasContentError(f"settlement {sid}: production cannot be a shortage")
  port=x.get("port")
  if port and (x["terrainClass"] not in {"coast","riverbank","island"} or "major_port" not in x["roles"] or port.get("maritimeZoneId") not in WATER): raise AmericasContentError(f"settlement {sid}: invalid port access")
  if not port and "major_port" in x["roles"]: raise AmericasContentError(f"settlement {sid}: inland settlement exposes maritime access")
  positions[sid]={"x":pos[0],"y":pos[1]}
 ids=sorted(settlements)
 for n,a in enumerate(ids):
  for b in ids[n+1:]:
   if settlements[a]["regionalInstanceId"]==settlements[b]["regionalInstanceId"] and math.dist(tuple(positions[a].values()),tuple(positions[b].values()))<source["placementRules"]["minimumSeparationCells"]: raise AmericasContentError(f"settlements overlap: {a} and {b}")
 routes=_index(source.get("tradeRoutes"),"routes"); land=[]; sea=[]
 for rid,r in routes.items():
  a,b=r.get("fromSettlementId"),r.get("toSettlementId"); kind=r.get("kind")
  if a not in settlements or b not in settlements or a==b or r.get("contract")!="settlement_trade_endpoint": raise AmericasContentError(f"trade route {rid}: invalid endpoint contract")
  if kind=="maritime":
   if "port" not in settlements[a] or "port" not in settlements[b]: raise AmericasContentError(f"trade route {rid}: inland maritime route")
   sea.append((a,b))
  else: land.append((a,b))
 req=set(source["requiredMainlandEndpoints"])
 if req-_reachable(land,next(iter(req))): raise AmericasContentError("mainland trade endpoints are not connected")
 ports={x for e in sea for x in e}
 if {x for x,v in settlements.items() if "port" in v}-ports: raise AmericasContentError("maritime port network is disconnected")
 transitions=_index(source.get("transitions"),"transitions")
 if {x["neighborRegionId"] for x in transitions.values()}!={"europe","africa","east_asia","pacific"}: raise AmericasContentError("regional transitions are incomplete")
 for tid,t in transitions.items():
  if t.get("settlementId") not in settlements or t.get("boundaryAnchorId") not in anchors or t.get("stub") is not True or "transition_location" not in settlements[t["settlementId"]]["roles"]: raise AmericasContentError(f"transition {tid}: invalid reference")
 return source,politics,geography,positions

def project(source,politics,geography,positions,world):
 world=project_politics(politics,copy.deepcopy(world)); sids={x["id"] for x in source["settlements"]}; zones={x["id"]:x for x in world["navigationZones"]}
 world["settlements"]=[x for x in world["settlements"] if x["id"] not in sids]; world["cityCores"]=[x for x in world["cityCores"] if x["id"] not in {"city_core_"+s for s in sids}]; world["defenseLayouts"]=[x for x in world["defenseLayouts"] if x["id"] not in {"defense_"+s for s in sids}]
 for node in geography["navigationTopology"]["nodes"]:
  move=["flying"] if node["class"] in {"impassable_barrier","decorative_water"} else ["naval","amphibious","flying"] if node["class"] in {"navigable_sea","navigable_river","island_coast"} else ["land","amphibious","flying"]
  zones.setdefault(node["id"],{"id":node["id"],"movementClasses":move,"connections":{m:[] for m in move}})
 for link in geography["navigationTopology"]["links"]:
  for m in link["movementClasses"]:
   for a,b in ((link["from"],link["to"]),(link["to"],link["from"])):
    if m in zones[a]["connections"] and b not in zones[a]["connections"][m]: zones[a]["connections"][m].append(b)
 world["navigationZones"]=[zones[x] for x in sorted(zones)]
 for x in source["settlements"]:
  sid=x["id"]; roles=x["roles"]; record={"id":sid,"name":x["name"],"kind":"capital" if "capital" in roles else "port" if "major_port" in roles else "fort" if "fortified_town" in roles else "major_city","provinceId":x["provinceId"],"legalOwnerPolityId":x["polityId"],"controllerPolityId":x["polityId"],"capturable":True,"civilianFacilitiesInvulnerable":True,"navigationZoneId":x["navigationZoneId"],"cityCoreId":"city_core_"+sid,"defenseLayoutId":"defense_"+sid,"serviceIds":x["services"],"regionalInstanceId":x["regionalInstanceId"],"physicalMapId":x["physicalMapId"],"localPosition":positions[sid],"terrainClass":x["terrainClass"],"roleIds":roles,"activation":{"runtimeState":"abstract","representationTemplateId":"settlement_representation","deterministicKey":sid},"economicProfile":copy.deepcopy(x["economy"]),"productionRefs":x["economy"]["production"]}
  if x.get("port"): record["portAccess"]=copy.deepcopy(x["port"])
  world["settlements"].append(record); world["cityCores"].append({"id":"city_core_"+sid,"objectTemplateId":"capital_city_core" if "capital" in roles else "city_core"}); world["defenseLayouts"].append({"id":"defense_"+sid,"objectTemplateIds":["capital_defenses" if "capital" in roles else "port_defenses" if "major_port" in roles else "city_defenses"]})
 for p in world["provinces"]: p["settlementIds"]=[x["id"] for x in world["settlements"] if x.get("provinceId")==p["id"]]
 return world

def update_economy(source,economy):
 economy=copy.deepcopy(economy); c=economy["catalog"]; state=economy["state"]; keep=lambda rows:[x for x in rows if not x.get("id","").startswith("amer_")]
 for key in ("stores","markets","prices","producers"): c[key]=keep(c[key])
 state["storeBalances"]=keep(state["storeBalances"])
 for n,x in enumerate(source["settlements"]):
  sid="amer_"+x["id"]+"_store"; mid="amer_"+x["id"]+"_market"; port="major_port" in x["roles"]
  c["stores"].append({"id":sid,"kind":"warehouse","owner":{"kind":"settlement","id":x["id"]},"capacityUnits":50000 if "trade_center" in x["roles"] else 20000,"allowedGoodIds":["grain","flour","ship_provisions"]}); c["markets"].append({"id":mid,"storeId":sid,"owner":{"kind":"settlement","id":x["id"]}}); c["producers"].append({"id":"amer_"+x["id"]+"_producer","storeId":sid,"recipeId":"prepare_ship_provisions" if port else "mill_grain_into_flour","owner":{"kind":"settlement","id":x["id"]}}); c["prices"].append({"id":"amer_"+x["id"]+"_grain_price","marketId":mid,"goodId":"grain","currencyId":"pound_sterling","quantityUnits":100,"amountMinor":9+n%9}); state["storeBalances"].append({"id":sid,"storeId":sid,"goods":[{"goodId":"grain","quantityUnits":1000+n*83},{"goodId":"ship_provisions","quantityUnits":500+n*31}],"currencies":[{"currencyId":"pound_sterling","amountMinor":1600+n*113}]})
 return economy

def main(argv=None):
 argv=sys.argv[1:] if argv is None else argv
 try:
  if argv==["--seed"]: SOURCE.write_text(json.dumps(seed_source(),ensure_ascii=False,indent=2)+"\n")
  source,politics,geography,positions=validate()
  if argv==["--write"]: WORLD.write_text(json.dumps(project(source,politics,geography,positions,json.loads(WORLD.read_text())),ensure_ascii=False,indent=2)+"\n"); ECONOMY.write_text(json.dumps(update_economy(source,json.loads(ECONOMY.read_text())),ensure_ascii=False,indent=2)+"\n")
  elif argv not in ([],["--seed"]): raise AmericasContentError("usage: americas_caribbean_content.py [--seed|--write]")
  print(f"Americas/Caribbean content valid: {len(source['settlements'])} settlements, {sum('port' in x for x in source['settlements'])} ports, {len(source['tradeRoutes'])} routes")
 except (OSError,json.JSONDecodeError,KeyError,AmericasContentError) as e: print(f"Americas/Caribbean content validation failed: {e}",file=sys.stderr); return 1
 return 0
if __name__=="__main__": raise SystemExit(main())

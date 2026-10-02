#!/usr/bin/env python3
"""Deterministically author the Phase 8 Pacific release-density expansion."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"scenario/settlements/pacific-1450.json"
POLITICS=ROOT/"scenario/politics/pacific-1450.json"

# Political/ceremonial centers use the stable IDs already declared by the
# authoritative polity catalogue. Coordinates are deliberately local map cells:
# they sit inside the reviewed island masks instead of pretending that the
# compressed maps are a continuous geographic projection.
ADDITIONS=[
 ("unangan_council","Unangan Island Council","unangan_island_communities","aleutian_island_communities","pacific_north_hawaii",[13,82],"upland",False,["political_center","voyaging_center","historical_location"]),
 ("hawaii_royal_center","Hawaiʻi Royal Center","hawaii_chiefdom","hawaii_island","pacific_north_hawaii",[22,8],"upland",False,["political_center","religious_location","historical_location"]),
 ("maui_royal_center","Maui Royal Center","maui_chiefdom","maui_nui","pacific_north_hawaii",[15,60],"island",True,["political_center","anchorage","voyaging_center"]),
 ("oahu_royal_center","Oʻahu Royal Center","oahu_chiefdom","oahu","pacific_north_hawaii",[39,60],"island",False,["political_center","religious_location"]),
 ("kauai_royal_center","Kauaʻi Royal Center","kauai_chiefdom","kauai_niihau","pacific_north_hawaii",[18,62],"island",False,["political_center","historical_location"]),
 ("guam_council","Guåhan Chiefs' Council","chamorro_chiefdoms","mariana_chiefdoms","pacific_micronesia",[48,77],"island",False,["political_center","religious_location"]),
 ("belau_council","Belau Chiefs' Council","belau_chiefdoms","belau_islands","pacific_micronesia",[19,17],"island",False,["political_center","religious_location"]),
 ("yap_council","Yap Council and Exchange Anchorage","yapese_domains","western_caroline_domains","pacific_micronesia",[44,42],"island",True,["political_center","anchorage","trade_center","voyaging_center"]),
 ("marshall_council","Marshall Atoll Irooj Council","marshallese_irooj_domains","marshall_atoll_domains","pacific_micronesia",[28,20],"island",True,["political_center","anchorage","voyaging_center"]),
 ("tungaru_maneaba","Tungaru Maneaba","tungaru_maneaba_communities","tungaru_atoll_communities","pacific_micronesia",[65,13],"island",True,["political_center","anchorage","religious_location","voyaging_center"]),
 ("new_guinea_council","Eastern New Guinea Exchange Council","new_guinea_exchange_communities","eastern_new_guinea_communities","pacific_melanesia",[10,62],"coast",True,["political_center","anchorage","trade_center"]),
 ("bismarck_council","Bismarck Island Council","bismarck_island_communities","bismarck_archipelago","pacific_melanesia",[39,62],"island",False,["political_center","historical_location"]),
 ("solomon_council","Solomon Island Chiefs' Council","solomon_island_chiefdoms","solomon_archipelago","pacific_melanesia",[64,46],"island",False,["political_center","historical_location"]),
 ("vanuatu_council","Vanuatu Chiefs' Council","vanuatu_chiefdoms","vanuatu_archipelago","pacific_melanesia",[91,15],"island",False,["political_center","religious_location"]),
 ("kanak_council","Kanak Chiefs' Council","kanak_chiefdoms","kanak_country","pacific_melanesia",[78,31],"island",True,["political_center","anchorage","trade_center"]),
 ("fiji_council","Fijian Vanua Council","fijian_vanua","fijian_vanua","pacific_west_polynesia",[49,30],"island",False,["political_center","religious_location"]),
 ("samoa_fono","Samoan Fono","samoan_chiefly_districts","samoan_districts","pacific_east_polynesia",[14,45],"island",False,["political_center","religious_location"]),
 ("tahiti_council","Tahiti Chiefs' Council","tahiti_chiefdoms","society_island_chiefdoms","pacific_east_polynesia",[40,35],"island",False,["political_center","religious_location"]),
 ("marquesas_council","Marquesan Valley Council","marquesan_chiefdoms","marquesan_valleys","pacific_east_polynesia",[52,58],"upland",False,["political_center","fortified_settlement","religious_location"]),
 ("tuamotu_council","Tuamotu Atoll Council Anchorage","tuamotu_atoll_communities","tuamotu_gambier_communities","pacific_east_polynesia",[34,42],"island",True,["political_center","anchorage","voyaging_center"]),
 ("anakena","Anakena","rapa_nui_clans","rapa_nui","pacific_east_polynesia",[89,5],"coast",False,["political_center","religious_location","historical_location"]),
 ("aotearoa_runanga","Aotearoa Rūnanga","maori_iwi_hapu","aotearoa_iwi_territories","pacific_new_zealand",[51,43],"upland",False,["political_center","historical_location"]),
 ("rotorua_kainga","Rotorua Kāinga","maori_iwi_hapu","aotearoa_iwi_territories","pacific_new_zealand",[63,32],"upland",False,["production_center","historical_location"]),
]

ROLE_ALIAS={"production_center":"trade_center"}
NODE={"pacific_north_hawaii":"node_hawaii_coast","pacific_micronesia":"node_micronesia_islands","pacific_melanesia":"node_melanesia_sea","pacific_west_polynesia":"node_fiji_coast","pacific_east_polynesia":"node_east_polynesia_sea","pacific_new_zealand":"node_new_zealand_sea"}
MAP={"pacific_north_hawaii":"pacific_north","pacific_micronesia":"pacific_west","pacific_melanesia":"pacific_melanesia","pacific_west_polynesia":"pacific_polynesia","pacific_east_polynesia":"pacific_polynesia","pacific_new_zealand":"pacific_new_zealand"}

def main():
 data=json.loads(PATH.read_text()); politics=json.loads(POLITICS.read_text()); data["placementRules"]["minimumSeparationCells"]=3
 polity={x["id"]:x for x in politics["polities"]}
 evidence={x["id"] for x in politics["historicalEvidence"]}
 for row in data["settlements"]:
  p=polity[row["polityId"]]; row.setdefault("evidenceIds",p["evidenceIds"]); row.setdefault("authorityType",p["structure"]); row.setdefault("routeImportance","oceanic" if "transition_location" in row["roles"] else "regional")
 existing={x["id"] for x in data["settlements"]}
 for sid,name,pid,province,instance,pos,terrain,port,roles in ADDITIONS:
  if sid in existing:
   next(x for x in data["settlements"] if x["id"]==sid)["position"]=pos
   continue
  p=polity[pid]; roles=[ROLE_ALIAS.get(x,x) for x in roles]
  item={"id":sid,"name":name,"polityId":pid,"provinceId":province,"regionalInstanceId":instance,"physicalMapId":MAP[instance],"position":pos,"terrainClass":terrain,"navigationZoneId":NODE[instance],"roles":roles,"services":["market","storage","crafting"],"economy":{"production":["taro","fish","barkcloth"],"imports":["stone_adzes","timber"],"shortages":["iron_goods","gunpowder"],"tradeEndpointIds":[sid+"_exchange"]},"captureModel":"non_capturable_community","evidenceIds":p["evidenceIds"],"authorityType":p["structure"],"routeImportance":"regional"}
  if port:
   item["services"] += ["port_services","ship_repair"]
   item["port"]={"maritimeZoneId":NODE[instance],"access":"island_anchorage"}
  data["settlements"].append(item)
 # Preserve minor communities authoritatively without paying physical-object cost.
 data["abstractCommunities"]=[{"id":"abstract_"+p["id"],"polityId":p["id"],"provinceIds":[x["id"] for x in p["provinces"]],"communityNames":p["preservedEntities"],"runtimeRepresentation":"authoritative_state_only","activationPolicy":"remain_abstract_unless_scenario_required","evidenceIds":p["evidenceIds"]} for p in politics["polities"] if p.get("preservedEntities")]
 # New ports branch from the nearest established network node; all routes remain
 # bounded endpoint contracts rather than continuously simulated ocean lanes.
 links={
  "maui_royal_center":"honolulu_anchorage","yap_council":"koror","marshall_council":"nan_madol","tungaru_maneaba":"nan_madol","new_guinea_council":"rabaul_exchange_harbor","kanak_council":"vanuatu_exchange_anchorage","tuamotu_council":"taputapuatea"}
 existing_routes={x["id"] for x in data["tradeRoutes"]}
 for a,b in links.items():
  rid="route_"+a+"_"+b
  if rid not in existing_routes: data["tradeRoutes"].append({"id":rid,"fromSettlementId":a,"toSettlementId":b,"kind":"maritime","contract":"settlement_trade_endpoint","importance":"regional"})
 # Land links make every physically represented authority reachable locally.
 by_instance={}
 for x in data["settlements"]: by_instance.setdefault(x["regionalInstanceId"],[]).append(x)
 for instance,rows in by_instance.items():
  hub=rows[0]["id"]
  for x in rows[1:]:
   if "port" in x: continue
   rid="route_local_"+hub+"_"+x["id"]
   if rid not in existing_routes: data["tradeRoutes"].append({"id":rid,"fromSettlementId":hub,"toSettlementId":x["id"],"kind":"overland","contract":"settlement_trade_endpoint","importance":"local"})
 for route in data["tradeRoutes"]: route.setdefault("importance","oceanic" if route["id"] in {"route_honolulu_hagatna","route_taputapuatea_hanga_roa","route_lakeba_tamaki"} else "regional")
 assert all(e in evidence for x in data["settlements"] for e in x["evidenceIds"])
 PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")

if __name__=="__main__": main()

#!/usr/bin/env python3
"""Reproducibly author the Phase 8 Americas/Caribbean density pass.

The grouped table is a compact historical gazetteer.  Group entries deliberately
include councils, villages, mound/ceremonial centres, pueblos, island anchorages,
river nodes and pukaras instead of treating every settlement as a European city.
"""
from __future__ import annotations
import json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"scenario/settlements/americas-caribbean-1450.json"

# polity, province, instance, approximate lon/lat, settlement IDs (* = port/anchorage)
GROUPS=[
 ("haudenosaunee_nations","haudenosaunee_homelands","americas_north_atlantic",(-76,43),"onondaga_council_fire ganondagan oneida_castle cayuga_village seneca_council"),
 ("wendat_confederacies","wendat_georgian_bay","americas_north_atlantic",(-80,44),"ossossane cahiague scanonaenat teanaustaye"),
 ("anishinaabe_networks","anishinaabe_upper_lakes","americas_north_atlantic",(-85,47),"baawitigong michilimackinac* manitoulin_council chequamegon*"),
 ("inuit_north_atlantic_communities","inuit_labrador_greenland","americas_north_atlantic",(-57,58),"inuit_seasonal_camps okak* nachvak* kalaallit_winter_camp*"),
 ("cahokian_successor_centers","mississippi_southeast_centers","americas_north_atlantic",(-89,34),"coosa_etowah spiro_mounds parkins_mounds natchez_emerald_mound caddoan_belcher"),
 ("pueblo_world","pueblo_rio_grande_mesa","americas_north_pacific",(-108,35),"awanyu_ohkay_owingeh acoma_pueblo zuni_hawikku walpi_tusayan taos_pueblo"),
 ("northwest_coast_nations","northwest_coast_homelands","americas_north_pacific",(-130,52),"sgang_gwaay* metlakatla* kitwanga yuquot* sxwoxwiymelh"),
 ("mexica_tenochtitlan","tenochtitlan_domain","americas_mexico_central",(-99.1,19.4),"tlatelolco xochimilco coyoacan culhuacan"),
 ("acolhua_texcoco","texcoco_domain","americas_mexico_central",(-98.9,19.5),"coatlinchan huexotla teotihuacan_acolhua"),
 ("tepanec_tlacopan","tlacopan_domain","americas_mexico_central",(-99.2,19.5),"tlacopan azcapotzalco coyohuacan_tepanec"),
 ("tlaxcallan_confederation","tlaxcallan_four_altepetl","americas_mexico_central",(-98.2,19.3),"tepeticpac ocotelulco tizatlan quiahuiztlan"),
 ("purepecha_state","purepecha_michoacan","americas_mexico_central",(-101.7,19.6),"ihuatzio patzcuaro zacapu ucareo"),
 ("chalco_confederation","chalco_altepetl","americas_mexico_central",(-98.9,19.3),"chalco_atenco amaquemecan tlalmanalco"),
 ("yucatan_maya_jurisdictions","yucatan_kuchkabal","americas_mexico_central",(-89,20.5),"mani_yucatan sotuta tihoo champoton* ecab*"),
 ("itza_kingdom","itza_peten","americas_mexico_central",(-89.9,16.9),"nohpeteen zacpeten yaxha"),
 ("kiche_kingdom","kiche_highlands","americas_mexico_central",(-91,15),"chichicastenango zaculeu kiche_chi_ismachi"),
 ("kaqchikel_kingdom","kaqchikel_highlands","americas_mexico_central",(-90.8,14.8),"ximche mixco_viejo solola"),
 ("taino_cacicazgos","taino_greater_antilles","americas_caribbean_islands",(-72,19),"jaragua* maguana magua_marien higuey* el_cobre_cuba* guanabacoa* caparra_boriken*"),
 ("kalinago_island_communities","kalinago_lesser_antilles","americas_caribbean_islands",(-61.5,15),"waitukubuli* karukera* hairouna* oualie* kallinago_tobago*"),
 ("muisca_zipazgo","muisca_bacata","americas_north_south",(-74,4.7),"facatativa zipacon guatavita pasca"),
 ("muisca_zacazgo","muisca_hunza","americas_north_south",(-73,5.5),"sogamoso duitama ramiriqui"),
 ("tairona_chiefdoms","tairona_sierra_nevada","americas_north_south",(-73.8,11),"tairona_mountain_centers teyuna pocigueica chairama*"),
 ("tawantinsuyu","inca_cusco_heartland","americas_andes_southern_cone",(-72,-13),"ollantaytambo pisac vilcashuaman pachacamac* jauja"),
 ("tawantinsuyu","inca_southern_highlands","americas_andes_southern_cone",(-69,-17),"hatunqulla chucuito paria tiwanaku_successor"),
 ("chimor_kingdom","chimor_north_coast","americas_andes_southern_cone",(-79,-8),"tucume lambayeque farfan pacatnamu*"),
 ("chincha_lordship","chincha_valley","americas_andes_southern_cone",(-76,-14),"tambo_de_mora* chincha_alta pisco_anchorage*"),
 ("amazonian_regional_societies","amazon_riverine_societies","americas_amazon_brazil",(-55,-3),"santarem_tapajos* marajo_successor* kuikuro_earthworks upper_xingu_plaza montanha_mound"),
 ("tupi_coastal_networks","tupi_atlantic_coast","americas_amazon_brazil",(-44,-18),"tupinamba_gabara* tupiniquim_village* guanabara_anchorage* sao_vicente_ancestral*"),
 ("mapuche_rewe_confederacies","mapuche_ngulumapu","americas_andes_southern_cone",(-72,-39),"tucapel_rewe arauco_rewe puren_rewe lumaco_rewe"),
 ("diaguita_calchaqui_lordships","diaguita_calchaqui_valleys","americas_andes_southern_cone",(-66,-27),"calchaqui_pukara_network quilmes_pukara tolombon shincal"),
 ("guarani_tekohas","guarani_parana_paraguay","americas_amazon_brazil",(-57,-26),"guarani_assembly_network paranay_tekohas itati_council mbya_forest_villages"),
 ("charrua_minuan_networks","charrua_uruguay_grasslands","americas_andes_southern_cone",(-56,-33),"charrua_seasonal_assemblies yi_river_camp santa_lucia_camp"),
 ("selknam_yaghan_communities","fuegian_archipelago","americas_andes_southern_cone",(-68,-54),"fuegian_seasonal_camps yaghan_canoe_camp* selknam_haruwen"),
]

EVIDENCE=[
 {"id":"americas_native_atlas","citation":"William C. Sturtevant, ed., Handbook of North American Indians (Smithsonian Institution, 1978–2008); Gordon R. Willey, An Introduction to American Archaeology (1966–1971).","note":"Supports Indigenous settlement forms, approximate locations, political contexts, and regional networks near 1450."},
 {"id":"mesoamerica_andes_gazetteer","citation":"Michael E. Smith, The Aztecs, 3rd ed. (2012); Terence N. D'Altroy, The Incas, 2nd ed. (2014); The Cambridge History of the Native Peoples of the Americas (1996–2000).","note":"Supports Mesoamerican altepetl and Maya courts, Andean administrative and ceremonial centers, chronology, and control."},
 {"id":"caribbean_amazon_networks","citation":"William F. Keegan and Corinne L. Hofman, The Caribbean before Columbus (2017); Clark L. Erickson, Amazonia: The Historical Ecology of a Domesticated Landscape (2006).","note":"Supports island anchorages, chiefdom seats, riverine centers, earthworks, and decentralized community representations."},
]

def inside(point,poly):
 x,y=point; hit=False
 for n,(x1,y1) in enumerate(poly):
  x2,y2=poly[n-1]
  if (y1>y)!=(y2>y) and x<(x2-x1)*(y-y1)/(y2-y1)+x1: hit=not hit
 return hit

def main():
 data=json.loads(SOURCE.read_text()); politics=json.loads((ROOT/"scenario/politics/americas-caribbean-1450.json").read_text())
 geography=json.loads((ROOT/"scenario/geography/americas_caribbean.json").read_text()); terrain=json.loads((ROOT/"scenario/terrain/americas-caribbean.json").read_text())
 instances={x["id"]:x for x in geography["instances"]}; policies={x["id"]:x for x in terrain["instancePolicies"]}; capitals={x["capitalSettlementId"] for x in politics["polities"]}
 authored={v.rstrip('*') for *_,names in GROUPS for v in names.split()}; data["settlements"]=[x for x in data["settlements"] if x["id"] not in authored]
 for row in data["settlements"]:
  row.setdefault("sourcePosition",[round(row["position"][0]/2-100,3),round(row["position"][1]/2-30,3)])
  row.setdefault("historicalEvidenceIds",["americas_native_atlas"])
  row.setdefault("controlContext",{"date":"1450-01-01","status":"legal_and_effective_control","basis":"political_baseline"})
  row.setdefault("availability",{"from":"1450-01-01","to":None})
 occupied={k:[x["position"] for x in data["settlements"] if x["regionalInstanceId"]==k] for k in instances}; new_ports=[]
 water={"americas_north_atlantic":"node_north_atlantic","americas_north_pacific":"node_north_pacific","americas_mexico_central":"node_caribbean_sea","americas_caribbean_islands":"node_caribbean_islands","americas_north_south":"node_caribbean_sea","americas_amazon_brazil":"node_amazon_river","americas_andes_southern_cone":"node_south_pacific"}
 land={"americas_north_atlantic":"node_north_america_east_land","americas_north_pacific":"node_north_america_west_land","americas_mexico_central":"node_central_america_land","americas_caribbean_islands":"node_caribbean_islands","americas_north_south":"node_north_andes_land","americas_amazon_brazil":"node_amazon_river","americas_andes_southern_cone":"node_southern_cone_land"}
 for polity,province,instance,centre,names in GROUPS:
  for j,raw in enumerate(names.split()):
   ident=raw.rstrip('*'); port=raw.endswith('*')
   if any(x["id"]==ident for x in data["settlements"]): continue
   bounds=instances[instance]["localBounds"]; chosen=None
   for y in range(math.ceil(bounds["minY"])+1,math.floor(bounds["maxY"]),2):
    for x in range(math.ceil(bounds["minX"])+1,math.floor(bounds["maxX"]),2):
     p=[x,y]
     if any(math.dist(p,q)<data["placementRules"]["minimumSeparationCells"] for q in occupied[instance]): continue
     if policies[instance]["landMasks"] and not any(inside(p,m) for m in policies[instance]["landMasks"]): continue
     chosen=p; break
    if chosen: break
   if not chosen: raise RuntimeError(f"no placement budget for {ident}")
   occupied[instance].append(chosen); roles=["historical_location","trade_center"]
   if ident in capitals: roles.insert(0,"capital")
   if port: roles.insert(0,"major_port")
   elif j%3==0: roles.append("fortified_town")
   if any(k in ident for k in ("mound","pukara","council","plaza","pachacamac")): roles.append("religious_location")
   services=["market","quest_hub"]+(["warehouse"] if "trade_center" in roles else [])+(["port_services"] if port else [])+(["banking"] if "capital" in roles else [])
   row={"id":ident,"name":ident.replace('_',' ').title(),"polityId":polity,"provinceId":province,"regionalInstanceId":instance,"physicalMapId":instance,"sourcePosition":[round(centre[0]+(j%3-1)*.25,3),round(centre[1]+(j//3)*.2,3)],"position":chosen,"terrainClass":"coast" if port else "riverbank" if instance=="americas_amazon_brazil" else "upland" if instance in {"americas_mexico_central","americas_north_south","americas_andes_southern_cone"} else "forest","navigationZoneId":water[instance] if port else land[instance],"roles":roles,"services":services,"economy":{"production":["fish","timber"] if port else ["maize","textiles"],"imports":["tools","salt"],"shortages":["iron_goods"]},"defenseClass":"capital" if "capital" in roles else "port" if port else "local_defense","historicalEvidenceIds":["caribbean_amazon_networks" if instance in {"americas_caribbean_islands","americas_amazon_brazil"} else "mesoamerica_andes_gazetteer" if instance in {"americas_mexico_central","americas_north_south","americas_andes_southern_cone"} else "americas_native_atlas"],"controlContext":{"date":"1450-01-01","status":"legal_and_effective_control","basis":"political_baseline"},"availability":{"from":"1450-01-01","to":None}}
   if port: row["port"]={"maritimeZoneId":water[instance],"access":"river_anchorage" if instance=="americas_amazon_brazil" else "coastal_anchorage"}; new_ports.append(ident)
   data["settlements"].append(row)
 # Keep every new port in the maritime graph without disturbing stable route IDs.
 ports=[x["id"] for x in data["settlements"] if "port" in x]
 routed={v for r in data["tradeRoutes"] if r["kind"]=="maritime" for v in (r["fromSettlementId"],r["toSettlementId"])}
 hub="taino_cacique_seats"
 for ident in ports:
  if ident not in routed:
   data["tradeRoutes"].append({"id":f"route_{hub}_{ident}","fromSettlementId":hub,"toSettlementId":ident,"kind":"maritime","contract":"settlement_trade_endpoint"})
 data["historicalEvidence"]=EVIDENCE
 data["abstractCommunities"]=[{"id":"compressed_mobile_and_seasonal_communities","polityIds":[x["id"] for x in politics["polities"] if x.get("structure")=="decentralized"],"representation":"authoritative_abstract_state","activationPolicy":"regional_on_demand"}]
 data["coverageRule"]="release_scale_historical_density_with_bounded_runtime_representation"
 SOURCE.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
 print(f"Authored {len(data['settlements'])} Americas/Caribbean settlements")

if __name__=="__main__": main()

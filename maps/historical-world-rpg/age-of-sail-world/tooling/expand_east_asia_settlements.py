#!/usr/bin/env python3
"""Reproducibly author the Phase 8 East Asia settlement-density expansion.

The source catalogue remains authoritative.  This helper preserves the original
priority-settlement IDs and makes the larger reviewed addition reproducible.
"""
from __future__ import annotations

import json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

# id, name, polity, province, instance, longitude, latitude, terrain, roles
ADDITIONS=[
 ("tianjin","Tianjin","ming_empire","ming_beizhili","east_asia_china_north",117.20,39.13,"coast","major_port market_center river_node"),
 ("baoding","Baoding","ming_empire","ming_beizhili","east_asia_china_north",115.47,38.87,"plains","administrative_seat fortified_town"),
 ("datong","Datong","ming_empire","ming_shanxi_shaanxi","east_asia_china_north",113.30,40.08,"upland","fortified_town market_center"),
 ("taiyuan","Taiyuan","ming_empire","ming_shanxi_shaanxi","east_asia_china_north",112.55,37.87,"riverbank","administrative_seat market_center"),
 ("pingyang","Pingyang","ming_empire","ming_shanxi_shaanxi","east_asia_china_north",111.52,36.08,"riverbank","market_center fortified_town"),
 ("yanan","Yan'an","ming_empire","ming_shanxi_shaanxi","east_asia_china_north",109.49,36.59,"upland","fortified_town historical_location"),
 ("jinan","Jinan","ming_empire","ming_shandong_henan","east_asia_china_north",117.00,36.65,"plains","administrative_seat market_center"),
 ("qingzhou","Qingzhou","ming_empire","ming_shandong_henan","east_asia_china_north",118.48,36.68,"plains","market_center fortified_town"),
 ("dengzhou","Dengzhou","ming_empire","ming_shandong_henan","east_asia_china_north",120.75,37.81,"coast","major_port fortified_town"),
 ("jining","Jining","ming_empire","ming_shandong_henan","east_asia_china_north",116.59,35.41,"riverbank","canal_node market_center"),
 ("luoyang","Luoyang","ming_empire","ming_shandong_henan","east_asia_china_north",112.45,34.62,"riverbank","market_center cultural_site"),
 ("zhengzhou","Zhengzhou","ming_empire","ming_shandong_henan","east_asia_china_north",113.62,34.75,"riverbank","market_center river_node"),
 ("xiangyang","Xiangyang","ming_empire","ming_huguang_sichuan","east_asia_china_north",112.14,32.04,"riverbank","fortified_town river_node"),
 ("ningxia","Ningxia","ming_empire","ming_shanxi_shaanxi","east_asia_china_north",106.23,38.49,"riverbank","fortified_town frontier_post"),
 ("ganzhou","Ganzhou, Gansu","ming_empire","ming_shanxi_shaanxi","east_asia_china_north",100.45,38.93,"upland","fortified_town route_node"),
 ("jiayuguan","Jiayu Pass","ming_empire","ming_shanxi_shaanxi","east_asia_interior",98.29,39.77,"upland","fortified_town route_node"),
 ("turpan","Turpan","kara_del_hami","kara_del_hami","east_asia_interior",89.19,42.95,"upland","market_center route_node"),
 ("beshbalik","Beshbalik","oirat_confederation","oirat_dzungaria","east_asia_interior",89.18,44.17,"upland","historical_location route_node"),
 ("karakorum","Karakorum","northern_yuan_khanate","northern_yuan_domains","east_asia_interior",102.83,47.20,"upland","cultural_site market_center"),
 ("hohhot_tumet","Tumet Pastures","northern_yuan_khanate","northern_yuan_domains","east_asia_interior",111.65,40.82,"plains","market_center historical_location"),
 ("oirat_eastern_encampment","Oirat Eastern Encampment","oirat_confederation","oirat_eastern_mongolia","east_asia_interior",108.50,46.50,"plains","frontier_post route_node historical_location"),
 ("lhasa","Lhasa","phagmodrupa_dynasty","phagmodrupa_u_tsang","east_asia_interior",91.12,29.65,"upland","religious_location cultural_site market_center"),
 ("gyantse","Gyantse","rinpungpa_house","rinpungpa_tsang","east_asia_interior",89.60,28.92,"upland","fortified_town market_center"),
 ("shigatse","Shigatse","rinpungpa_house","rinpungpa_tsang","east_asia_interior",88.88,29.27,"upland","religious_location market_center"),
 ("wuchang","Wuchang","ming_empire","ming_huguang_sichuan","east_asia_china_south",114.30,30.55,"riverbank","administrative_seat river_node market_center"),
 ("jingzhou","Jingzhou","ming_empire","ming_huguang_sichuan","east_asia_china_south",112.24,30.34,"riverbank","fortified_town river_node"),
 ("changsha","Changsha","ming_empire","ming_huguang_sichuan","east_asia_china_south",112.94,28.23,"riverbank","administrative_seat market_center"),
 ("changde","Changde","ming_empire","ming_huguang_sichuan","east_asia_china_south",111.69,29.03,"riverbank","market_center river_node"),
 ("chongqing","Chongqing","ming_empire","ming_huguang_sichuan","east_asia_china_south",106.55,29.56,"riverbank","fortified_town river_node market_center"),
 ("baoning","Baoning","ming_empire","ming_huguang_sichuan","east_asia_china_south",105.97,31.58,"upland","administrative_seat fortified_town"),
 ("kunming","Yunnan","ming_empire","ming_huguang_sichuan","east_asia_china_south",102.71,25.04,"upland","administrative_seat market_center"),
 ("guiyang","Guiyang","ming_empire","ming_huguang_sichuan","east_asia_china_south",106.63,26.65,"upland","administrative_seat fortified_town"),
 ("yangzhou","Yangzhou","ming_empire","ming_nanzhili","east_asia_china_south",119.41,32.39,"riverbank","canal_node market_center production_center"),
 ("zhenjiang","Zhenjiang","ming_empire","ming_nanzhili","east_asia_china_south",119.42,32.19,"riverbank","fortified_town canal_node"),
 ("songjiang","Songjiang","ming_empire","ming_nanzhili","east_asia_china_south",121.23,31.03,"coast","major_port production_center"),
 ("huizhou","Huizhou","ming_empire","ming_nanzhili","east_asia_china_south",118.34,29.72,"upland","market_center production_center"),
 ("ningbo","Ningbo","ming_empire","ming_fujian_zhejiang","east_asia_china_south",121.55,29.87,"coast","major_port market_center"),
 ("wenzhou","Wenzhou","ming_empire","ming_fujian_zhejiang","east_asia_china_south",120.70,28.00,"coast","major_port market_center"),
 ("fuzhou","Fuzhou","ming_empire","ming_fujian_zhejiang","east_asia_china_south",119.30,26.08,"coast","administrative_seat major_port"),
 ("zhangzhou","Zhangzhou","ming_empire","ming_fujian_zhejiang","east_asia_china_south",117.65,24.52,"coast","market_center production_center"),
 ("chaozhou","Chaozhou","ming_empire","ming_lingnan","east_asia_china_south",116.62,23.66,"coast","major_port market_center"),
 ("zhaoqing","Zhaoqing","ming_empire","ming_lingnan","east_asia_china_south",112.47,23.05,"riverbank","administrative_seat river_node"),
 ("wuzhou","Wuzhou","ming_empire","ming_lingnan","east_asia_china_south",111.28,23.48,"riverbank","market_center river_node"),
 ("guilin","Guilin","ming_empire","ming_lingnan","east_asia_china_south",110.29,25.27,"upland","administrative_seat fortified_town"),
 ("nanning","Nanning","ming_empire","ming_lingnan","east_asia_china_south",108.32,22.82,"riverbank","market_center fortified_town"),
 ("hainan_qiongzhou","Qiongzhou","ming_empire","ming_lingnan","east_asia_china_south",110.35,20.02,"island","major_port administrative_seat"),
 ("wonsan","Anbyeon","joseon_kingdom","joseon_hamgil_pyeongan","east_asia_korea",127.52,39.04,"plains","administrative_seat fortified_town"),
 ("hamhung","Hamhung","joseon_kingdom","joseon_hamgil_pyeongan","east_asia_korea",127.54,39.91,"plains","administrative_seat fortified_town"),
 ("pyongyang","Pyeongyang","joseon_kingdom","joseon_hamgil_pyeongan","east_asia_korea",125.75,39.03,"riverbank","administrative_seat market_center fortified_town"),
 ("uiju","Uiju","joseon_kingdom","joseon_hamgil_pyeongan","east_asia_korea",124.53,40.20,"riverbank","fortified_town route_node"),
 ("kaesong","Gaeseong","joseon_kingdom","joseon_central_provinces","east_asia_korea",126.55,37.97,"plains","market_center cultural_site"),
 ("wonju","Wonju","joseon_kingdom","joseon_central_provinces","east_asia_korea",127.94,37.34,"upland","administrative_seat market_center"),
 ("cheongju","Cheongju","joseon_kingdom","joseon_central_provinces","east_asia_korea",127.49,36.64,"plains","administrative_seat market_center"),
 ("jeonju","Jeonju","joseon_kingdom","joseon_southern_provinces","east_asia_korea",127.15,35.82,"plains","administrative_seat production_center"),
 ("gyeongju","Gyeongju","joseon_kingdom","joseon_southern_provinces","east_asia_korea",129.22,35.86,"plains","cultural_site religious_location"),
 ("jinju","Jinju","joseon_kingdom","joseon_southern_provinces","east_asia_korea",128.08,35.18,"riverbank","fortified_town market_center"),
 ("nagasaki","Kuchinotsu","ashikaga_shogunate","ashikaga_kyushu","east_asia_japan",130.19,32.61,"coast","major_port market_center"),
 ("dazaifu","Dazaifu","ashikaga_shogunate","ashikaga_kyushu","east_asia_japan",130.52,33.52,"plains","religious_location administrative_seat"),
 ("kagoshima","Kagoshima","ashikaga_shogunate","ashikaga_kyushu","east_asia_japan",130.56,31.60,"coast","major_port fortified_town"),
 ("yamaguchi","Yamaguchi","ashikaga_shogunate","ashikaga_western_honshu_shikoku","east_asia_japan",131.47,34.19,"upland","administrative_seat market_center"),
 ("shimonoseki","Shimonoseki","ashikaga_shogunate","ashikaga_western_honshu_shikoku","east_asia_japan",130.94,33.96,"coast","major_port route_node"),
 ("hiroshima","Itsukushima","ashikaga_shogunate","ashikaga_western_honshu_shikoku","east_asia_japan",132.32,34.30,"island","major_port religious_location"),
 ("izumo","Izumo","ashikaga_shogunate","ashikaga_western_honshu_shikoku","east_asia_japan",132.75,35.37,"coast","religious_location production_center"),
 ("himeji","Himeji","ashikaga_shogunate","ashikaga_western_honshu_shikoku","east_asia_japan",134.69,34.82,"plains","fortified_town route_node"),
 ("osaka","Watanabe","ashikaga_shogunate","ashikaga_kinai","east_asia_japan",135.51,34.69,"coast","major_port market_center"),
 ("nara","Nara","ashikaga_shogunate","ashikaga_kinai","east_asia_japan",135.80,34.69,"plains","religious_location cultural_site"),
 ("otsu","Otsu","ashikaga_shogunate","ashikaga_kinai","east_asia_japan",135.87,35.02,"riverbank","market_center route_node"),
 ("kanazawa","Kanazawa","ashikaga_shogunate","ashikaga_western_honshu_shikoku","east_asia_japan",136.66,36.56,"coast","market_center fortified_town"),
 ("nagoya","Owari","ashikaga_shogunate","ashikaga_eastern_honshu","east_asia_japan",136.91,35.18,"plains","market_center fortified_town"),
 ("sunpu","Sunpu","ashikaga_shogunate","ashikaga_eastern_honshu","east_asia_japan",138.38,34.98,"coast","administrative_seat market_center"),
 ("odawara","Odawara","ashikaga_shogunate","ashikaga_eastern_honshu","east_asia_japan",139.16,35.25,"coast","fortified_town market_center"),
 ("edo","Musashi Fuchu","ashikaga_shogunate","ashikaga_eastern_honshu","east_asia_japan",139.48,35.67,"plains","administrative_seat market_center"),
 ("nikko","Nikko","ashikaga_shogunate","ashikaga_eastern_honshu","east_asia_japan",139.60,36.75,"upland","religious_location cultural_site"),
 ("sendai","Shiogama","ashikaga_shogunate","ashikaga_eastern_honshu","east_asia_japan",141.02,38.32,"coast","major_port religious_location"),
 ("aomori","Tosaminato","ashikaga_shogunate","ashikaga_eastern_honshu","east_asia_japan",140.30,41.06,"coast","major_port market_center"),
 ("tokushima","Awa","ashikaga_shogunate","ashikaga_western_honshu_shikoku","east_asia_japan",134.55,34.07,"coast","major_port production_center"),
 ("matsuyama","Iyo","ashikaga_shogunate","ashikaga_western_honshu_shikoku","east_asia_japan",132.77,33.84,"coast","major_port fortified_town"),
 ("hirado","Hirado","ashikaga_shogunate","ashikaga_kyushu","east_asia_japan",129.55,33.37,"island","major_port market_center"),
 ("nakijin","Nakijin","ryukyu_kingdom","ryukyu_islands","east_asia_china_south",127.97,26.69,"island","fortified_town historical_location"),
 ("kumejima","Kume Island","ryukyu_kingdom","ryukyu_islands","east_asia_china_south",126.77,26.34,"island","major_port route_node"),
 ("tamsui","Tamsui","taiwan_indigenous_domains","taiwan_indigenous_domains","east_asia_china_south",121.44,25.17,"coast","major_port historical_location"),
 ("tainan_siraya","Siraya Council Place","taiwan_indigenous_domains","taiwan_indigenous_domains","east_asia_china_south",120.20,23.00,"coast","major_port cultural_site"),
 ("ningguta","Hurha Council Place","jianzhou_jurchen","jianzhou_jurchen_domains","east_asia_china_north",129.47,44.35,"forest","market_center cultural_site"),
 ("jilin_ula","Jilin Ula","haixi_jurchen","haixi_jurchen_domains","east_asia_china_north",126.55,43.84,"riverbank","market_center river_node"),
 ("sanxing","Sanxing Council Place","wild_jurchen_confederacies","wild_jurchen_domains","east_asia_northeast_pacific",130.55,46.80,"riverbank","market_center cultural_site"),
 ("tyr_amur","Tyr","wild_jurchen_confederacies","wild_jurchen_domains","east_asia_northeast_pacific",136.15,52.93,"riverbank","cultural_site route_node"),
 ("otaru_ainu","Yoichi Ainu Port","ainu_moshir","ainu_ezo","east_asia_japan",140.77,43.19,"island","major_port market_center"),
 ("shiraoi_ainu","Shiraoi Council Place","ainu_moshir","ainu_ezo","east_asia_japan",141.35,42.55,"island","cultural_site historical_location"),
 ("aniva_council","Aniva Council Place","sakhalin_communities","sakhalin_ainu_nivkh","east_asia_northeast_pacific",142.55,46.67,"coast","major_port cultural_site"),
]

EVIDENCE=[
 {"id":"east_asia_urban_networks","citation":"The Cambridge History of China, vol. 7 (1988); The Cambridge History of Japan, vol. 3 (1990); The Cambridge History of Korea, vol. 2 (2022).","note":"Supports fifteenth-century administrative centers, urban hierarchies, fortified towns, ports, and cultural sites."},
 {"id":"east_asia_routes_ports","citation":"Janet L. Abu-Lughod, Before European Hegemony (1989); Angela Schottenhammer, ed., The East Asian Maritime World 1400–1800 (2007).","note":"Supports canal, river, overland, and maritime commercial networks and their principal nodes."},
 {"id":"east_asia_historical_atlas","citation":"The Times Atlas of World History, 4th ed. (1993); Geoffrey Barraclough, ed., The Times Atlas of World History (1978).","note":"Supports approximate real-world placement and 1450 political-geographic context."},
]

WATER_BY_INSTANCE={"east_asia_china_north":"node_east_china_sea","east_asia_china_south":"node_south_china_sea","east_asia_korea":"node_japan_sea","east_asia_japan":"node_japan_sea","east_asia_northeast_pacific":"node_okhotsk_sea"}
NODE_BY_INSTANCE={"east_asia_interior":"node_central_asia_gate","east_asia_china_north":"node_north_china","east_asia_china_south":"node_south_china","east_asia_korea":"node_korea_land","east_asia_japan":"node_japan_coast","east_asia_northeast_pacific":"node_okhotsk_sea"}

def inside(point,polygon):
 x,y=point; result=False
 for n,(x1,y1) in enumerate(polygon):
  x2,y2=polygon[n-1]
  if (y1>y)!=(y2>y) and x<(x2-x1)*(y-y1)/(y2-y1)+x1: result=not result
 return result

def services(roles):
 out=["market","quest_hub"]
 if set(roles)&{"market_center","trade_center","production_center","canal_node","river_node"}: out.append("warehouse")
 if "major_port" in roles: out.append("port_services")
 return out

def main():
 path=ROOT/"scenario/settlements/east-asia-1450.json"; data=json.loads(path.read_text())
 geo=json.loads((ROOT/"scenario/geography/east_asia.json").read_text()); terrain=json.loads((ROOT/"scenario/terrain/east-asia.json").read_text())
 instances={x["id"]:x for x in geo["instances"]}; policies={x["id"]:x for x in terrain["instancePolicies"]}; anchors=geo["boundaryAnchors"]
 authored={x[0] for x in ADDITIONS}; data["settlements"]=[x for x in data["settlements"] if x["id"] not in authored]
 evidence=[x["id"] for x in EVIDENCE]
 for row in data["settlements"]:
  row.setdefault("historicalEvidenceIds",evidence); row.setdefault("controlContext",{"date":"1450-01-01","status":"legal_and_effective_control","basis":"east_asia_1450_political_baseline"})
  if "sourcePosition" not in row:
   t=instances[row["regionalInstanceId"]]["transform"]; row["sourcePosition"]=[round(row["position"][0]/t["scale"][0]+t["sourceOrigin"][0],4),round(row["position"][1]/t["scale"][1]+t["sourceOrigin"][1],4)]
 occupied={k:[] for k in instances}
 for row in data["settlements"]: occupied[row["regionalInstanceId"]].append(row["position"])
 for ident,name,polity,province,instance,lon,lat,terrain_class,role_text in ADDITIONS:
  t=instances[instance]["transform"]; bounds=instances[instance]["localBounds"]; raw=[(lon-t["sourceOrigin"][0])*t["scale"][0],(lat-t["sourceOrigin"][1])*t["scale"][1]]
  policy=policies[instance]; chosen=None
  for radius in range(0,31):
   candidates=[(0,0)] if radius==0 else [(dx,dy) for dx in range(-radius,radius+1) for dy in range(-radius,radius+1) if max(abs(dx),abs(dy))==radius]
   for dx,dy in candidates:
    p=[round(raw[0]+dx*2.05,2),round(raw[1]+dy*2.05,2)]
    generated=terrain_class=="island" or (instance=="east_asia_japan" and not policy["landMasks"])
    valid_land=generated or any(inside(p,m) for m in policy["landMasks"])
    if bounds["minX"]<=p[0]<=bounds["maxX"] and bounds["minY"]<=p[1]<=bounds["maxY"] and valid_land and not any(inside(p,m) for m in policy["decorativeWaterMasks"]) and all(math.dist(p,q)>=2 for q in occupied[instance]) and all(a["instanceId"]!=instance or math.dist(p,a["local"])>=3 for a in anchors): chosen=p; break
   if chosen: break
  if chosen is None: raise RuntimeError(f"no valid placement for {ident}")
  roles=role_text.split(); production=["grain","textiles"] if "production_center" in roles else ["grain","tools"]
  row={"id":ident,"name":name,"polityId":polity,"provinceId":province,"regionalInstanceId":instance,"sourcePosition":[lon,lat],"position":chosen,"terrainClass":terrain_class,"navigationZoneId":NODE_BY_INSTANCE[instance],"physicalMapId":instance,"roles":roles,"services":services(roles),"economy":{"production":production,"imports":["salt","timber"],"shortages":["horses"]},"defenseClass":"port" if "major_port" in roles else "fortified" if "fortified_town" in roles else "town","historicalEvidenceIds":evidence,"controlContext":{"date":"1450-01-01","status":"legal_and_effective_control","basis":"east_asia_1450_political_baseline"}}
  if math.dist(raw,chosen)>.1: row["declaredDistortion"]={"offset":[round(chosen[0]-raw[0],2),round(chosen[1]-raw[1],2)],"reason":"Bounded gameplay displacement preserves access and separation on the compressed physical map."}
  if "major_port" in roles: row["port"]={"maritimeZoneId":WATER_BY_INSTANCE[instance],"access":"coastal"}
  data["settlements"].append(row); occupied[instance].append(chosen)
 # Extend the strategic networks without altering any original route IDs.
 originals={x["id"] for x in data["settlements"] if x["id"] not in authored}; routes=[x for x in data["tradeRoutes"] if not x["id"].startswith("route_density_")]
 for row in data["settlements"]:
  if row["id"] not in authored: continue
  candidates=[x for x in data["settlements"] if x["id"]!=row["id"] and x["regionalInstanceId"]==row["regionalInstanceId"] and (x["id"] in originals or x["id"]<row["id"])]
  near=min(candidates,key=lambda x:math.dist(x["position"],row["position"]))
  routes.append({"id":f"route_density_land_{row['id']}","fromSettlementId":near["id"],"toSettlementId":row["id"],"kind":"river" if set(row["roles"])&{"river_node","canal_node"} else "overland","contract":"settlement_trade_endpoint"})
 # The priority catalogue's Kyoto and Sakai records deliberately had no local
 # edge.  At release density they are one Kinai network, and this bridge also
 # keeps the eastern Honshu road chain reachable from the maritime backbone.
 routes.append({"id":"route_density_land_kyoto_sakai","fromSettlementId":"kyoto","toSettlementId":"sakai","kind":"overland","contract":"settlement_trade_endpoint"})
 ports=[x for x in data["settlements"] if "port" in x]
 original_ports=[x for x in ports if x["id"] in originals]
 for row in ports:
  if row["id"] not in authored: continue
  candidates=[x for x in ports if x["id"]!=row["id"] and (x["id"] in {p["id"] for p in original_ports} or x["id"]<row["id"])]
  near=min(candidates,key=lambda x:math.dist(x["sourcePosition"],row["sourcePosition"]))
  routes.append({"id":f"route_density_sea_{row['id']}","fromSettlementId":near["id"],"toSettlementId":row["id"],"kind":"maritime","contract":"settlement_trade_endpoint"})
 data["tradeRoutes"]=routes; data["historicalEvidence"]=EVIDENCE
 data["densityPolicy"]={"status":"regional_complete","globalRoadmapComplete":False,"rule":"historical_network_density_not_equal_polity_quotas","inactiveRuntimePolicy":"authoritative_abstract_until_regional_activation"}
 data["abstractCommunities"]=[
  {"id":"east_asia_steppe_mobile_communities","regionalInstanceId":"east_asia_interior","kind":"pastoral_and_mobile","rationale":"Pastoral camps remain authoritative population and economy state without fictitious permanent towns."},
  {"id":"east_asia_amur_forest_communities","regionalInstanceId":"east_asia_northeast_pacific","kind":"riverine_and_forest","rationale":"Dispersed Amur communities remain authoritative abstract state between selected route and council sites."},
  {"id":"east_asia_tibetan_highland_communities","regionalInstanceId":"east_asia_interior","kind":"monastic_pastoral_and_rural","rationale":"Highland communities are aggregated outside the principal seats and religious centers."}
 ]
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")

if __name__=="__main__": main()

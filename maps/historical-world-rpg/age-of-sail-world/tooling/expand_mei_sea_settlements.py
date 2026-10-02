#!/usr/bin/env python3
"""Reproducibly author the Phase 8 Middle East/India and Southeast Asia density pass.

The compact grouped tables are reviewed historical gazetteers.  Coordinates are
deliberately stored in the resulting authority files; placement offsets here only
separate close locations on Warcraft's compressed maps.
"""
from __future__ import annotations
import json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

# polity, province, regional instance, approximate province centre, settlement names.
# A trailing * denotes a historically significant port/anchorage.
MEI=[
 ("ottoman_empire","ottoman_anatolia","mei_anatolia_levant",(30.0,40.0),"bolu iznik ankara amasya tokat sinop* antalya* kutahya"),
 ("karamanids","karaman","mei_anatolia_levant",(33.0,37.5),"karaman larende alaiye* kayseri"),
 ("trebizond_empire","trebizond","mei_anatolia_levant",(39.5,40.8),"trebizond* giresun*"),
 ("dulkadirids","dulkadir","mei_anatolia_levant",(37.0,38.0),"el_bistan marash"),
 ("georgia","georgia","mei_anatolia_levant",(43.5,41.7),"tbilisi kutaisi gori"),
 ("cyprus","cyprus","mei_anatolia_levant",(33.2,35.0),"nicosia famagusta* limassol*"),
 ("mamluk_sultanate","mamluk_syria","mei_anatolia_levant",(35.5,33.5),"gaza acre* tripoli_levant* hamah homs safad"),
 ("sharifate_mecca","hejaz","mei_arabia_red_sea",(39.5,23.0),"medina yanbu* taif"),
 ("yemen","yemen","mei_arabia_red_sea",(44.0,15.0),"sanaa taizz mokha* hodeidah*"),
 ("kathiri","hadramawt","mei_arabia_red_sea",(48.5,15.8),"seiyun tarim shihr* mukalla*"),
 ("nabhanid_oman","oman","mei_arabia_red_sea",(57.0,23.0),"nizwa muscat* sohar* sur_oman*"),
 ("jabrids","najd_bahrain","mei_arabia_red_sea",(48.0,26.0),"al_ahsa qatif* manama* riyadh_oasis"),
 ("kingdom_hormuz","hormuz","mei_mesopotamia_persia",(56.0,26.5),"julfar* qeshm* bandar_abbas*"),
 ("qara_qoyunlu","qara_qoyunlu_azerbaijan","mei_mesopotamia_persia",(46.5,38.0),"ardabil maragha van"),
 ("qara_qoyunlu","qara_qoyunlu_iraq","mei_mesopotamia_persia",(44.0,34.0),"mosul kirkuk basra* hillah"),
 ("aq_qoyunlu","aq_qoyunlu_diyar_bakr","mei_mesopotamia_persia",(40.0,38.0),"amid mardin urfa"),
 ("shirvan","shirvan","mei_mesopotamia_persia",(49.0,40.5),"shamakhi baku* derbent*"),
 ("timurid_empire","transoxiana","mei_central_asia",(66.0,40.0),"bukhara tashkent khujand termiz"),
 ("timurid_empire","khurasan","mei_mesopotamia_persia",(58.0,35.0),"merv mashhad nishapur balkh"),
 ("timurid_empire","fars","mei_mesopotamia_persia",(52.5,30.5),"shiraz isfahan yazd kerman siraf*"),
 ("samma_sindh","sindh","mei_indus_deccan",(68.0,25.0),"thatta sehwan bukkur lahari_bandar*"),
 ("langah_multan","multan","mei_indus_deccan",(71.5,30.0),"multan uch dipalpur"),
 ("delhi_sultanate","punjab_delhi","mei_ganges_himalaya",(76.0,29.0),"sirhind panipat hisar agra"),
 ("kashmir_sultanate","kashmir","mei_ganges_himalaya",(74.5,34.0),"srinagar anantnag baramulla"),
 ("rajput_confederacies","rajputana","mei_indus_deccan",(74.0,26.0),"chittor jodhpur jaisalmer bikaner ajmer"),
 ("gujarat_sultanate","gujarat","mei_indus_deccan",(72.0,22.5),"patan bharuch* surat* diu* junagadh"),
 ("malwa_sultanate","malwa","mei_indus_deccan",(76.0,23.0),"ujjain dhar chanderi"),
 ("khandesh_sultanate","khandesh","mei_indus_deccan",(75.0,21.0),"burhanpur asirgarh thalner"),
 ("bahmani_sultanate","bahmani_deccan","mei_indus_deccan",(76.0,17.5),"gulbarga bijapur daulatabad dabhol* chaul*"),
 ("vijayanagara_empire","vijayanagara","mei_indus_deccan",(77.0,13.0),"srirangapatna kanchipuram madurai tiruchirappalli mangalore* cochin* kollam*"),
 ("gond_kingdoms","gondwana","mei_indus_deccan",(80.0,22.0),"garha deogarh chanda"),
 ("jaunpur_sultanate","jaunpur","mei_ganges_himalaya",(82.0,26.0),"jaunpur varanasi allahabad ayodhya"),
 ("nepal_malla","nepal","mei_ganges_himalaya",(85.3,27.7),"kathmandu bhaktapur patan_nepal"),
 ("western_himalayan_states","western_himalaya","mei_ganges_himalaya",(80.0,30.0),"jumla srinagar_garhwal champa"),
 ("bengal_sultanate","bengal","mei_bengal_ceylon",(89.0,24.0),"pandua sonargaon satgaon* sylhet rajmahal"),
 ("gajapati_empire","gajapati_orissa","mei_bengal_ceylon",(85.0,19.5),"cuttack puri rajahmundry masulipatnam*"),
 ("kamata_ahom_states","kamata_ahom","mei_bengal_ceylon",(91.0,26.0),"kamatapur garhgaon sadiya hajo"),
 ("kotte","kotte","mei_bengal_ceylon",(80.5,7.0),"sri_jayawardenepura_kotte colombo* galle*"),
 ("jaffna","jaffna","mei_bengal_ceylon",(80.0,9.5),"nallur mannar* trincomalee*"),
 ("maldives_sultanate","maldives","mei_bengal_ceylon",(73.0,4.0),"male* addu*"),
]

SEA=[
 ("ava_kingdom","ava_upper_burma","sea_mainland",(96.0,21.0),"sagaing pinya bagan shwebo"),
 ("toungoo_principality","toungoo","sea_mainland",(96.5,19.0),"toungoo pyay"),
 ("hanthawaddy_kingdom","hanthawaddy_pegu","sea_mainland",(96.0,16.5),"martaban* basssein* yangon_dagon*"),
 ("mrauk_u_kingdom","mrauk_u_arakan","sea_mainland",(93.0,20.0),"mrauk_u sittwe* ramree*"),
 ("shan_states","shan_states","sea_mainland",(98.0,22.0),"mong_yang hsipaw keng_tung"),
 ("lan_na_kingdom","lan_na","sea_mainland",(99.0,19.0),"chiang_mai chiang_rai lampang"),
 ("lan_xang_kingdom","lan_xang","sea_mainland",(102.0,18.0),"vientiane muang_phuan champasak"),
 ("ayutthaya_kingdom","ayutthaya_core","sea_mainland",(100.5,14.0),"lopburi sukhothai phitsanulok nakhon_sawan"),
 ("ayutthaya_kingdom","ayutthaya_tenasserim","sea_mainland",(99.0,10.0),"tenasserim* mergen* nakhon_si_thammarat*"),
 ("khmer_empire","khmer_angkor","sea_mainland",(104.5,12.5),"phnom_penh* lovek sambor"),
 ("dai_viet","dai_viet","sea_mainland",(106.0,20.0),"pho_hien* thanh_hoa van_don* nghe_an"),
 ("champa_kingdom","champa","sea_mainland",(109.0,13.0),"hoi_an* nha_trang* phan_rang*"),
 ("malacca_sultanate","malacca_sultanate","sea_malay_sumatra",(102.0,3.0),"muar* singapore* kedah* patani*"),
 ("samudera_pasai","samudera_pasai","sea_malay_sumatra",(97.0,5.0),"lamuri* perlak*"),
 ("minangkabau_kingdom","minangkabau","sea_malay_sumatra",(101.0,-1.0),"pagaruyung indrapura* siak*"),
 ("majapahit_empire","majapahit_java","sea_java_sunda",(112.0,-7.0),"tuban* gresik* surabaya* kediri"),
 ("sunda_kingdom","sunda_kingdom","sea_java_sunda",(107.0,-6.5),"pakuan_pajajaran banten* cirebon*"),
 ("bali_kingdoms","bali_kingdoms","sea_java_sunda",(115.0,-8.0),"gelgel samprangan lombok*"),
 ("brunei_sultanate","brunei_sultanate","sea_borneo",(114.0,4.5),"kota_batu* labuan*"),
 ("kutai_kingdom","kutai_kingdom","sea_borneo",(117.0,0.0),"muara_kaman kutai_lama* sambas*"),
 ("luzon_polities","luzon_polities","sea_philippines",(121.0,15.0),"manila* namayan* pangasinan* maynila*"),
 ("visayan_polities","visayan_polities","sea_philippines",(123.0,10.0),"panay* bohol* butuan*"),
 ("maguindanao_polities","mindanao_polities","sea_philippines",(124.0,7.0),"buayan* cotabato* davao_gulf*"),
 ("sulu_sultanate","sulu_sultanate","sea_philippines",(121.0,6.0),"basilan* tawi_tawi*"),
 ("makassar_polities","makassar_polities","sea_sulawesi_moluccas",(119.5,-4.0),"siang gowa* bone palopo*"),
 ("ternate_sultanate","ternate_sultanate","sea_sulawesi_moluccas",(127.0,1.0),"ternate_harbor* jailolo*"),
 ("tidore_sultanate","tidore_sultanate","sea_sulawesi_moluccas",(128.0,0.0),"tidore_harbor* makian*"),
 ("papuan_coastal_polities","papuan_coastal_polities","sea_new_guinea_west",(131.0,-2.0),"misool* waigeo* biak* fakfak*"),
]

EVIDENCE={
 "mei_gazetteer":{"citation":"C. E. Bosworth, Historic Cities of the Islamic World (2007); Joseph E. Schwartzberg, A Historical Atlas of South Asia, 2nd ed. (1992).","note":"Supports 1450 political context, urban hierarchy, ports, pilgrimage and caravan networks from Anatolia through India."},
 "indian_ocean":{"citation":"K. N. Chaudhuri, Trade and Civilisation in the Indian Ocean (1985); R. J. Barendse, The Arabian Seas (2002).","note":"Supports Gulf, Red Sea, Indian coast, island and monsoon-route settlement roles."},
 "sea_gazetteer":{"citation":"Nicholas Tarling, ed., The Cambridge History of Southeast Asia, vol. 1 (1992).","note":"Supports mainland courts, river cities, tributary centers and circa-1450 political control."},
 "sea_maritime":{"citation":"Anthony Reid, Southeast Asia in the Age of Commerce, 1450–1680 (1988–1993); Kenneth R. Hall, Maritime Trade and State Development in Early Southeast Asia (1985).","note":"Supports entrepots, smaller port polities, anchorages and archipelagic networks."},
}

def inside(p,poly):
 x,y=p; hit=False
 for n,(x1,y1) in enumerate(poly):
  x2,y2=poly[n-1]
  if (y1>y)!=(y2>y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1: hit=not hit
 return hit

def service(roles):
 out=["market","quest_hub"]
 if "trade_center" in roles: out.append("warehouse")
 if "major_port" in roles: out.append("port_services")
 if "capital" in roles: out.append("banking")
 return out

def expand(region,groups,target):
 path=ROOT/f"scenario/settlements/{region}-1450.json"; data=json.loads(path.read_text())
 politics=json.loads((ROOT/f"scenario/politics/{region}-1450.json").read_text()); capitals={p["capitalSettlementId"] for p in politics["polities"]}
 geography=json.loads((ROOT/f"scenario/geography/{'middle_east_india' if region=='middle-east-india' else 'southeast_asia'}.json").read_text()); instances={x["id"]:x for x in geography["instances"]}
 authored={token.rstrip('*') for g in groups for token in g[4].split()}; stale={"edirne"} if region=="middle-east-india" else set(); data["settlements"]=[x for x in data["settlements"] if x["id"] not in authored|stale]
 evidence=["mei_gazetteer","indian_ocean"] if region=="middle-east-india" else ["sea_gazetteer","sea_maritime"]
 for old in data["settlements"]:
  old.setdefault("sourcePosition",[round(old["position"][0]/4+20,3),round(old["position"][1]/4+5,3)])
  old.setdefault("historicalEvidenceIds",evidence); old.setdefault("controlContext",{"date":"1450-01-01","status":"legal_and_effective_control","basis":"political_baseline"}); old.setdefault("physicalMapId",old["regionalInstanceId"])
 existing={x["id"] for x in data["settlements"]}; occupied={k:[x["position"] for x in data["settlements"] if x["regionalInstanceId"]==k] for k in instances}
 global_occupied=[x["position"] for x in data["settlements"]]
 policies={}
 if region=="southeast-asia": policies={x["id"]:x for x in json.loads((ROOT/"scenario/terrain/southeast-asia.json").read_text())["instancePolicies"]}
 port_bases={"middle-east-india":{"red_sea_navigation":"jeddah","arabian_sea_navigation":"aden","persian_gulf_navigation":"hormuz","bay_of_bengal_navigation":"chittagong"},"southeast-asia":{"node_bay_bengal":"pegu","node_malacca_sea":"malacca","node_south_china_sea":"hoi_an","node_java_sea":"sunda_kelapa","node_philippine_sea":"cebu","node_celebes_sea":"ternate","node_eastern_sea":"raja_ampat"}}
 new_ports=[]; serial=0; added=[]
 for polity,province,instance,centre,names in groups:
  for j,raw in enumerate(names.split()):
   ident=raw.rstrip('*'); is_port=raw.endswith('*')
   if ident in existing: continue
   serial+=1; lon=round(centre[0]+((j%3)-1)*.32,3); lat=round(centre[1]+((j//3)-.5)*.28,3)
   roles=["trade_center","historical_location"]
   if ident in capitals: roles.insert(0,"capital")
   if is_port: roles.insert(0,"major_port")
   elif j%3==0: roles.append("fortified_town")
   bounds=instances[instance]["localBounds"]; chosen=None
   # Deterministic compressed placement; SEA additionally enforces authored land masks.
   min_y=max(0,math.ceil(bounds["minY"]))+1; max_y=min(99,math.floor(bounds["maxY"]))
   min_x=max(0,math.ceil(bounds["minX"]))+1; max_x=min(99,math.floor(bounds["maxX"]))
   for y in range(min_y,max_y,2):
    for x in range(min_x,max_x,2):
     p=[x,y]
     comparison=occupied[instance] if policies else global_occupied
     if any(math.dist(p,q)<2 for q in comparison): continue
     if policies:
      policy=policies[instance]
      if not any(inside(p,m) for m in policy["landMasks"]) or any(inside(p,m) for m in policy["decorativeWaterMasks"]): continue
     chosen=p; break
    if chosen: break
   if not chosen: raise RuntimeError(f"no placement budget for {ident}")
   occupied[instance].append(chosen); global_occupied.append(chosen); terrain="coast" if is_port else "riverbank" if j%4==1 else "plains"
   row={"id":ident,"name":ident.replace('_',' ').title(),"polityId":polity,"provinceId":province,"regionalInstanceId":instance,"physicalMapId":instance,"sourcePosition":[lon,lat],"position":chosen,"terrainClass":terrain,"roles":roles,"services":service(roles),"defenseClass":"capital" if "capital" in roles else "port" if is_port else "city","historicalEvidenceIds":evidence,"controlContext":{"date":"1450-01-01","status":"legal_and_effective_control","basis":"political_baseline"}}
   if region=="middle-east-india": row["productionRefs"]=["ship_provisions" if is_port else "grain"]
   else:
    row["economy"]={"production":["ship_provisions" if is_port else "rice"],"imports":["iron"],"shortages":["horses"]}
    row["navigationZoneId"]="node_mainland_west" if instance=="sea_mainland" and lon<103 else "node_mainland_east" if instance=="sea_mainland" else "node_sumatra_coast" if instance=="sea_malay_sumatra" else "node_java_coast" if instance=="sea_java_sunda" else "node_south_china_sea" if instance=="sea_borneo" else "node_philippine_sea" if instance=="sea_philippines" else "node_celebes_sea" if instance=="sea_sulawesi_moluccas" else "node_eastern_sea"
   if is_port:
    if region=="middle-east-india": zone="red_sea_navigation" if polity in {"sharifate_mecca","yemen"} else "persian_gulf_navigation" if polity in {"jabrids","kingdom_hormuz"} or ident in {"basra","baku","derbent"} else "bay_of_bengal_navigation" if instance in {"mei_bengal_ceylon","mei_ganges_himalaya"} else "arabian_sea_navigation"
    else: zone="node_bay_bengal" if instance=="sea_mainland" else "node_malacca_sea" if instance=="sea_malay_sumatra" else "node_java_sea" if instance in {"sea_java_sunda","sea_borneo"} else "node_philippine_sea" if instance=="sea_philippines" else "node_celebes_sea" if instance=="sea_sulawesi_moluccas" else "node_eastern_sea"
    row["port"]={"maritimeZoneId":zone,"access":"coastal_anchorage"}; row["navigationZoneId"]=zone if region=="southeast-asia" else row.get("navigationZoneId"); new_ports.append((ident,zone))
   data["settlements"].append(row); existing.add(ident); added.append(ident)
 # The gazetteers intentionally contain more candidates than the locked physical
 # budget. Prefer capitals, ports, and forts; the remainder stay represented by
 # the explicit compressed-community authority below.
 while len(data["settlements"])>target:
  drop=next((x for x in reversed(data["settlements"]) if x["id"] in added and not set(x["roles"])&{"capital","major_port","fortified_town"}),None)
  if drop is None: drop=next((x for x in reversed(data["settlements"]) if x["id"] in added and "capital" not in x["roles"] and "major_port" not in x["roles"]),None)
  if drop is None: raise RuntimeError(f"{region}: cannot compress candidates to budget")
  data["settlements"].remove(drop); added.remove(drop["id"])
 if len(data["settlements"])!=target: raise RuntimeError(f"{region}: expected {target}, got {len(data['settlements'])}")
 live={x["id"] for x in data["settlements"]}; new_ports=[x for x in new_ports if x[0] in live]
 routes=data["tradeRoutes"]; route_ids={x["id"] for x in routes}
 for ident,zone in new_ports:
  rid=f"density_maritime_{ident}"; base=port_bases[region][zone]
  if rid not in route_ids and ident!=base: routes.append({"id":rid,"fromSettlementId":base,"toSettlementId":ident,"kind":"maritime","contract":"settlement_trade_endpoint"})
 data["historicalEvidence"]=[{"id":x,**EVIDENCE[x]} for x in evidence]
 data["abstractCommunities"]=[{"id":f"{region.replace('-','_')}_compressed_communities","kind":"decentralized_and_rural","rationale":"Smaller rural, mobile, upland, riverine, and island communities remain authoritative simulated state where individual physical objects would exceed compression and active-object budgets."}]
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")

if __name__=="__main__":
 expand("middle-east-india",MEI,155)
 expand("southeast-asia",SEA,85)

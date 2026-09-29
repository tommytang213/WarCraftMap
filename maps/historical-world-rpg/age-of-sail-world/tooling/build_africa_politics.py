#!/usr/bin/env python3
"""Build Africa's authoritative 1450 political baseline and world projection."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scenario/politics/africa-1450.json"
WORLD = ROOT / "scenario/world/world.json"

# id, name, adjective, tier, native title, capital, instance, geographic features,
# provinces as (id, name, historical/administrative type, adjacent province ids).
# Broad entities deliberately describe their 1450 identity; they are not proxies for
# modern states. Fine borders are compressed while small, consequential polities remain.
POLITIES = [
 ("marinid_morocco","Marinid Sultanate","Marinid","king","Sultan","fez","africa_maghreb_med_atlantic",["coast_maghreb_atlantic_med","mountains_atlas"],[
  ("fez_meknes","Fez and Meknes","makhzen_heartland",["rif","central_morocco"]),("rif","Rif","mountain_region",["fez_meknes","tlemcen"]),("central_morocco","Marrakesh and Atlantic Morocco","compressed_provinces",["fez_meknes","sijilmasa"]),("sijilmasa","Sijilmasa and Tafilalt","oasis_region",["central_morocco","air"])]),
 ("zayyanid_tlemcen","Zayyanid Kingdom of Tlemcen","Zayyanid","king","Sultan","tlemcen_city","africa_maghreb_med_atlantic",["coast_maghreb_atlantic_med","mountains_atlas"],[
  ("tlemcen","Tlemcen","kingdom_heartland",["rif","central_maghreb"]),("central_maghreb","Central Maghreb","compressed_provinces",["tlemcen","hafsid_ifriqiya"])]),
 ("hafsid_sultanate","Hafsid Sultanate","Hafsid","king","Sultan","tunis","africa_maghreb_med_atlantic",["coast_maghreb_atlantic_med","mountains_atlas"],[
  ("hafsid_ifriqiya","Ifriqiya","sultanate_heartland",["central_maghreb","tripolitania"]),("tripolitania","Tripolitania","province",["hafsid_ifriqiya","mamluk_egypt"])]),
 ("mamluk_sultanate","Mamluk Sultanate","Mamluk","king","Sultan","cairo","africa_nile_red_sea",["river_nile","coast_red_sea_northeast"],[
  ("mamluk_egypt","Egypt","sultanate_heartland",["tripolitania","lower_nubia"])]),
 ("alodia","Kingdom of Alodia","Alodian","king","Basileus","soba","africa_nile_red_sea",["river_nile"],[
  ("alodia_realm","Alodia","kingdom",["lower_nubia","amhara"]),("lower_nubia","Lower Nubian Successor Lands","compressed_lordships",["mamluk_egypt","alodia_realm"])]),
 ("ethiopian_empire","Ethiopian Empire","Ethiopian","emperor","Negusa Nagast","ethiopian_royal_camp","africa_nile_red_sea",["mountains_ethiopian_highlands","river_nile"],[
  ("shewa","Shewa","imperial_heartland",["amhara","ifat"]),("amhara","Amhara and Lake Tana","compressed_provinces",["shewa","tigray","alodia_realm"]),("tigray","Tigray","province",["amhara","medri_bahri"])]),
 ("medri_bahri","Medri Bahri","Bahr Negash","prince","Bahr Negash","debarwa","africa_nile_red_sea",["mountains_ethiopian_highlands","coast_red_sea_northeast"],[
  ("medri_bahri","Medri Bahri","governorate",["tigray","beja_lands"])]),
 ("beja_confederations","Beja Confederations","Beja","none","Chief","suakin","africa_nile_red_sea",["coast_red_sea_northeast"],[
  ("beja_lands","Beja Lands","compressed_confederations",["medri_bahri","lower_nubia"])]),
 ("adal_sultanate","Sultanate of Adal","Adalite","king","Sultan","dakkar","africa_nile_red_sea",["mountains_ethiopian_highlands","strait_bab_el_mandeb"],[
  ("ifat","Ifat and Harar","sultanate_heartland",["shewa","zeila_coast"]),("zeila_coast","Zeila Coast","coastal_province",["ifat","warsangali"])]),
 ("warsangali_sultanate","Warsangali Sultanate","Warsangali","king","Sultan","las_khorey","africa_horn_swahili",["coast_somali_swahili"],[
  ("warsangali","Warsangali","sultanate",["zeila_coast","ajuran_realm"])]),
 ("ajuran_sultanate","Ajuran Sultanate","Ajuran","king","Sultan","mareeg","africa_horn_swahili",["coast_somali_swahili"],[
  ("ajuran_realm","Ajuran Realm","sultanate",["warsangali","mogadishu_hinterland"])]),
 ("mogadishu_sultanate","Sultanate of Mogadishu","Mogadishan","king","Sultan","mogadishu","africa_horn_swahili",["coast_somali_swahili"],[
  ("mogadishu_hinterland","Mogadishu and Benadir","city_state_hinterland",["ajuran_realm","lamu_archipelago"])]),
 ("kilwa_sultanate","Kilwa Sultanate","Kilwan","king","Sultan","kilwa_kisiwani","africa_horn_swahili",["coast_somali_swahili","island_zanzibar_pemba"],[
  ("kilwa_coast","Kilwa Coast","sultanate_domains",["zanzibar_pemba","sofala_coast"]),("zanzibar_pemba","Zanzibar and Pemba","island_domains",["kilwa_coast","mombasa"]),("sofala_coast","Sofala Coast","tributary_port_region",["kilwa_coast","mutapa"])]),
 ("mombasa","Mombasa","Mombasan","prince","Sheikh","mombasa_city","africa_horn_swahili",["coast_somali_swahili"],[
  ("mombasa","Mombasa","city_state",["zanzibar_pemba","malindi"])]),
 ("malindi","Malindi","Malindian","prince","Sheikh","malindi_city","africa_horn_swahili",["coast_somali_swahili"],[
  ("malindi","Malindi","city_state",["mombasa","lamu_archipelago"])]),
 ("pate_sultanate","Pate Sultanate","Pate","prince","Sultan","pate","africa_horn_swahili",["coast_somali_swahili"],[
  ("lamu_archipelago","Pate and the Lamu Archipelago","island_city_states",["malindi","mogadishu_hinterland"])]),
 ("mali_empire","Mali Empire","Malian","emperor","Mansa","niani","africa_sahara_sahel",["river_senegal_niger","desert_western_sahara"],[
  ("manding","Manding","imperial_heartland",["upper_senegal","middle_niger"]),("upper_senegal","Upper Senegal and Bambuk","province",["manding","jolof_realm"]),("middle_niger","Middle Niger and Timbuktu","imperial_province",["manding","songhai_realm","mossi_lands"])]),
 ("songhai_kingdom","Songhai Kingdom","Songhai","king","Sonni","gao","africa_sahara_sahel",["river_senegal_niger","desert_tenere_libyan"],[
  ("songhai_realm","Gao and Songhai","kingdom",["middle_niger","air"])]),
 ("jolof_empire","Jolof Empire","Jolof","king","Buurba","linguere","africa_sahara_sahel",["river_senegal_niger","desert_western_sahara"],[
  ("jolof_realm","Jolof and Cayor","confederated_realms",["upper_senegal","senegambia"]),("senegambia","Senegambian Mandinka States","compressed_tributaries",["jolof_realm","fouta_jallon"])]),
 ("fouta_jallon_polities","Fouta Jallon Polities","Fula and Jallonke","none","Chief","timbo","africa_west_guinea_congo",["coast_guinea_congo"],[("fouta_jallon","Fouta Jallon and Upper Guinea","distributed_polities",["senegambia","akan_forest","loango_coast"])]),
 ("mossi_kingdoms","Mossi Kingdoms","Mossi","king","Mogho Naba","ouagadougou","africa_sahara_sahel",["river_senegal_niger"],[
  ("mossi_lands","Mossi Lands","compressed_kingdoms",["middle_niger","hausa_west"])]),
 ("air_sultanate","Sultanate of Air","Air","king","Amenokal","agadez","africa_sahara_sahel",["desert_tenere_libyan"],[
  ("air","Air","sultanate",["songhai_realm","hausa_north"])]),
 ("kanem_bornu","Kanem-Bornu Empire","Kanembu","emperor","Mai","njimi","africa_sahara_sahel",["lake_chad","desert_tenere_libyan"],[
  ("kanem","Kanem","imperial_province",["bornu","air"]),("bornu","Bornu","imperial_heartland",["kanem","hausa_north"])]),
 ("kano","Kingdom of Kano","Kano","king","Sarki","kano_city","africa_sahara_sahel",["lake_chad"],[
  ("hausa_north","Kano","city_state_hinterland",["air","bornu","hausa_west","katsina"])]),
 ("katsina","Kingdom of Katsina","Katsina","king","Sarki","katsina_city","africa_sahara_sahel",["lake_chad"],[
  ("katsina","Katsina","city_state_hinterland",["hausa_north","gobir"])]),
 ("gobir","Kingdom of Gobir","Gobirawa","king","Sarki","gobir_city","africa_sahara_sahel",["desert_tenere_libyan"],[
  ("gobir","Gobir","city_state_hinterland",["katsina","hausa_west"])]),
 ("zazzau","Kingdom of Zazzau","Zazzau","king","Sarki","zazzau_city","africa_sahara_sahel",["lake_chad"],[
  ("hausa_west","Zazzau and Southern Hausaland","city_state_hinterland",["hausa_north","gobir","mossi_lands","nupe"])]),
 ("benin_kingdom","Kingdom of Benin","Edo","king","Oba","benin_city","africa_west_guinea_congo",["coast_guinea_congo"],[
  ("benin_realm","Benin Realm","kingdom",["oyo_realm","lower_niger"])]),
 ("oyo_kingdom","Kingdom of Oyo","Oyo","king","Alaafin","oyo_ile","africa_west_guinea_congo",["coast_guinea_congo"],[
  ("oyo_realm","Oyo Realm","kingdom",["benin_realm","nupe","akan_forest"])]),
 ("nupe_kingdom","Kingdom of Nupe","Nupe","king","Etsu","nupeko","africa_west_guinea_congo",["coast_guinea_congo"],[
  ("nupe","Nupe","kingdom",["oyo_realm","hausa_west","lower_niger"])]),
 ("igala_kingdom","Igala Kingdom","Igala","king","Ata","idah","africa_west_guinea_congo",["coast_guinea_congo"],[
  ("lower_niger","Lower Niger","kingdom",["nupe","benin_realm","kwararafa"])]),
 ("kwararafa_confederacy","Kwararafa Confederacy","Jukun","none","Aku Uka","wukari","africa_west_guinea_congo",["coast_guinea_congo"],[
  ("kwararafa","Kwararafa","confederacy",["lower_niger","bornu"])]),
 ("bonoman","Bonoman","Akan","king","Ohene","begho","africa_west_guinea_congo",["coast_guinea_congo"],[
  ("akan_forest","Akan Forest States","compressed_kingdoms",["oyo_realm","fouta_jallon"])]),
 ("kongo_kingdom","Kingdom of Kongo","Kongo","king","Manikongo","mbanza_kongo","africa_west_guinea_congo",["river_congo","coast_guinea_congo"],[
  ("kongo_core","Mpemba and Mbata","kingdom_heartland",["loango_coast","kongo_east"]),("kongo_east","Eastern Kongo","province",["kongo_core","luba_lands"])]),
 ("loango_kingdom","Kingdom of Loango","Loango","king","Maloango","buali","africa_west_guinea_congo",["river_congo","coast_guinea_congo"],[
  ("loango_coast","Loango Coast","kingdom",["kongo_core","fouta_jallon"])]),
 ("luba_kingdom","Kingdom of Luba","Luba","king","Mulopwe","mwibele","africa_great_lakes_rift",["lake_tanganyika_malawi","river_zambezi"],[
  ("luba_lands","Luba Heartland","emergent_kingdom",["kongo_east","lunda_lands"])]),
 ("lunda_polities","Lunda Polities","Lunda","none","Mwaantangaand","lunda_royal_camp","africa_great_lakes_rift",["river_zambezi"],[
  ("lunda_lands","Lunda Lands","compressed_chiefdoms",["luba_lands","maravi_lands"])]),
 ("buganda_kingdom","Kingdom of Buganda","Ganda","king","Kabaka","mengo","africa_great_lakes_rift",["lake_victoria","mountains_east_african_rift"],[
  ("buganda","Buganda","kingdom",["bunyoro","rwanda_burundi"])]),
 ("bunyoro_kitara","Kingdom of Bunyoro-Kitara","Nyoro","king","Omukama","bigo_bya_mugenyi","africa_great_lakes_rift",["lake_victoria","mountains_east_african_rift"],[
  ("bunyoro","Bunyoro-Kitara","kingdom",["buganda","rwanda_burundi"])]),
 ("rwanda_burundi_kingdoms","Rwanda and Burundi Kingdoms","Great Lakes","king","Mwami","nyanza","africa_great_lakes_rift",["lake_victoria","lake_tanganyika_malawi"],[
  ("rwanda_burundi","Rwanda and Burundi Highlands","compressed_kingdoms",["buganda","bunyoro","luba_lands"])]),
 ("mutapa_kingdom","Kingdom of Mutapa","Mutapa","king","Mwene Mutapa","zvongombe","africa_great_lakes_rift",["river_zambezi"],[
  ("mutapa","Zambezi Mutapa","kingdom",["great_zimbabwe","maravi_lands","sofala_coast"])]),
 ("great_zimbabwe","Kingdom of Zimbabwe","Zimbabwean","king","Mambo","great_zimbabwe_city","africa_southern_cape",["river_orange_limpopo","mountains_drakenberg"],[
  ("great_zimbabwe","Zimbabwe Plateau","kingdom",["mutapa","mapungubwe_successors"])]),
 ("maravi_polities","Maravi Polities","Maravi","none","Kalonga","mankhamba","africa_great_lakes_rift",["lake_tanganyika_malawi","river_zambezi"],[
  ("maravi_lands","Maravi Lands","compressed_chiefdoms",["lunda_lands","mutapa"])]),
 ("mapungubwe_successors","Limpopo and Mapungubwe Successor Polities","Limpopo","none","Chief","mapungubwe","africa_southern_cape",["river_orange_limpopo","mountains_drakenberg"],[
  ("mapungubwe_successors","Limpopo Polities","compressed_chiefdoms",["great_zimbabwe","kalahari_polities"])]),
 ("khoi_san_polities","Khoi and San Polities","Khoisan","none","Chief","khoi_san_seasonal_camp","africa_southern_cape",["coast_southern_africa","desert_namib_kalahari"],[
  ("kalahari_polities","Kalahari and Cape Polities","distributed_polities",["mapungubwe_successors","namib_polities"]),("namib_polities","Namib and Southwestern Polities","distributed_polities",["kalahari_polities"])]),
 ("imerina_chiefdoms","Imerina Highland Chiefdoms","Merina","none","Andriana","alasora","africa_madagascar_indian_ocean",["island_madagascar"],[
  ("imerina_highlands","Imerina Highlands","compressed_chiefdoms",["madagascar_west","madagascar_east"])]),
 ("madagascar_coastal_polities","Madagascar Coastal Polities","Malagasy","none","Mpanjaka","vohemar","africa_madagascar_indian_ocean",["island_madagascar","strait_mozambique_channel"],[
  ("madagascar_east","Eastern and Northern Madagascar","distributed_polities",["imerina_highlands","madagascar_west"]),("madagascar_west","Western and Southern Madagascar","distributed_polities",["imerina_highlands","madagascar_east"])]),
]

# Relationships confidently present at the baseline. Tribute does not erase the
# subject's legal ownership, governance, or sovereignty in the world projection.
VASSALS = {"medri_bahri": "ethiopian_empire"}
TRIBUTARIES = [
 {"id":"mogadishu_ajuran_tribute","subjectPolityId":"mogadishu_sultanate","overlordPolityId":"ajuran_sultanate","kind":"tribute","taxRatePercent":5},
]
ACTIVE_CONFLICTS = []


def title_rank(tier):
    return tier if tier != "none" else "prince"


def main():
    records=[]
    for pid,name,adjective,tier,title,capital,instance,features,provinces in POLITIES:
        records.append({"id":pid,"name":name,"adjective":adjective,"sovereignTier":tier,"nativeSovereignTitle":title,
          "capitalSettlementId":capital,"regionalInstanceId":instance,"geographicFeatureIds":features,
          "provinces":[{"id":p,"name":n,"administrativeType":kind,"regionalInstanceId":instance,
            "geographicFeatureIds":list(features),"adjacentProvinceIds":adj} for p,n,kind,adj in provinces]})
    source={"schemaVersion":1,"id":"africa_political_baseline_1450","campaignStartDate":"1450-01-01",
      "coverageRule":{"kind":"exclusive_authoritative_provinces","exceptions":[]},"polities":records,
      "vassalage":[{"id":p+"_vassalage","subjectPolityId":p,"overlordPolityId":o} for p,o in VASSALS.items()],
      "tributaryRelations":TRIBUTARIES,"personalUnions":[],"activeConflicts":ACTIVE_CONFLICTS}
    SOURCE.parent.mkdir(parents=True,exist_ok=True)
    SOURCE.write_text(json.dumps(source,ensure_ascii=False,indent=2)+"\n")

    world=json.loads(WORLD.read_text())
    # Remove the superseded focused-pass IDs when rebuilding after integration with
    # the comprehensive political baseline. These aliases must not survive beside
    # the authoritative 1450 entities.
    legacy_polity_ids={"hafsid_ifriqiya","songhai","hausa_states","swahili_city_states","mutapa","kongo","benin"}
    legacy_province_ids={"morocco_core","tafilalt","manden","ifriqiya","lower_egypt","upper_egypt","western_sahel","niger_bend","hausaland","ethiopian_highlands","somali_coast","swahili_coast","zanzibar_archipelago","zimbabwe_plateau","sofala_hinterland","benin_kingdom"}
    polity_ids={r[0] for r in POLITIES}; province_ids={p[0] for r in POLITIES for p in r[8]}
    polity_ids |= legacy_polity_ids; province_ids |= legacy_province_ids
    capital_ids={r[5] for r in POLITIES}
    # Idempotently replace only Africa's projection; Europe and reusable fixtures stay intact.
    world["polities"]=[x for x in world["polities"] if x["id"] not in polity_ids]
    world["provinces"]=[x for x in world["provinces"] if x["id"] not in province_ids]
    world["settlements"]=[x for x in world["settlements"] if x["id"] not in capital_ids]
    world["cityCores"]=[x for x in world["cityCores"] if x["id"] not in {"city_core_"+x for x in capital_ids}]
    world["defenseLayouts"]=[x for x in world["defenseLayouts"] if x["id"] not in {"defense_"+x for x in capital_ids}]
    world["titleStyles"]=[x for x in world["titleStyles"] if x.get("polityId") not in polity_ids]
    world["titleGrants"]=[x for x in world["titleGrants"] if x.get("holder",{}).get("id") not in polity_ids]
    world["territorialHoldings"]=[x for x in world["territorialHoldings"] if x.get("territory",{}).get("id") not in province_ids]
    world["allegiances"]=[x for x in world["allegiances"] if x.get("subject",{}).get("id") not in polity_ids]
    by_polity={r[0]:r for r in POLITIES}
    tribute_by_subject={x["subjectPolityId"]:x for x in TRIBUTARIES}
    for polity in records:
        pid=polity["id"]; pids=[p["id"] for p in polity["provinces"]]; capital=polity["capitalSettlementId"]
        world["polities"].append({k:polity[k] for k in ("id","name","adjective","sovereignTier","nativeSovereignTitle","capitalSettlementId")}|{"provinceIds":pids})
        for ix,p in enumerate(polity["provinces"]):
            world["provinces"].append({"id":p["id"],"name":p["name"],"administrativeType":p["administrativeType"],"legalOwnerPolityId":pid,"controllerPolityId":pid,"settlementIds":[capital] if ix==0 else []})
            overlord=VASSALS.get(pid); sovereign=overlord or pid
            tribute=tribute_by_subject.get(pid)
            tax=10 if overlord else (tribute["taxRatePercent"] if tribute else 0)
            holding={"id":"holding_"+p["id"],"territory":{"kind":"province","id":p["id"]},"legalOwner":{"kind":"polity","id":pid},"controllerPolityId":pid,"governingPolityId":pid,"sovereignPolityId":sovereign,"autonomyPercent":70 if overlord or tribute else 35,"overlordTaxRatePercent":tax,"upkeepRatePercent":5,"obligations":[{"kind":"service" if overlord else "tribute","value":1}] if overlord or tribute else []}
            superior=overlord or (tribute["overlordPolityId"] if tribute else None)
            if superior: holding["overlordHoldingId"]="holding_"+by_polity[superior][8][0][0]
            world["territorialHoldings"].append(holding)
        world["settlements"].append({"id":capital,"name":capital.replace("_"," ").title(),"kind":"capital","provinceId":pids[0],"legalOwnerPolityId":pid,"controllerPolityId":pid,"capturable":True,"civilianFacilitiesInvulnerable":True,"cityCoreId":"city_core_"+capital,"defenseLayoutId":"defense_"+capital,"serviceIds":["market","quest_hub"],"regionalInstanceId":polity["regionalInstanceId"]})
        world["cityCores"].append({"id":"city_core_"+capital,"objectTemplateId":"capital_city_core"})
        world["defenseLayouts"].append({"id":"defense_"+capital,"objectTemplateIds":["capital_defenses"]})
        style="title_"+pid; grant="grant_"+pid; overlord=VASSALS.get(pid)
        world["titleStyles"].append({"id":style,"polityId":pid,"rankTier":title_rank(polity["sovereignTier"]),"nativeName":polity["nativeSovereignTitle"],"genericName":title_rank(polity["sovereignTier"]).title()})
        item={"id":grant,"titleStyleId":style,"holder":{"kind":"polity","id":pid},"allegiancePolityId":overlord or pid,"sovereign":not bool(overlord)}
        if overlord: item["grantorTitleId"]="grant_"+overlord
        world["titleGrants"].append(item)
        if overlord: world["allegiances"].append({"id":"allegiance_"+pid,"subject":{"kind":"polity","id":pid},"polityId":overlord})
    WORLD.write_text(json.dumps(world,ensure_ascii=False,indent=2)+"\n")


if __name__ == "__main__": main()

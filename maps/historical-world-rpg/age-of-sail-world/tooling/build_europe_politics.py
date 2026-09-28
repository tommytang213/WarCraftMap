#!/usr/bin/env python3
"""Build the authoritative Europe 1450 political baseline and its world projection."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scenario/politics/europe-1450.json"
WORLD = ROOT / "scenario/world/world.json"

# id, display name, adjective, rank, native title, capital, instance, geographic refs,
# provinces as (id, display name, administrative type, adjacency ids)
POLITIES = [
 ("england","Kingdom of England","English","king","King","london","europe_atlantic_isles",["coast_british_isles","river_thames"],[
  ("greater_london","London","capital_region",["kent","english_midlands"]),("kent","Kent","county",["greater_london","normandy"]),("english_midlands","English Midlands","region",["greater_london","northern_england"]),("northern_england","Northern England","region",["english_midlands","scottish_lowlands"])]),
 ("scotland","Kingdom of Scotland","Scottish","king","King","edinburgh","europe_atlantic_isles",["coast_british_isles"],[("scottish_lowlands","Scottish Lowlands","region",["northern_england","scottish_highlands"]),("scottish_highlands","Scottish Highlands","region",["scottish_lowlands"])]),
 ("ireland","Lordship of Ireland","Irish","duke","Lord","dublin","europe_atlantic_isles",["island_ireland"],[("the_pale","The Pale","lordship",["gaelic_ireland"]),("gaelic_ireland","Gaelic Ireland","compressed_lordships",["the_pale"])]),
 ("norway","Kingdom of Norway","Norwegian","king","Konge","oslo","europe_baltic_scandinavia",["mountains_scandinavian","island_iceland"],[("norway_proper","Norway","kingdom_region",["swedish_gotaland","iceland"]),("iceland","Iceland","dependency",["norway_proper"])]),
 ("denmark","Kingdom of Denmark","Danish","king","Konge","copenhagen","europe_baltic_scandinavia",["coast_jutland","strait_danish_belts"],[("denmark_proper","Denmark","kingdom_region",["schleswig_holstein","swedish_gotaland"]),("schleswig_holstein","Schleswig and Holstein","duchies",["denmark_proper","imperial_free_cities"])]),
 ("sweden","Kingdom of Sweden","Swedish","king","Konung","stockholm","europe_baltic_scandinavia",["mountains_scandinavian"],[("swedish_gotaland","Gotaland and Svealand","kingdom_region",["denmark_proper","norway_proper","swedish_finland"]),("swedish_finland","Finland","realm_region",["swedish_gotaland","livonia"])]),
 ("france","Kingdom of France","French","king","Roi","paris","europe_france_low_countries",["river_seine","coast_channel_low_countries"],[("ile_de_france","Ile-de-France","royal_domain",["normandy","burgundy_duchy","loire_france"]),("normandy","Normandy","province",["ile_de_france","brittany","kent"]),("loire_france","Loire and Languedoc","compressed_provinces",["ile_de_france","provence"])]),
 ("burgundy","Burgundian State","Burgundian","duke","Duc","dijon","europe_france_low_countries",["river_rhine","coast_channel_low_countries"],[("burgundy_duchy","Duchy of Burgundy","duchy",["ile_de_france","burgundian_netherlands"]),("burgundian_netherlands","Burgundian Netherlands","composite_lands",["burgundy_duchy","imperial_free_cities"])]),
 ("brittany","Duchy of Brittany","Breton","duke","Duc","nantes","europe_france_low_countries",["coast_channel_low_countries"],[("brittany","Brittany","duchy",["normandy","loire_france"])]),
 ("provence","County of Provence","Provencal","count","Comte","aix_en_provence","europe_france_low_countries",["mountains_alps"],[("provence","Provence","county",["loire_france","savoy","liguria"])]),
 ("portugal","Kingdom of Portugal","Portuguese","king","Rei","lisbon","europe_iberia_western_med",["coast_atlantic_iberia","river_tagus"],[("portugal","Portugal","kingdom_region",["castile_crown"])]),
 ("castile","Crown of Castile","Castilian","king","Rey","toledo","europe_iberia_western_med",["coast_atlantic_iberia","river_tagus"],[("castile_crown","Castile and Leon","crown_lands",["portugal","navarre","aragon_crown","granada"])]),
 ("aragon","Crown of Aragon","Aragonese","king","Rei","zaragoza","europe_iberia_western_med",["island_balearics","mountains_pyrenees"],[("aragon_crown","Aragon and Catalonia","crown_lands",["castile_crown","navarre","valencia_balearics"]),("valencia_balearics","Valencia and the Balearics","crown_lands",["aragon_crown","liguria"])]),
 ("navarre","Kingdom of Navarre","Navarrese","king","Rey","pamplona","europe_iberia_western_med",["mountains_pyrenees"],[("navarre","Navarre","kingdom",["castile_crown","aragon_crown"])]),
 ("granada","Emirate of Granada","Granadan","king","Emir","granada","europe_iberia_western_med",["coast_atlantic_iberia","strait_gibraltar"],[("granada","Granada","emirate",["castile_crown"])]),
 ("austria","Archduchy of Austria","Austrian","duke","Erzherzog","vienna","europe_central_alpine",["river_danube","mountains_alps"],[("austrian_lands","Austrian Hereditary Lands","archduchy",["bavaria","bohemian_crown","hungary","venetian_mainland"])]),
 ("bohemia","Crown of Bohemia","Bohemian","king","Kral","prague","europe_central_alpine",["river_danube"],[("bohemian_crown","Bohemia and Moravia","crown_lands",["austrian_lands","saxony","poland_crown"])]),
 ("brandenburg","Margraviate of Brandenburg","Brandenburgish","marquess","Markgraf","berlin","europe_central_alpine",["river_rhine"],[("brandenburg","Brandenburg","margraviate",["saxony","imperial_free_cities","poland_crown"])]),
 ("saxony","Electorate of Saxony","Saxon","duke","Kurfurst","wittenberg","europe_central_alpine",["river_rhine"],[("saxony","Saxony","electorate",["brandenburg","bohemian_crown","bavaria"])]),
 ("bavaria","Duchy of Bavaria","Bavarian","duke","Herzog","munich","europe_central_alpine",["river_danube","mountains_alps"],[("bavaria","Bavaria","duchy",["saxony","austrian_lands","swiss_confederacy"])]),
 ("palatinate","Electoral Palatinate","Palatine","prince","Pfalzgraf","heidelberg","europe_central_alpine",["river_rhine"],[("rhine_palatinate","Rhine Palatinate","electorate",["imperial_free_cities","swiss_confederacy"])]),
 ("holy_roman_empire","Holy Roman Empire","Imperial","emperor","Romischer Kaiser","aachen","europe_central_alpine",["river_rhine","river_danube"],[("imperial_free_cities","Imperial Free Cities","compressed_imperial_estates",["schleswig_holstein","burgundian_netherlands","brandenburg","rhine_palatinate","swiss_confederacy"])]),
 ("swiss_confederacy","Old Swiss Confederacy","Swiss","none","Landammann","lucerne","europe_central_alpine",["mountains_alps","river_rhine"],[("swiss_confederacy","Swiss Confederacy","confederacy",["bavaria","rhine_palatinate","savoy","milan"])]),
 ("poland","Kingdom of Poland","Polish","king","Krol","krakow","europe_eastern_black_sea",["mountains_carpathians"],[("poland_crown","Polish Crown Lands","crown_lands",["bohemian_crown","brandenburg","prussia","lithuania_proper","hungary"])]),
 ("lithuania","Grand Duchy of Lithuania","Lithuanian","duke","Didysis Kunigaikstis","vilnius","europe_eastern_black_sea",["river_dnieper"],[("lithuania_proper","Lithuania","grand_duchy",["poland_crown","livonia","novgorod_lands","ruthenia"]),("ruthenia","Ruthenian Lands","grand_ducal_lands",["lithuania_proper","moldavia","golden_horde_steppe"])]),
 ("teutonic_order","State of the Teutonic Order","Teutonic","duke","Hochmeister","marienburg","europe_baltic_scandinavia",["strait_danish_belts"],[("prussia","Prussia","monastic_state",["poland_crown","livonia"])]),
 ("livonian_confederation","Livonian Confederation","Livonian","none","Landmeister","riga","europe_baltic_scandinavia",["strait_danish_belts"],[("livonia","Livonia","confederation",["prussia","swedish_finland","lithuania_proper","novgorod_lands"])]),
 ("hungary","Kingdom of Hungary","Hungarian","king","Kiraly","buda","europe_central_alpine",["river_danube","mountains_carpathians"],[("hungary","Hungary and Croatia","crown_lands",["austrian_lands","poland_crown","moldavia","bosnia","serbia"])]),
 ("wallachia","Principality of Wallachia","Wallachian","prince","Voivode","targoviste","europe_balkans_aegean",["river_danube","mountains_carpathians"],[("wallachia","Wallachia","principality",["moldavia","hungary","ottoman_balkans"])]),
 ("moldavia","Principality of Moldavia","Moldavian","prince","Voivode","suceava","europe_eastern_black_sea",["mountains_carpathians","coast_black_sea"],[("moldavia","Moldavia","principality",["wallachia","hungary","ruthenia","crimea"])]),
 ("bosnia","Kingdom of Bosnia","Bosnian","king","Kralj","jajce","europe_balkans_aegean",["mountains_dinaric","coast_adriatic_balkan"],[("bosnia","Bosnia","kingdom",["hungary","serbia","venetian_mainland"])]),
 ("serbia","Serbian Despotate","Serbian","prince","Despot","smederevo","europe_balkans_aegean",["river_danube","mountains_dinaric"],[("serbia","Serbia","despotate",["bosnia","hungary","ottoman_balkans","albania"])]),
 ("albania","League of Lezhe","Albanian","prince","Princ","lezhe","europe_balkans_aegean",["coast_adriatic_balkan","strait_otranto"],[("albania","Albania","league",["serbia","ottoman_balkans","venetian_mainland"])]),
 ("ottoman_empire","Ottoman Empire","Ottoman","emperor","Sultan","edirne","europe_balkans_aegean",["strait_bosporus_dardanelles","river_danube"],[("ottoman_balkans","Rumelia","beylerbeylik",["wallachia","serbia","albania","byzantine_thrace"])]),
 ("byzantine_empire","Roman Empire","Roman","emperor","Basileus","constantinople","europe_balkans_aegean",["strait_bosporus_dardanelles"],[("byzantine_thrace","Constantinople and Morea","compressed_remnant",["ottoman_balkans"])]),
 ("venice","Republic of Venice","Venetian","duke","Doge","venice","europe_italy_central_med",["coast_adriatic_balkan","strait_otranto","island_crete","island_cyprus"],[("venetian_mainland","Terraferma and Stato da Mar","republican_domains",["austrian_lands","milan","papal_states","bosnia","albania"])]),
 ("milan","Duchy of Milan","Milanese","duke","Duca","milan","europe_italy_central_med",["river_po","mountains_alps"],[("milan","Lombardy","duchy",["venetian_mainland","swiss_confederacy","savoy","tuscany"])]),
 ("florence","Republic of Florence","Florentine","duke","Gonfaloniere","florence","europe_italy_central_med",["mountains_apennines"],[("tuscany","Tuscany","republican_domain",["milan","papal_states","liguria"])]),
 ("papal_states","Papal States","Papal","king","Papa","rome","europe_italy_central_med",["mountains_apennines"],[("papal_states","Papal States","ecclesiastical_states",["tuscany","venetian_mainland","naples_sicily"])]),
 ("naples","Kingdom of Naples","Neapolitan","king","Re","naples","europe_italy_central_med",["coast_italian_peninsula","island_sicily","strait_messina"],[("naples_sicily","Naples and Sicily","kingdom",["papal_states"])]),
 ("genoa","Republic of Genoa","Genoese","duke","Doge","genoa","europe_italy_central_med",["coast_italian_peninsula","island_sardinia_corsica","coast_black_sea"],[("liguria","Liguria and Genoese colonies","republican_domains",["provence","tuscany","savoy","crimea"])]),
 ("savoy","Duchy of Savoy","Savoyard","duke","Duca","chambery","europe_central_alpine",["mountains_alps"],[("savoy","Savoy and Piedmont","duchy",["provence","liguria","milan","swiss_confederacy"])]),
 ("muscovy","Grand Principality of Moscow","Muscovite","prince","Velikiy Knyaz","moscow","europe_eastern_black_sea",["river_volga_upper"],[("muscovy","Muscovy","grand_principality",["tver","ryazan","novgorod_lands","golden_horde_steppe"])]),
 ("novgorod","Novgorod Republic","Novgorodian","prince","Posadnik","novgorod","europe_eastern_black_sea",["river_volga_upper"],[("novgorod_lands","Novgorod Lands","republican_lands",["livonia","lithuania_proper","muscovy","tver"])]),
 ("tver","Grand Principality of Tver","Tverian","prince","Velikiy Knyaz","tver","europe_eastern_black_sea",["river_volga_upper"],[("tver","Tver","grand_principality",["novgorod_lands","muscovy"])]),
 ("ryazan","Grand Principality of Ryazan","Ryazanian","prince","Velikiy Knyaz","ryazan","europe_eastern_black_sea",["river_volga_upper"],[("ryazan","Ryazan","grand_principality",["muscovy","golden_horde_steppe"])]),
 ("golden_horde","Golden Horde","Tatar","king","Khan","saray","europe_eastern_black_sea",["river_volga_upper","coast_black_sea"],[("golden_horde_steppe","Pontic-Caspian Steppe","khanate_lands",["ruthenia","muscovy","ryazan","crimea","kazan"])]),
 ("crimea","Crimean Khanate","Crimean Tatar","king","Khan","solkhat","europe_eastern_black_sea",["coast_black_sea"],[("crimea","Crimea","khanate",["moldavia","liguria","golden_horde_steppe"])]),
 ("kazan","Khanate of Kazan","Kazan Tatar","king","Khan","kazan","europe_eastern_black_sea",["river_volga_upper"],[("kazan","Kazan","khanate",["golden_horde_steppe"])]),
]

VASSALS = {"ireland":"england", "brandenburg":"holy_roman_empire", "saxony":"holy_roman_empire", "bavaria":"holy_roman_empire", "palatinate":"holy_roman_empire", "austria":"holy_roman_empire", "bohemia":"holy_roman_empire"}
PERSONAL_UNIONS = [{"id":"kalmar_union","seniorPolityId":"denmark","juniorPolityIds":["norway","sweden"]},{"id":"polish_lithuanian_union","seniorPolityId":"poland","juniorPolityIds":["lithuania"]}]
CONFLICTS = [{"id":"hundred_years_war","name":"Hundred Years' War","attackerPolityIds":["england"],"defenderPolityIds":["france"],"startDate":"1337-05-24"},{"id":"ottoman_byzantine_war","name":"Ottoman-Byzantine War","attackerPolityIds":["ottoman_empire"],"defenderPolityIds":["byzantine_empire"],"startDate":"1450-01-01"}]

def main():
    records=[]; seen=set()
    for row in POLITIES:
        pid,name,adj,rank,title,capital,instance,features,provinces=row
        if pid in seen: raise ValueError(f"duplicate polity {pid}")
        seen.add(pid)
        records.append({"id":pid,"name":name,"adjective":adj,"sovereignTier":rank,"nativeSovereignTitle":title,"capitalSettlementId":capital,"regionalInstanceId":instance,"geographicFeatureIds":features,"provinces":[{"id":x,"name":n,"administrativeType":t,"regionalInstanceId":instance,"geographicFeatureIds":list(features),"adjacentProvinceIds":a} for x,n,t,a in provinces]})
    source={"schemaVersion":1,"id":"europe_political_baseline_1450","campaignStartDate":"1450-01-01","coverageRule":{"kind":"exclusive_authoritative_provinces","exceptions":[]},"polities":records,"vassalage":[{"id":f"{v}_vassalage","subjectPolityId":v,"overlordPolityId":o} for v,o in VASSALS.items()],"personalUnions":PERSONAL_UNIONS,"activeConflicts":CONFLICTS}
    SOURCE.parent.mkdir(parents=True,exist_ok=True); SOURCE.write_text(json.dumps(source,ensure_ascii=False,indent=2)+"\n")
    world=json.loads(WORLD.read_text())
    # Preserve runtime fixtures unrelated to the baseline, while replacing political/civil data.
    world["polities"]=[]; world["provinces"]=[]; world["settlements"]=[]; world["cityCores"]=[]; world["defenseLayouts"]=[]; world["titleStyles"]=[]; world["titleGrants"]=[]; world["territorialHoldings"]=[]; world["allegiances"]=[]
    for polity in records:
        pid=polity["id"]; rank=polity["sovereignTier"]; title=polity["nativeSovereignTitle"]; province_ids=[p["id"] for p in polity["provinces"]]
        world["polities"].append({k:polity[k] for k in ("id","name","adjective","sovereignTier","nativeSovereignTitle","capitalSettlementId")}|{"provinceIds":province_ids})
        capital_province=province_ids[0]
        for p in polity["provinces"]:
            world["provinces"].append({"id":p["id"],"name":p["name"],"administrativeType":p["administrativeType"],"legalOwnerPolityId":pid,"controllerPolityId":pid,"settlementIds":[polity["capitalSettlementId"]] if p["id"]==capital_province else []})
            overlord=VASSALS.get(pid); sovereign=overlord or pid
            world["territorialHoldings"].append({"id":"holding_"+p["id"],"territory":{"kind":"province","id":p["id"]},"legalOwner":{"kind":"polity","id":pid},"controllerPolityId":pid,"governingPolityId":pid,"sovereignPolityId":sovereign,"autonomyPercent":70 if overlord else 35,"overlordHoldingId":"holding_"+next(x["id"] for r in records if r["id"]==sovereign for x in r["provinces"]) if overlord else None,"overlordTaxRatePercent":10 if overlord else 0,"upkeepRatePercent":5,"obligations":[{"kind":"service","value":1}] if overlord else []})
        for h in world["territorialHoldings"]:
            if h.get("overlordHoldingId") is None: h.pop("overlordHoldingId",None)
        capital=polity["capitalSettlementId"]
        services=["market","quest_hub"]+(["banking","port_services"] if capital=="london" else [])
        settlement={"id":capital,"name":capital.replace("_"," ").title(),"kind":"capital","provinceId":capital_province,"legalOwnerPolityId":pid,"controllerPolityId":pid,"capturable":True,"civilianFacilitiesInvulnerable":True,"cityCoreId":"city_core_"+capital,"defenseLayoutId":"defense_"+capital,"serviceIds":services}
        if capital=="london": settlement["navigationZoneId"]="north_sea_atlantic"
        world["settlements"].append(settlement)
        world["cityCores"].append({"id":"city_core_"+capital,"objectTemplateId":"capital_city_core"}); world["defenseLayouts"].append({"id":"defense_"+capital,"objectTemplateIds":["capital_defenses"]})
        style={"england":"english_king","france":"french_king"}.get(pid,"title_"+pid); grant={"england":"crown_of_england","france":"crown_of_france"}.get(pid,"grant_"+pid)
        world["titleStyles"].append({"id":style,"polityId":pid,"rankTier":rank if rank!="none" else "prince","nativeName":title,"genericName":rank.title() if rank!="none" else "Leader"})
        grantor={"england":"crown_of_england","france":"crown_of_france"}.get(VASSALS.get(pid),"grant_"+VASSALS[pid]) if pid in VASSALS else None
        item={"id":grant,"titleStyleId":style,"holder":{"kind":"polity","id":pid},"allegiancePolityId":VASSALS.get(pid,pid),"sovereign":grantor is None}
        if grantor: item["grantorTitleId"]=grantor
        world["titleGrants"].append(item)
        if pid in VASSALS: world["allegiances"].append({"id":"allegiance_"+pid,"subject":{"kind":"polity","id":pid},"polityId":VASSALS[pid]})
    world["titleStyles"].append({"id":"english_duke","polityId":"england","rankTier":"duke","nativeName":"Duke","genericName":"Duke"})
    for ident,name,province,owner,zone in (("dover","Dover","kent","england","english_channel"),("rouen","Rouen","normandy","france",None)):
        world["settlements"].append({"id":ident,"name":name,"kind":"port" if ident=="dover" else "major_city","provinceId":province,"legalOwnerPolityId":owner,"controllerPolityId":owner,"capturable":True,"civilianFacilitiesInvulnerable":True,"cityCoreId":"city_core_"+ident,"defenseLayoutId":"defense_"+ident,"serviceIds":["market","port_services"]}|({"navigationZoneId":zone} if zone else {}))
        next(x for x in world["provinces"] if x["id"]==province)["settlementIds"].append(ident)
        world["cityCores"].append({"id":"city_core_"+ident,"objectTemplateId":"city_core"}); world["defenseLayouts"].append({"id":"defense_"+ident,"objectTemplateIds":["city_defenses"]})
    # Research/adoption samples may only refer to the replaced catalog.
    world["polityResearchStates"]=[x for x in world.get("polityResearchStates",[]) if x.get("polityId") in seen]
    province_set={p["id"] for r in records for p in r["provinces"]}
    world["provinceAdoptionStates"]=[x for x in world.get("provinceAdoptionStates",[]) if x.get("provinceId") in province_set]
    WORLD.write_text(json.dumps(world,ensure_ascii=False,indent=2)+"\n")

if __name__=="__main__": main()

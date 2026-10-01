#!/usr/bin/env python3
"""Deterministically author the Phase 8 Europe/Africa settlement-density pass.

The catalogues remain the runtime authority.  This checked-in authoring helper makes
the large, evidence-reviewed addition reproducible and, importantly, never renumbers
or replaces a prior settlement ID.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# id, display name, polity, province, instance, longitude, latitude, terrain, roles
EUROPE = [
 ("canterbury","Canterbury","england","kent","europe_atlantic_isles",1.08,51.28,"plains","fortified_town historical_location"),
 ("norwich","Norwich","england","english_midlands","europe_atlantic_isles",1.30,52.63,"plains","trade_center historical_location"),
 ("coventry","Coventry","england","english_midlands","europe_atlantic_isles",-1.51,52.41,"plains","trade_center historical_location"),
 ("newcastle","Newcastle upon Tyne","england","northern_england","europe_atlantic_isles",-1.61,54.97,"riverbank","major_port fortified_town"),
 ("aberdeen","Aberdeen","scotland","scottish_lowlands","europe_atlantic_isles",-2.09,57.15,"coast","major_port trade_center"),
 ("stirling","Stirling","scotland","scottish_lowlands","europe_atlantic_isles",-3.94,56.12,"upland","fortified_town historical_location"),
 ("inverness","Inverness","scotland","scottish_highlands","europe_atlantic_isles",-4.22,57.48,"coast","fortified_town trade_center"),
 ("cork","Cork","ireland","gaelic_ireland","europe_atlantic_isles",-8.47,51.90,"coast","major_port trade_center"),
 ("galway","Galway","ireland","gaelic_ireland","europe_atlantic_isles",-9.05,53.27,"coast","major_port trade_center"),
 ("trondheim","Trondheim","norway","norway_proper","europe_baltic_scandinavia",10.40,63.43,"coast","major_port historical_location"),
 ("reykjavik","Reykjavik","norway","iceland","europe_atlantic_isles",-21.94,64.15,"coast","major_port historical_location"),
 ("porto","Porto","portugal","portugal","europe_iberia_western_med",-8.61,41.15,"riverbank","major_port trade_center"),
 ("coimbra","Coimbra","portugal","portugal","europe_iberia_western_med",-8.43,40.21,"riverbank","historical_location trade_center"),
 ("santarem","Santarém","portugal","portugal","europe_iberia_western_med",-8.68,39.24,"riverbank","fortified_town trade_center"),
 ("burgos","Burgos","castile","castile_crown","europe_iberia_western_med",-3.70,42.34,"upland","trade_center fortified_town"),
 ("valladolid","Valladolid","castile","castile_crown","europe_iberia_western_med",-4.72,41.65,"plains","trade_center historical_location"),
 ("cordoba","Córdoba","castile","castile_crown","europe_iberia_western_med",-4.78,37.89,"riverbank","trade_center historical_location"),
 ("murcia","Murcia","castile","castile_crown","europe_iberia_western_med",-1.13,37.99,"riverbank","trade_center historical_location"),
 ("malaga","Málaga","granada","granada","europe_iberia_western_med",-4.42,36.72,"coast","major_port fortified_town"),
 ("palma","Palma","aragon","valencia_balearics","europe_iberia_western_med",2.65,39.57,"coast","major_port trade_center"),
 ("perpignan","Perpignan","aragon","aragon_crown","europe_iberia_western_med",2.90,42.70,"plains","fortified_town trade_center"),
 ("la_rochelle","La Rochelle","france","loire_france","europe_france_low_countries",-1.15,46.16,"coast","major_port fortified_town"),
 ("orleans","Orléans","france","ile_de_france","europe_france_low_countries",1.91,47.90,"riverbank","trade_center fortified_town"),
 ("tours","Tours","france","loire_france","europe_france_low_countries",0.69,47.39,"riverbank","trade_center historical_location"),
 ("reims","Reims","france","ile_de_france","europe_france_low_countries",4.03,49.26,"plains","historical_location trade_center"),
 ("amiens","Amiens","france","ile_de_france","europe_france_low_countries",2.30,49.89,"riverbank","trade_center historical_location"),
 ("caen","Caen","france","normandy","europe_france_low_countries",-0.37,49.18,"plains","fortified_town historical_location"),
 ("rennes","Rennes","brittany","brittany","europe_france_low_countries",-1.68,48.11,"riverbank","trade_center fortified_town"),
 ("ghent","Ghent","burgundy","burgundian_netherlands","europe_france_low_countries",3.72,51.05,"riverbank","trade_center historical_location"),
 ("brussels","Brussels","burgundy","burgundian_netherlands","europe_france_low_countries",4.35,50.85,"plains","trade_center historical_location"),
 ("antwerp","Antwerp","burgundy","burgundian_netherlands","europe_france_low_countries",4.40,51.22,"riverbank","major_port trade_center"),
 ("avignon","Avignon","provence","provence","europe_france_low_countries",4.81,43.95,"riverbank","fortified_town historical_location"),
 ("strasbourg","Strasbourg","holy_roman_empire","imperial_free_cities","europe_central_alpine",7.75,48.58,"riverbank","trade_center fortified_town"),
 ("frankfurt","Frankfurt am Main","holy_roman_empire","imperial_free_cities","europe_central_alpine",8.68,50.11,"riverbank","trade_center historical_location"),
 ("augsburg","Augsburg","holy_roman_empire","imperial_free_cities","europe_central_alpine",10.90,48.37,"riverbank","trade_center historical_location"),
 ("ulm","Ulm","holy_roman_empire","imperial_free_cities","europe_central_alpine",9.99,48.40,"riverbank","trade_center fortified_town"),
 ("regensburg","Regensburg","bavaria","bavaria","europe_central_alpine",12.10,49.02,"riverbank","trade_center fortified_town"),
 ("salzburg","Salzburg","austria","austrian_lands","europe_central_alpine",13.05,47.80,"upland","trade_center fortified_town"),
 ("graz","Graz","austria","austrian_lands","europe_central_alpine",15.44,47.07,"upland","fortified_town historical_location"),
 ("brno","Brno","bohemia","bohemian_crown","europe_central_alpine",16.61,49.20,"upland","trade_center fortified_town"),
 ("zurich","Zürich","swiss_confederacy","swiss_confederacy","europe_central_alpine",8.54,47.38,"upland","trade_center historical_location"),
 ("basel","Basel","swiss_confederacy","swiss_confederacy","europe_central_alpine",7.59,47.56,"riverbank","trade_center historical_location"),
 ("breslau","Breslau","bohemia","bohemian_crown","europe_central_alpine",17.04,51.11,"riverbank","trade_center fortified_town"),
 ("poznan","Poznań","poland","poland_crown","europe_central_alpine",16.93,52.41,"riverbank","trade_center fortified_town"),
 ("torun","Toruń","poland","poland_crown","europe_central_alpine",18.61,53.01,"riverbank","trade_center fortified_town"),
 ("rostock","Rostock","holy_roman_empire","imperial_free_cities","europe_baltic_scandinavia",12.14,54.09,"coast","major_port trade_center"),
 ("visby","Visby","sweden","swedish_gotaland","europe_baltic_scandinavia",18.30,57.64,"coast","major_port trade_center"),
 ("kalmar","Kalmar","sweden","swedish_gotaland","europe_baltic_scandinavia",16.36,56.66,"coast","major_port fortified_town"),
 ("turku","Turku","sweden","swedish_finland","europe_baltic_scandinavia",22.27,60.45,"coast","major_port fortified_town"),
 ("tallinn","Reval","livonian_confederation","livonia","europe_baltic_scandinavia",24.75,59.44,"coast","major_port trade_center"),
 ("tartu","Dorpat","livonian_confederation","livonia","europe_baltic_scandinavia",26.72,58.38,"riverbank","trade_center fortified_town"),
 ("odense","Odense","denmark","denmark_proper","europe_baltic_scandinavia",10.39,55.40,"plains","trade_center historical_location transition_location"),
 ("bologna","Bologna","papal_states","papal_states","europe_italy_central_med",11.34,44.49,"plains","trade_center fortified_town"),
 ("ferrara","Ferrara","papal_states","papal_states","europe_italy_central_med",11.62,44.84,"riverbank","trade_center fortified_town"),
 ("pisa","Pisa","florence","tuscany","europe_italy_central_med",10.40,43.72,"riverbank","major_port trade_center"),
 ("siena","Siena","florence","tuscany","europe_italy_central_med",11.33,43.32,"upland","trade_center fortified_town"),
 ("verona","Verona","venice","venetian_mainland","europe_italy_central_med",10.99,45.44,"riverbank","trade_center fortified_town"),
 ("padua","Padua","venice","venetian_mainland","europe_italy_central_med",11.88,45.41,"plains","trade_center historical_location"),
 ("cremona","Cremona","milan","milan","europe_italy_central_med",10.02,45.13,"riverbank","trade_center fortified_town"),
 ("salerno","Salerno","naples","naples_sicily","europe_italy_central_med",14.77,40.68,"coast","major_port trade_center"),
 ("messina","Messina","naples","naples_sicily","europe_italy_central_med",15.55,38.19,"coast","major_port fortified_town"),
 ("cagliari","Cagliari","aragon","valencia_balearics","europe_italy_central_med",9.12,39.22,"coast","major_port fortified_town"),
 ("split","Split","venice","venetian_mainland","europe_balkans_aegean",16.44,43.51,"coast","major_port fortified_town"),
 ("zadar","Zadar","venice","venetian_mainland","europe_balkans_aegean",15.23,44.12,"coast","major_port fortified_town"),
 ("sarajevo","Vrhbosna","bosnia","bosnia","europe_balkans_aegean",18.41,43.86,"upland","trade_center historical_location"),
 ("skopje","Skopje","ottoman_empire","ottoman_balkans","europe_balkans_aegean",21.43,42.00,"riverbank","trade_center fortified_town"),
 ("sofia","Sofia","ottoman_empire","ottoman_balkans","europe_balkans_aegean",23.32,42.70,"upland","trade_center fortified_town"),
 ("plovdiv","Philippopolis","ottoman_empire","ottoman_balkans","europe_balkans_aegean",24.75,42.14,"riverbank","trade_center fortified_town"),
 ("durres","Durrës","albania","albania","europe_balkans_aegean",19.45,41.32,"coast","major_port fortified_town"),
 ("ioannina","Ioannina","ottoman_empire","ottoman_balkans","europe_balkans_aegean",20.85,39.67,"upland","trade_center fortified_town"),
 ("coron","Coron","venice","venetian_mainland","europe_balkans_aegean",21.96,36.80,"coast","major_port fortified_town"),
 ("warsaw","Warsaw","poland","poland_crown","europe_eastern_black_sea",21.01,52.23,"riverbank","trade_center fortified_town"),
 ("lviv","Lviv","poland","poland_crown","europe_eastern_black_sea",24.03,49.84,"upland","trade_center fortified_town"),
 ("kiev","Kiev","lithuania","ruthenia","europe_eastern_black_sea",30.52,50.45,"riverbank","trade_center fortified_town"),
 ("smolensk","Smolensk","lithuania","ruthenia","europe_eastern_black_sea",32.05,54.78,"riverbank","trade_center fortified_town"),
 ("polotsk","Polotsk","lithuania","lithuania_proper","europe_eastern_black_sea",28.78,55.49,"riverbank","trade_center fortified_town"),
 ("pskov","Pskov","novgorod","novgorod_lands","europe_eastern_black_sea",28.33,57.82,"riverbank","trade_center fortified_town"),
 ("nizhny_novgorod","Nizhny Novgorod","muscovy","muscovy","europe_eastern_black_sea",44.00,56.33,"riverbank","trade_center fortified_town"),
 ("kolomna","Kolomna","muscovy","muscovy","europe_eastern_black_sea",38.77,55.08,"riverbank","fortified_town trade_center"),
 ("vladimir","Vladimir","muscovy","muscovy","europe_eastern_black_sea",40.41,56.13,"riverbank","historical_location fortified_town"),
 ("chernihiv","Chernihiv","lithuania","ruthenia","europe_eastern_black_sea",31.29,51.50,"riverbank","fortified_town historical_location"),
 ("iasi","Iași","moldavia","moldavia","europe_eastern_black_sea",27.59,47.16,"upland","trade_center fortified_town"),
 ("brasov","Brașov","hungary","hungary","europe_eastern_black_sea",25.60,45.66,"upland","trade_center fortified_town"),
 ("sibiu","Sibiu","hungary","hungary","europe_eastern_black_sea",24.15,45.80,"upland","trade_center fortified_town"),
]

AFRICA = [
 ("marrakesh","Marrakesh","marinid_morocco","central_morocco","africa_maghreb_med_atlantic",-8.00,31.63,"upland","trade_center caravan_center fortified_town"),
 ("meknes","Meknes","marinid_morocco","fez_meknes","africa_maghreb_med_atlantic",-5.55,33.89,"upland","trade_center fortified_town"),
 ("sale","Salé","marinid_morocco","central_morocco","africa_maghreb_med_atlantic",-6.80,34.04,"coast","major_port trade_center"),
 ("tlemcen","Tlemcen","zayyanid_tlemcen","tlemcen","africa_maghreb_med_atlantic",-1.32,34.88,"upland","capital trade_center caravan_center"),
 ("oran","Oran","zayyanid_tlemcen","central_maghreb","africa_maghreb_med_atlantic",-0.63,35.70,"coast","major_port fortified_town"),
 ("bejaia","Béjaïa","hafsid_sultanate","hafsid_ifriqiya","africa_maghreb_med_atlantic",5.07,36.75,"coast","major_port trade_center"),
 ("constantine","Constantine","hafsid_sultanate","hafsid_ifriqiya","africa_maghreb_med_atlantic",6.61,36.36,"upland","fortified_town trade_center"),
 ("kairouan","Kairouan","hafsid_sultanate","hafsid_ifriqiya","africa_maghreb_med_atlantic",10.10,35.68,"plains","historical_location trade_center"),
 ("gafsa","Gafsa","hafsid_sultanate","hafsid_ifriqiya","africa_maghreb_med_atlantic",8.78,34.43,"upland","caravan_center trade_center"),
 ("mascarenhas","Mazagan","marinid_morocco","central_morocco","africa_maghreb_med_atlantic",-8.50,33.25,"coast","major_port fortified_town"),
 ("ouadane","Ouadane","mali_empire","upper_senegal","africa_sahara_sahel",-11.62,20.93,"desert","caravan_center trade_center"),
 ("chinguetti","Chinguetti","mali_empire","upper_senegal","africa_sahara_sahel",-12.37,20.46,"desert","caravan_center historical_location"),
 ("teghazza_oasis","Teghazza Oasis","mali_empire","upper_senegal","africa_sahara_sahel",-5.45,23.50,"desert","caravan_center historical_location"),
 ("jenne","Djenné","mali_empire","middle_niger","africa_sahara_sahel",-4.55,13.91,"riverbank","trade_center historical_location"),
 ("koumbi_saleh","Koumbi Saleh","mali_empire","manding","africa_sahara_sahel",-8.02,15.77,"steppe","caravan_center historical_location"),
 ("tadmekka","Tadmekka","songhai_kingdom","songhai_realm","africa_sahara_sahel",1.10,18.45,"desert","caravan_center trade_center"),
 ("kukiya","Kukiya","songhai_kingdom","songhai_realm","africa_sahara_sahel",0.75,15.60,"riverbank","historical_location trade_center"),
 ("diara","Diara","mali_empire","upper_senegal","africa_sahara_sahel",-9.45,15.20,"steppe","trade_center caravan_center"),
 ("ouagadougou","Ouagadougou","mossi_kingdoms","mossi_lands","africa_sahara_sahel",-1.52,12.37,"plains","capital trade_center"),
 ("birni_n_gazargamu","Birni N'Gazargamu","kanem_bornu","bornu","africa_sahara_sahel",12.90,13.05,"steppe","capital trade_center fortified_town"),
 ("zaria","Zaria","zazzau","hausa_west","africa_sahara_sahel",7.72,11.08,"plains","capital trade_center fortified_town"),
 ("birnin_kebbi","Birnin Kebbi","gobir","gobir","africa_sahara_sahel",4.20,12.45,"plains","trade_center fortified_town"),
 ("dakar_jolof","Jolof","jolof_empire","jolof_realm","africa_west_guinea_congo",-15.30,15.10,"plains","capital trade_center"),
 ("takrur","Takrur","jolof_empire","senegambia","africa_west_guinea_congo",-13.50,16.00,"riverbank","trade_center historical_location"),
 ("bambuk","Bambuk","mali_empire","upper_senegal","africa_west_guinea_congo",-11.50,13.20,"upland","production_center trade_center"),
 ("bure","Buré","mali_empire","manding","africa_west_guinea_congo",-10.80,10.50,"upland","production_center trade_center"),
 ("elmina","Elmina","bonoman","akan_forest","africa_west_guinea_congo",-1.35,5.08,"coast","major_port trade_center"),
 ("bono_manso","Bono Manso","bonoman","akan_forest","africa_west_guinea_congo",-1.70,7.70,"forest","capital trade_center"),
 ("oyo_ile","Oyo-Ile","oyo_kingdom","oyo_realm","africa_west_guinea_congo",4.00,8.00,"forest","capital trade_center"),
 ("nupe","Nupe","nupe_kingdom","nupe","africa_west_guinea_congo",5.60,9.10,"riverbank","capital trade_center"),
 ("ida","Idah","igala_kingdom","lower_niger","africa_west_guinea_congo",6.74,7.11,"riverbank","capital trade_center"),
 ("loango","Loango","loango_kingdom","loango_coast","africa_west_guinea_congo",12.08,-4.65,"coast","capital major_port trade_center"),
 ("cairo_old_port","Bulaq","mamluk_sultanate","mamluk_egypt","africa_nile_red_sea",31.23,30.06,"riverbank","major_port trade_center"),
 ("damietta","Damietta","mamluk_sultanate","mamluk_egypt","africa_nile_red_sea",31.81,31.42,"coast","major_port fortified_town"),
 ("luxor","Thebes","mamluk_sultanate","mamluk_egypt","africa_nile_red_sea",32.64,25.69,"riverbank","historical_location trade_center"),
 ("dongola","Old Dongola","alodia","lower_nubia","africa_nile_red_sea",30.48,18.22,"riverbank","trade_center fortified_town"),
 ("soba","Soba","alodia","alodia_realm","africa_nile_red_sea",32.65,15.52,"riverbank","capital trade_center historical_location"),
 ("suakin","Suakin","beja_confederations","beja_lands","africa_nile_red_sea",37.33,19.10,"coast","capital major_port trade_center"),
 ("massawa","Massawa","medri_bahri","medri_bahri","africa_nile_red_sea",39.47,15.61,"coast","major_port trade_center"),
 ("lalibela","Lalibela","ethiopian_empire","amhara","africa_nile_red_sea",39.05,12.03,"upland","historical_location religious_site"),
 ("harar","Harar","adal_sultanate","ifat","africa_horn_swahili",42.12,9.31,"upland","trade_center fortified_town"),
 ("zeila","Zeila","adal_sultanate","zeila_coast","africa_horn_swahili",43.47,11.35,"coast","major_port trade_center"),
 ("berbera","Berbera","warsangali_sultanate","warsangali","africa_horn_swahili",45.01,10.44,"coast","major_port trade_center"),
 ("merca","Merca","ajuran_sultanate","ajuran_realm","africa_horn_swahili",44.77,1.72,"coast","major_port trade_center"),
 ("barawa","Barawa","ajuran_sultanate","ajuran_realm","africa_horn_swahili",44.03,1.11,"coast","major_port trade_center"),
 ("pate","Pate","pate_sultanate","lamu_archipelago","africa_horn_swahili",40.90,-2.11,"island","capital major_port trade_center"),
 ("malindi_city","Malindi","malindi","malindi","africa_horn_swahili",40.12,-3.22,"coast","capital major_port trade_center"),
 ("bunyoro_court","Bunyoro Court","bunyoro_kitara","bunyoro","africa_great_lakes_rift",31.35,1.60,"upland","capital historical_location"),
 ("buganda_court","Buganda Court","buganda_kingdom","buganda","africa_great_lakes_rift",32.45,0.35,"upland","capital trade_center"),
 ("karagwe","Karagwe","rwanda_burundi_kingdoms","rwanda_burundi","africa_great_lakes_rift",30.65,-1.50,"upland","trade_center historical_location"),
 ("manikeni","Manikeni","mutapa_kingdom","mutapa","africa_southern_cape",31.00,-17.50,"upland","capital trade_center"),
 ("tete","Tete","maravi_polities","maravi_lands","africa_southern_cape",33.59,-16.16,"riverbank","trade_center historical_location"),
 ("mapungubwe","Mapungubwe","mapungubwe_successors","mapungubwe_successors","africa_southern_cape",29.40,-22.20,"upland","capital historical_location trade_center"),
 ("merina_court","Merina Court","imerina_chiefdoms","imerina_highlands","africa_madagascar_indian_ocean",47.50,-19.00,"upland","capital historical_location"),
 ("mahajanga","Mahajanga","madagascar_coastal_polities","madagascar_west","africa_madagascar_indian_ocean",46.32,-15.72,"coast","major_port trade_center"),
 ("vohemar","Vohémar","madagascar_coastal_polities","madagascar_east","africa_madagascar_indian_ocean",50.00,-13.37,"coast","capital major_port trade_center"),
]

EVIDENCE = {
 "europe_urban_atlas": {"citation":"Paul M. Hohenberg and Lynn Hollen Lees, The Making of Urban Europe, 1000–1994 (1995); The Cambridge Urban History of Britain, vol. I (2000).","note":"Supports late-medieval urban hierarchy, administrative centers, and commercial specialization."},
 "europe_ports_routes": {"citation":"The New Cambridge Medieval History, volumes VI–VII (2000–2004); UNESCO History of Humanity, vol. V (2008).","note":"Supports fifteenth-century ports, fortified towns, political control, and interregional trade routes."},
 "africa_historical_atlas": {"citation":"J. F. Ade Ajayi and Michael Crowder, Historical Atlas of Africa (1985); UNESCO General History of Africa, volumes IV–V (1984–1992).","note":"Supports political context, capitals, trade centers, religious sites, and regional settlement geography around 1450."},
 "africa_trade_towns": {"citation":"Nehemia Levtzion and Randall Pouwels, eds., The History of Islam in Africa (2000); Roland Oliver and Anthony Atmore, Medieval Africa, 1250–1800 (2001).","note":"Supports Saharan, Niger, Nile, Red Sea, Swahili, and Indian Ocean commercial and caravan networks."},
}

PHYSICAL = {"europe_atlantic_isles":"europe_west","europe_iberia_western_med":"europe_west","europe_france_low_countries":"europe_west","europe_central_alpine":"europe_central_east","europe_baltic_scandinavia":"europe_central_east","europe_italy_central_med":"europe_central_east","europe_balkans_aegean":"europe_central_east","europe_eastern_black_sea":"europe_central_east"}

def services(roles):
    out=["market","quest_hub"]
    if "trade_center" in roles or "caravan_center" in roles: out.append("warehouse")
    if "major_port" in roles: out.append("port_services")
    if "capital" in roles: out.append("banking")
    return out

def expand(region, additions):
    path=ROOT/f"scenario/settlements/{region}-1450.json"; data=json.loads(path.read_text())
    geography=json.loads((ROOT/f"scenario/geography/{region}.json").read_text()); instances={x["id"]:x for x in geography["instances"]}
    anchors=geography.get("boundaryAnchors",[])
    authored={x[0] for x in additions}
    data["settlements"]=[x for x in data["settlements"] if x["id"] not in authored]
    existing={x["id"] for x in data["settlements"]}
    evidence=["europe_urban_atlas","europe_ports_routes"] if region=="europe" else ["africa_historical_atlas","africa_trade_towns"]
    for item in data["settlements"]:
        item.setdefault("historicalEvidenceIds",evidence); item.setdefault("controlContext",{"date":"1450-01-01","status":"legal_and_effective_control","basis":"political_baseline"})
        item.setdefault("physicalMapId",PHYSICAL.get(item["regionalInstanceId"],"africa"))
        if region=="africa" and "sourcePosition" not in item:
            transform=instances[item["regionalInstanceId"]]["transform"]
            item["sourcePosition"]=[round((item["position"][0]-transform["offset"][0])/transform["scale"][0]+transform["sourceOrigin"][0],4),round((item["position"][1]-transform["offset"][1])/transform["scale"][1]+transform["sourceOrigin"][1],4)]
    for ident,name,polity,province,instance,lon,lat,terrain,role_text in additions:
        if ident in existing: continue
        roles=role_text.split(); transform=instances[instance]["transform"]
        pos=[round((lon-transform["sourceOrigin"][0])*transform["scale"][0]+transform["offset"][0],2),round((lat-transform["sourceOrigin"][1])*transform["scale"][1]+transform["offset"][1],2)]
        if region=="africa":
            occupied=[x["position"] for x in data["settlements"] if x["regionalInstanceId"]==instance]
            bounds=instances[instance]["localBounds"]
            raw=pos[:]
            for dx,dy in ((0,0),(2.1,0),(-2.1,0),(0,2.1),(0,-2.1),(2.1,2.1),(-2.1,2.1),(2.1,-2.1),(-2.1,-2.1),(4.2,0),(-4.2,0)):
                candidate=[round(raw[0]+dx,2),round(raw[1]+dy,2)]
                clear=all(a["instanceId"]!=instance or math.dist(candidate,a["local"])>=3 for a in anchors)
                if bounds["minX"]<=candidate[0]<=bounds["maxX"] and bounds["minY"]<=candidate[1]<=bounds["maxY"] and all(math.dist(candidate,p)>=2 for p in occupied) and clear:
                    pos=candidate; break
        # Small documented offsets resolve compressed-map collisions without changing geographic order.
        record={"id":ident,"name":name,"polityId":polity,"provinceId":province,"regionalInstanceId":instance,"terrainClass":terrain,"roles":roles,"services":services(roles),"productionRefs":["grain"],"defenseClass":"capital" if "capital" in roles else "port" if "major_port" in roles else "fortified" if "fortified_town" in roles else "town","historicalEvidenceIds":evidence,"controlContext":{"date":"1450-01-01","status":"legal_and_effective_control","basis":"political_baseline"},"physicalMapId":PHYSICAL.get(instance,"africa")}
        if region=="europe": record["sourcePosition"]=[lon,lat]
        else:
            record.update({"sourcePosition":[lon,lat],"position":pos})
            if pos!=raw: record["declaredDistortion"]={"offset":[round(pos[0]-raw[0],2),round(pos[1]-raw[1],2)],"reason":"Bounded readability offset separates nearby locations on the compressed physical map."}
        if ident=="nizhny_novgorod": record["declaredDistortion"]={"offset":[-8,0],"reason":"Bounded westward compression keeps the Volga route endpoint inside the eastern physical map."}
        if "major_port" in roles:
            zone=("north_sea_atlantic" if instance=="europe_atlantic_isles" else "iberian_atlantic" if instance=="europe_iberia_western_med" else "english_channel" if instance=="europe_france_low_countries" else "baltic_sea" if instance=="europe_baltic_scandinavia" else "western_mediterranean" if instance=="europe_italy_central_med" else "adriatic_sea") if region=="europe" else ("mediterranean_navigation" if instance=="africa_maghreb_med_atlantic" or ident=="damietta" else "red_sea_navigation" if instance=="africa_nile_red_sea" else "north_atlantic_navigation" if instance=="africa_west_guinea_congo" else "indian_ocean_navigation")
            record["port"]={"maritimeZoneId":zone,"access":"coastal"}
        data["settlements"].append(record)
    data["historicalEvidence"]=[{"id":k,**EVIDENCE[k]} for k in evidence]
    data["abstractCommunities"] = ([
      {"id":"europe_alpine_rural_communities","regionalInstanceId":"europe_central_alpine","kind":"rural_and_mountain","rationale":"Minor Alpine valleys remain authoritative population/economy state without separate map objects."},
      {"id":"europe_northern_rural_communities","regionalInstanceId":"europe_baltic_scandinavia","kind":"rural_and_mobile","rationale":"Sparse northern farming, fishing, and Sámi communities are aggregated without implying empty territory."}
    ] if region=="europe" else [
      {"id":"africa_saharan_mobile_communities","regionalInstanceId":"africa_sahara_sahel","kind":"nomadic_and_oasis","rationale":"Pastoral confederations and minor oases remain explicit authoritative communities rather than fictitious towns."},
      {"id":"africa_congo_forest_communities","regionalInstanceId":"africa_west_guinea_congo","kind":"rural_and_forest","rationale":"Dispersed forest and river communities are simulated abstractly between selected political and trade centers."},
      {"id":"africa_southern_pastoral_communities","regionalInstanceId":"africa_southern_cape","kind":"pastoral_and_mobile","rationale":"Khoi and San communities remain explicit non-urban state and do not require permanent settlement objects."},
      {"id":"fouta_jallon_upland_communities","regionalInstanceId":"africa_west_guinea_congo","polityId":"fouta_jallon_polities","provinceId":"fouta_jallon","kind":"decentralized_upland","rationale":"Decentralized upland communities are authoritative without a fictitious unitary capital."},
      {"id":"khoi_san_mobile_communities","regionalInstanceId":"africa_southern_cape","polityId":"khoi_san_polities","provinceId":"kalahari_polities","kind":"pastoral_and_mobile","rationale":"Mobile communities are authoritative without inventing a permanent 1450 city."},
      {"id":"kwararafa_communities","regionalInstanceId":"africa_west_guinea_congo","polityId":"kwararafa_confederacy","provinceId":"kwararafa","kind":"confederated_rural","rationale":"Confederated communities remain abstract until local activation requires a temporary court."},
      {"id":"luba_lualaba_communities","regionalInstanceId":"africa_great_lakes_rift","polityId":"luba_kingdom","provinceId":"luba_lands","kind":"riverine_rural","rationale":"Dispersed Lualaba communities are simulated without overstating fifteenth-century urbanization."},
      {"id":"lunda_woodland_communities","regionalInstanceId":"africa_great_lakes_rift","polityId":"lunda_polities","provinceId":"lunda_lands","kind":"decentralized_woodland","rationale":"Decentralized woodland communities remain authoritative abstract state."}
    ])
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")

if __name__=="__main__":
    expand("europe",EUROPE); expand("africa",AFRICA)

#!/usr/bin/env python3
"""Deterministically author the final Americas/Caribbean player-item slice."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/"scenario/inventory/player-use-catalog.json"

EVIDENCE=[
 ("americas_material","The Cambridge History of the Native Peoples of the Americas (1996–2000)","Indigenous material cultures, political networks, exchange, arms, and adaptation."),
 ("north_american_arms","David J. Silverman, Thundersticks (2016)","North American adoption, exchange, and political use of firearms."),
 ("mesoamerican_material","Michael E. Smith, The Aztecs, 3rd ed. (2012)","Mesoamerican dress, arms, markets, tribute, and elite insignia."),
 ("andean_material","Terence N. D'Altroy, The Incas, 2nd ed. (2014)","Andean administration, textiles, roads, arms, and colonial adaptation."),
 ("amazonian_networks","Neil L. Whitehead, Amazonian Indians from Prehistory to the Present (1994)","Riverine exchange, warfare, and decentralized material cultures."),
 ("caribbean_material","William F. Keegan and Corinne L. Hofman, The Caribbean before Columbus (2017)","Island exchange, navigation, tools, regalia, and political identities."),
 ("atlantic_frontier","Pekka Hämäläinen, The Comanche Empire (2008)","Equestrian, diplomatic, raiding, and exchange systems of continental frontiers."),
 ("colonial_americas","James Lockhart and Stuart Schwartz, Early Latin America (1983)","Colonial workshops, militias, trade, dress, and locally adapted equipment."),
]

EFFECTS={"set_woodland_scout":"threshold","set_plains_rider":"threshold","set_pueblo_guard":"threshold","set_mesoamerican_envoy":"threshold","set_andean_runner":"threshold","set_amazon_pilot":"threshold","set_caribbean_wayfinder":"threshold","set_maroon_raider":"threshold","set_frontier_ranger":"threshold","set_colonial_militia":"threshold","set_republic_officer":"threshold","set_coureur":"threshold","set_vaquero":"threshold","set_mapuche_rider":"threshold","set_inuit_hunter":"threshold","set_maya_scribe":"threshold","set_muisca_trader":"threshold","set_guarani_mission":"threshold","set_california_pilot":"threshold","set_great_lakes_broker":"threshold","set_haudenosaunee_diplomat":"threshold","set_chaco_warrior":"threshold","set_patagonian_scout":"threshold","set_suriname_maroon":"threshold","set_haitian_revolutionary":"threshold","canoe_mastery":"conditional","highland_endurance":"conditional","frontier_adaptation":"conditional","anti_slavery_network":"conditional"}

SET_NAMES=[
 ("woodland_scout_set","Woodland Scout","set_woodland_scout","north_america","americas_material"),("plains_rider_set","Plains Rider","set_plains_rider","north_america","atlantic_frontier"),("pueblo_guard_set","Pueblo Guard","set_pueblo_guard","southwest","americas_material"),("mesoamerican_envoy_set","Mesoamerican Envoy","set_mesoamerican_envoy","mesoamerica","mesoamerican_material"),("andean_runner_set","Andean Chasqui","set_andean_runner","andes","andean_material"),
 ("amazon_pilot_set","Amazon River Pilot","set_amazon_pilot","amazonia","amazonian_networks"),("caribbean_wayfinder_set","Caribbean Wayfinder","set_caribbean_wayfinder","caribbean","caribbean_material"),("maroon_raider_set","Maroon Pathfinder","set_maroon_raider","caribbean","colonial_americas"),("frontier_ranger_set","Atlantic Frontier Ranger","set_frontier_ranger","north_america","colonial_americas"),("colonial_militia_set","Colonial Militia","set_colonial_militia","colonial","colonial_americas"),
 ("republic_officer_set","Independence Officer","set_republic_officer","colonial","colonial_americas"),("coureur_set","Great Lakes Voyageur","set_coureur","great_lakes","colonial_americas"),("vaquero_set","Frontier Vaquero","set_vaquero","frontier","colonial_americas"),("mapuche_rider_set","Mapuche Rider","set_mapuche_rider","southern_cone","americas_material"),("inuit_hunter_set","Arctic Hunter","set_inuit_hunter","arctic","americas_material"),
 ("maya_scribe_set","Maya Scribe","set_maya_scribe","mesoamerica","mesoamerican_material"),("muisca_trader_set","Muisca Trader","set_muisca_trader","northern_andes","americas_material"),("guarani_mission_set","Guaraní Mission Artisan","set_guarani_mission","la_plata","colonial_americas"),("california_pilot_set","California Coastal Pilot","set_california_pilot","pacific_coast","colonial_americas"),("great_lakes_broker_set","Great Lakes Broker","set_great_lakes_broker","great_lakes","americas_material"),
 ("haudenosaunee_diplomat_set","Haudenosaunee Diplomat","set_haudenosaunee_diplomat","northeast","americas_material"),("chaco_warrior_set","Chaco Warrior","set_chaco_warrior","chaco","americas_material"),("patagonian_scout_set","Patagonian Scout","set_patagonian_scout","southern_cone","americas_material"),("suriname_maroon_set","Suriname Maroon","set_suriname_maroon","guianas","colonial_americas"),("haitian_revolutionary_set","Haitian Revolutionary","set_haitian_revolutionary","caribbean","colonial_americas")]

SLOTS=(("head","Headwear",{"armor":7,"perception":6}),("chest","Garment",{"armor":12,"endurance":7}),("primary","Arms",{"meleePower":17,"mobility":5}),("trinket","Kit",{"survival":14,"diplomacy":6}))

ORDINARY=[
 ("cassava_travel_cake","Cassava Travel Cake","caribbean","consumable",None,12,(1450,1820),("general_merchant",),{"endurance":9},()),
 ("cacao_field_draught","Cacao Field Draught","mesoamerica","consumable",None,19,(1450,1820),("apothecary","general_merchant"),{"morale":8,"endurance":5},()),
 ("quina_bark_packet","Andean Quina Bark Packet","andes","consumable",None,42,(1630,1820),("apothecary",),{"healing":18,"feverResistance":12},()),
 ("yerba_mate_gourd","Yerba Mate Travel Gourd","la_plata","consumable",None,25,(1450,1820),("general_merchant","apothecary"),{"endurance":13},()),
 ("obsidian_edge_kit","Obsidian Edge-working Kit","mesoamerica","tool",None,23,(1450,1650),("general_merchant","armourer"),{"artisan":13,"repair":5},()),
 ("quipu_accounting_bundle","Quipu Accounting Bundle","andes","tool",None,39,(1450,1820),("bookseller_cartographer","general_merchant"),{"administration":16,"memory":8},()),
 ("birchbark_canoe_repair_roll","Birchbark Canoe Repair Roll","great_lakes","tool",None,31,(1450,1820),("ship_chandler","general_merchant"),{"repair":15,"riverMobility":7},()),
 ("arctic_sewing_case","Arctic Sinew Sewing Case","arctic","tool",None,28,(1450,1820),("outfitter","general_merchant"),{"repair":12,"coldResistance":6},()),
 ("caribbean_swell_memory_board","Caribbean Swell Memory Board","caribbean","book_map",None,35,(1450,1820),("ship_chandler","bookseller_cartographer"),{"navigation":16,"reefSense":7},()),
 ("nahua_market_codex","Nahua Market Codex","mesoamerica","book_map",None,47,(1450,1700),("bookseller_cartographer","relic_merchant"),{"trade":17,"learning":10},()),
 ("andean_road_khipu","Andean Road Khipu","andes","book_map",None,51,(1450,1820),("bookseller_cartographer","general_merchant"),{"routeFinding":19,"supply":11},()),
 ("amazon_channel_chart","Amazon Channel Chart","amazonia","book_map",None,58,(1650,1820),("ship_chandler","bookseller_cartographer"),{"navigation":20,"riverMobility":12},()),
 ("wampum_diplomatic_belt","Wampum Diplomatic Belt","northeast","artifact","trinket",55,(1450,1820),("general_merchant","relic_merchant"),{"diplomacy":22,"memory":9},()),
 ("colonial_printed_almanac","Colonial Printed Almanac","colonial","book_map",None,72,(1650,1820),("bookseller_cartographer",),{"learning":18,"navigation":9},("movable_type_printing",)),
 ("kentucky_rifle","Long Frontier Rifle","frontier","equipment","primary",118,(1730,1820),("gunsmith","military_supplier"),{"rangedPower":38,"reload":-8},("flintlock_drill",)),
 ("caribbean_boarding_pistol","Caribbean Boarding Pistol","caribbean","equipment","offhand",91,(1660,1820),("gunsmith","ship_chandler"),{"rangedPower":27,"boarding":13},("flintlock_drill",)),
 ("silver_mounted_vaquero_saddle","Silver-mounted Vaquero Saddle","frontier","equipment","mount",79,(1600,1820),("horse_dealer","outfitter"),{"mountedMobility":25,"trade":6},()),
 ("revolutionary_field_surgery_case","Revolutionary Field-surgery Case","colonial","tool",None,146,(1770,1820),("apothecary","military_supplier"),{"medicine":39,"healing":22},()),
]

UNIQUE_NAMES=[
 "Hiawatha Wampum Tradition","Deganawida Peace Belt","Powhatan Mantle Tradition","Metacom War Club","Pontiac Council Pipe","Tecumseh Sash","Black Hawk Medicine Bundle","Sacagawea Trail Token","Pocahontas Copper Necklace","Joseph Brant Gorget","Red Jacket Peace Medal","Sequoyah Silversmith Tablet","Osceola Powder Horn","Micanopy Council Staff","Dragging Canoe Belt","Cornstalk Pipe Tomahawk","Little Turtle Treaty Medal","Blue Jacket War Belt","King Philip Belt","Uncas Council Token",
 "Moctezuma Featherwork Tradition","Cuauhtemoc Shield Tradition","Nezahualcoyotl Poetry Codex","Malintzin Interpreter Token","Tupac Yupanqui Standard","Atahualpa Royal Fringe","Manco Inca Sun Emblem","Tupac Amaru II Hat","Garcilaso Royal Commentaries","Pachacuti Stone Measure","Lautaro Lance","Caupolican Command Club","Janequeo Riding Mantle","Galvarino War Token","Tupac Katari Sling","Bartolina Sisa Standard","Zumbi Palmares Spear","Ganga Zumba Council Staff","Benkos Bioho Machete","Nanny Maroon Horn",
 "Anacaona Areito Belt","Caonabo Stone Pendant","Hatuey Resistance Staff","Agueybana Cemi","Enriquillo Treaty Cross","Kalina Sea Bow","Orellana River Astrolabe","Acuna Amazon Journal","Bolivar Campaign Sword","San Martin Curved Saber","Toussaint Louverture Dress Sword","Dessalines Standard","Henri Christophe Crown Emblem","Jose Maria Morelos Bandana","Miguel Hidalgo Banner Token","Manuela Saenz Dispatch Case","Juana Azurduy Saber","Artigas Gaucho Poncho","Tiradentes Mining Tools","Francisco Miranda Tricolor","George Washington Survey Compass","Benjamin Franklin Spectacles","Simon Fraser River Journal"]

def row(ident,name,sub,category,slot,level,years,merchants,stats,evidence,*,unique=False,set_id=None,tech=()):
 req={"startYear":years[0],"endYear":years[1],"regionIds":["americas_caribbean"]}
 if tech:req["technologyIds"]=list(tech)
 late=years[0]>=1500
 return {"id":ident,"name":name,"category":category,"itemLevel":level,"rarityId":("relic" if unique else "rare" if level>=55 else "fine"),"provenance":{"kind":"historical" if unique else "set_piece" if set_id else "regional","identityId":ident+"_identity"},"unique":unique,"requirements":req,"enhancement":{"maxRank":5 if unique else 3,"maxRestoration":4 if unique else 2},"merchant":{"eligible":True,"archetypeIds":list(merchants),"basePriceMinor":level*(65 if unique else 12),"minimumWealth":min(80,level//3),**({"requiresTradeAccess":True} if late and category in {"book_map","artifact"} else {})},"comparison":{"slotIds":[slot] if slot else [],"majorStats":stats,"effectIds":(["frontier_adaptation"] if sub in {"frontier","colonial"} else []),**({"setId":set_id} if set_id else {})},"coverage":{"subregionIds":[sub],"historicalClass":"named_historical" if unique else "ordinary"},"availability":{"source":"deterministic_merchant","ownershipPolicy":"singular_registry" if unique else "ordinary_instance","rewardQuestIds":[]},"evidenceIds":[evidence]}

def expand():
 data=json.loads(CATALOG.read_text())
 have={x["id"] for x in data["effects"]}; data["effects"] += [{"id":k,"kind":v} for k,v in EFFECTS.items() if k not in have]
 have={x["id"] for x in data["historicalEvidence"]}; data["historicalEvidence"] += [{"id":i,"citation":c,"note":n} for i,c,n in EVIDENCE if i not in have]
 items=[]; sets=[]
 for si,(sid,sname,effect,sub,evidence) in enumerate(SET_NAMES):
  ids=[]
  for pi,(slot,label,stats) in enumerate(SLOTS):
   ident=sid.removesuffix("_set")+"_"+slot; ids.append(ident); level=24+si*3+pi*2
   start=1770 if sid in {"republic_officer_set","haitian_revolutionary_set"} else 1650 if sid in {"colonial_militia_set","suriname_maroon_set"} else 1450
   tech=("flintlock_drill",) if start>=1650 and slot=="primary" else ()
   items.append(row(ident,f"{sname} {label}",sub,"equipment",slot,level,(start,1820),("armourer","outfitter","military_supplier"),dict(stats),evidence,set_id=sid,tech=tech))
  sets.append({"id":sid,"name":sname,"itemTypeIds":ids,"thresholds":[{"pieceCount":2,"effectIds":[effect]},{"pieceCount":3,"effectIds":["set_mobility"]},{"pieceCount":4,"effectIds":[effect,"set_resilience"]}]})
 for v in ORDINARY:
  ident,name,sub,cat,slot,level,years,merchants,stats,tech=v
  evidence="caribbean_material" if sub=="caribbean" else "andean_material" if sub=="andes" else "mesoamerican_material" if sub=="mesoamerica" else "colonial_americas" if years[0]>=1600 else "americas_material"
  items.append(row(ident,name,sub,cat,slot,level,years,merchants,stats,evidence,tech=tech))
 for n,name in enumerate(UNIQUE_NAMES):
  ident=''.join(c.lower() if c.isalnum() else '_' for c in name).strip('_').replace('__','_')
  start=1450 if n<40 else 1500+(n%7)*50
  sub="north_america" if n<20 else "mesoamerica_andes" if n<40 else "caribbean_colonial"
  evidence="americas_material" if n<20 else "andean_material" if n<40 else "colonial_americas"
  items.append(row(ident,name,sub,"artifact","trinket",105+n,(start,1820),("relic_merchant",),{"authority":25+n%17,"diplomacy":12+n%13},evidence,unique=True,tech=(("flintlock_drill",) if start>=1700 else ())))
 setids={x["id"] for x in sets}; itemids={x["id"] for x in items}
 data["equipmentSets"]=[x for x in data["equipmentSets"] if x["id"] not in setids]+sets
 data["items"]=[x for x in data["items"] if x["id"] not in itemids]+items
 CATALOG.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")

if __name__=="__main__": expand()

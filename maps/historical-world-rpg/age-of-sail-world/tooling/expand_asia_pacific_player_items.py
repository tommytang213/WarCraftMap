#!/usr/bin/env python3
"""Deterministically author the issue-281 Asia-Pacific player-use catalogue pass.

The resulting JSON is the scenario authority.  This idempotent recipe keeps the
large content pass reviewable without putting regional names in shared code.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "scenario/inventory/player-use-catalog.json"


EFFECTS = {
    "river_campaigning": "conditional", "monsoon_trader": "conditional",
    "court_audience": "conditional", "island_wayfinding": "passive",
    "reef_landing": "conditional", "scholarly_method": "passive",
    "field_medicine": "active", "concealed_defence": "conditional",
    "volley_discipline": "conditional", "mounted_archery": "conditional",
    "storm_reading": "passive", "artisan_precision": "passive",
    "ritual_authority": "conditional", "set_jungle_column": "threshold",
    "set_strait_broker": "threshold", "set_mandarin_scholar": "threshold",
    "set_samurai_retainer": "threshold", "set_steppe_rider": "threshold",
    "set_blue_water_voyager": "threshold", "set_island_diplomat": "threshold",
    "set_reef_guardian": "threshold", "set_expedition_surveyor": "threshold",
}

EVIDENCE = [
    ("sea_monsoon_world", "Anthony Reid, Southeast Asia in the Age of Commerce, 1450–1680", "Regional commerce, dress, arms, medicines, and port institutions."),
    ("southeast_arms", "Michael Charney, Southeast Asian Warfare, 1300–1900", "Mainland and maritime arms, elephants, firearms, and military practice."),
    ("malay_world", "Barbara Watson Andaya and Leonard Andaya, A History of Malaysia", "Malay court, strait, kris, and mercantile contexts."),
    ("china_material", "Joseph Needham, Science and Civilisation in China", "Chinese instruments, printing, medicine, craft, and technical practice."),
    ("ming_trade", "Timothy Brook, The Confusions of Pleasure", "Ming material culture, commerce, print, and social institutions."),
    ("japan_warfare", "Thomas Conlan, Weapons and Fighting Techniques of the Samurai Warrior", "Japanese arms, armour, firearms, and campaigning equipment."),
    ("korea_material", "Michael Seth, A History of Korea", "Joseon scholarship, administration, military technology, and material culture."),
    ("inner_asia", "David Sneath, The Headless State", "Inner Asian pastoral, mounted, diplomatic, and political equipment."),
    ("pacific_navigation", "Ben Finney, Voyage of Rediscovery", "Oceanic wayfinding, sailing practice, and experimental voyaging evidence."),
    ("pacific_material", "Patrick Kirch, On the Road of the Winds", "Pacific exchange, settlement, voyaging, and material cultures."),
    ("polynesian_societies", "Patrick Kirch and Roger Green, Hawaiki, Ancestral Polynesia", "Polynesian tools, ceremony, textiles, and social practice."),
    ("contact_pacific", "Anne Salmond, The Trial of the Cannibal Dog", "Pacific contact-era exchange, collecting, mediation, and consequences."),
]


def item(ident, name, region, subregions, category, slot, level, rarity, kind,
         years, merchants, stats, *, set_id=None, effects=(), technology=(),
         institutions=(), controllers=(), settlements=(), local=(), trade=False,
         evidence=(), unique=False, quest=(), events=(), historical_class=None,
         price=None):
    req = {"startYear": years[0], "endYear": years[1], "regionIds": [region]}
    if technology: req["technologyIds"] = list(technology)
    if institutions: req["institutionIds"] = list(institutions)
    if controllers: req["controllerIds"] = list(controllers)
    if settlements: req["settlementIds"] = list(settlements)
    if quest: req["questFlagIds"] = list(quest)
    if events: req["eventFlagIds"] = list(events)
    merchant = {"eligible": bool(merchants), "archetypeIds": list(merchants),
                "basePriceMinor": price or max(45, level * 11),
                "minimumWealth": min(85, max(0, level // 3))}
    if local: merchant["localProductionAny"] = list(local)
    if trade: merchant["requiresTradeAccess"] = True
    identity = {"kind": kind}
    if kind != "generic" or unique: identity["identityId"] = ident + "_identity"
    comparison = {"slotIds": [slot] if slot else [], "majorStats": stats,
                  "effectIds": list(effects)}
    if effects and any(x in {"river_campaigning", "monsoon_trader", "court_audience", "reef_landing", "concealed_defence", "volley_discipline", "mounted_archery", "ritual_authority"} for x in effects):
        comparison["conditionalEffects"] = [{"id": x, "condition": x} for x in effects if EFFECTS.get(x) == "conditional"]
    if set_id: comparison["setId"] = set_id
    row = {"id": ident, "name": name, "category": category, "itemLevel": level,
           "rarityId": rarity, "provenance": identity, "unique": unique,
           "requirements": req,
           "enhancement": {"maxRank": 0 if category == "consumable" else min(7, 1 + level // 45),
                           "maxRestoration": 4 if unique else (0 if category == "consumable" else 2)},
           "merchant": merchant, "comparison": comparison,
           "coverage": {"subregionIds": list(subregions),
                        "historicalClass": historical_class or ("singular" if unique else "ordinary")},
           "availability": {"source": "deterministic_merchant" if merchants else "quest_reward",
                            "ownershipPolicy": "singular_registry" if unique else "ordinary_instance",
                            "rewardQuestIds": list(quest)},
           "evidenceIds": list(evidence)}
    return row


SET_SPECS = [
    ("mekong_field_set", "Mekong Field Column", "southeast_asia", ("mainland",), "set_jungle_column", [
        ("rattan_campaign_helmet", "Rattan Campaign Helmet", "head", 28, "fine", {"armor": 7, "heatResistance": 7}),
        ("quilted_campaign_jacket", "Quilted Campaign Jacket", "chest", 32, "fine", {"armor": 10, "mobility": 3}),
        ("dha_field_blade", "Dha Field Blade", "primary", 35, "superior", {"meleePower": 17, "jungleMobility": 6}),
        ("bamboo_water_case", "Bamboo Water Case", "trinket", 24, "common", {"endurance": 9, "heatResistance": 5})]),
    ("malacca_broker_set", "Malacca Strait Broker", "southeast_asia", ("maritime", "straits"), "set_strait_broker", [
        ("malay_baju_dagang", "Malay Merchant's Baju", "chest", 42, "superior", {"trade": 14, "diplomacy": 7}),
        ("strait_ledger_case", "Strait Ledger Case", "offhand", 39, "rare", {"trade": 16, "accounting": 9}),
        ("merchant_signet_ring", "Port Merchant's Signet", "ring", 45, "rare", {"credit": 12, "diplomacy": 11}),
        ("monsoon_route_roll", "Monsoon Route Roll", "trinket", 48, "rare", {"navigation": 13, "tradeRange": 10})]),
    ("javanese_court_set", "Javanese Court Retinue", "southeast_asia", ("java", "island"), "ritual_authority", [
        ("javanese_batik_wrapping", "Javanese Court Batik", "chest", 38, "superior", {"diplomacy": 12, "morale": 5}),
        ("court_kris", "Court-forged Kris", "primary", 47, "rare", {"meleePower": 17, "authority": 12}),
        ("gilded_sirih_box", "Gilded Sirih Box", "offhand", 43, "rare", {"diplomacy": 14, "hospitality": 8}),
        ("court_ear_ornament", "Court Ear Ornament", "trinket", 36, "fine", {"authority": 9, "trade": 5})]),
    ("spice_island_pilot_set", "Spice Island Pilot", "southeast_asia", ("maluku", "island"), "storm_reading", [
        ("palm_fiber_rain_cape", "Palm-fibre Rain Cape", "chest", 31, "fine", {"stormResistance": 12, "mobility": 3}),
        ("outrigger_sounding_line", "Outrigger Sounding Line", "offhand", 34, "fine", {"navigation": 12, "reefSense": 8}),
        ("clove_island_chart", "Clove Islands Pilot Chart", "trinket", 52, "rare", {"navigation": 17, "tradeRange": 9}),
        ("shell_inlaid_compass_box", "Shell-inlaid Bearing Box", "ring", 49, "rare", {"navigation": 14, "stormResistance": 6})]),
    ("ming_scholar_set", "Ming Scholar-official", "east_asia", ("china", "scholarly"), "set_mandarin_scholar", [
        ("scholars_winged_cap", "Scholar's Winged Cap", "head", 44, "rare", {"learning": 14, "authority": 8}),
        ("silk_official_robe", "Silk Official Robe", "chest", 50, "rare", {"diplomacy": 14, "administration": 13}),
        ("inkstone_and_brush", "Inkstone and Brush Case", "offhand", 41, "superior", {"learning": 15, "survey": 5}),
        ("civil_service_classics", "Civil Service Classics", "trinket", 55, "epic", {"administration": 18, "learning": 12})]),
    ("sengoku_retainer_set", "Sengoku Retainer", "east_asia", ("japan", "military"), "set_samurai_retainer", [
        ("lacquered_kabuto", "Lacquered Kabuto", "head", 56, "rare", {"armor": 16, "morale": 7}),
        ("tosei_gusoku_cuirass", "Tosei-gusoku Cuirass", "chest", 66, "epic", {"armor": 25, "mobility": -4}),
        ("katana_and_saya", "Katana and Saya", "primary", 61, "rare", {"meleePower": 28, "guard": 8}),
        ("war_fan_gunbai", "Gunbai War Fan", "offhand", 53, "rare", {"command": 15, "rangedResistance": 5})]),
    ("steppe_envoy_set", "Steppe Envoy", "east_asia", ("inner_asia", "frontier"), "set_steppe_rider", [
        ("fur_riding_hat", "Fur Riding Hat", "head", 29, "fine", {"coldResistance": 10, "perception": 4}),
        ("lamellar_riding_coat", "Lamellar Riding Coat", "chest", 48, "rare", {"armor": 17, "mountedMobility": 5}),
        ("composite_horse_bow", "Composite Horse Bow", "primary", 51, "rare", {"rangedPower": 22, "mountedPower": 12}),
        ("steppe_high_saddle", "Steppe High Saddle", "mount", 46, "superior", {"mountedMobility": 18, "mountedGuard": 8})]),
    ("joseon_guard_set", "Joseon Guard", "east_asia", ("korea", "military"), "volley_discipline", [
        ("joseon_jeonrip", "Joseon Jeonrip", "head", 39, "superior", {"armor": 9, "command": 5}),
        ("dujeong_gap_coat", "Dujeong-gap Coat", "chest", 55, "rare", {"armor": 20, "mobility": -2}),
        ("gakgung_horn_bow", "Gakgung Horn Bow", "primary", 58, "rare", {"rangedPower": 27, "range": 7}),
        ("archers_bracer", "Horn Archer's Bracer", "gloves", 37, "fine", {"reload": 9, "rangedPower": 5})]),
    ("polynesian_voyager_set", "Blue-water Wayfinder", "pacific", ("polynesia", "voyaging"), "set_blue_water_voyager", [
        ("pandanus_sun_shade", "Pandanus Sun Shade", "head", 25, "fine", {"heatResistance": 9, "perception": 5}),
        ("barkcloth_voyaging_wrap", "Barkcloth Voyaging Wrap", "chest", 30, "fine", {"stormResistance": 8, "endurance": 7}),
        ("star_path_cord", "Star-path Memory Cord", "trinket", 47, "rare", {"navigation": 20, "memory": 8}),
        ("swell_reading_staff", "Swell-reading Staff", "offhand", 43, "rare", {"navigation": 16, "stormSense": 10})]),
    ("pacific_envoy_set", "Island Council Envoy", "pacific", ("micronesia", "melanesia", "polynesia"), "set_island_diplomat", [
        ("shell_headband", "Shell Council Headband", "head", 32, "superior", {"authority": 8, "diplomacy": 8}),
        ("fine_mat_cloak", "Fine Mat Cloak", "chest", 40, "rare", {"diplomacy": 15, "hospitality": 7}),
        ("exchange_shell_strand", "Exchange Shell Strand", "ring", 38, "rare", {"trade": 13, "diplomacy": 6}),
        ("orators_fly_whisk", "Orator's Fly Whisk", "offhand", 44, "rare", {"authority": 15, "morale": 8})]),
    ("melanesian_reef_set", "Melanesian Reef Guardian", "pacific", ("melanesia", "reef"), "set_reef_guardian", [
        ("woven_cane_helmet", "Woven Cane Helmet", "head", 27, "fine", {"armor": 7, "mobility": 4}),
        ("fiber_war_cuirass", "Fibre War Cuirass", "chest", 36, "superior", {"armor": 13, "heatResistance": 4}),
        ("obsidian_tipped_spear", "Obsidian-tipped Spear", "primary", 40, "superior", {"meleePower": 19, "armorPiercing": 5}),
        ("reefwood_shield", "Reefwood Shield", "offhand", 35, "fine", {"guard": 14, "reefMobility": 6})]),
    ("pacific_survey_set", "Pacific Natural-history Survey", "pacific", ("contact_ports", "exploration"), "set_expedition_surveyor", [
        ("waxed_specimen_hat", "Waxed Specimen Hat", "head", 73, "rare", {"perception": 15, "weatherResistance": 8}),
        ("surveyors_field_coat", "Surveyor's Field Coat", "chest", 81, "epic", {"survey": 17, "endurance": 10}),
        ("botanical_collecting_case", "Botanical Collecting Case", "offhand", 78, "rare", {"naturalHistory": 22, "medicine": 5}),
        ("brass_sextant_case", "Brass Sextant and Case", "trinket", 92, "epic", {"navigation": 28, "survey": 14})]),
]


ORDINARY = [
    # id, name, region, subregions, category, slot, level, rarity, provenance, years, merchants, stats, options
    ("betel_travel_packet", "Betel Travel Packet", "southeast_asia", ("mainland","maritime"), "consumable", None, 12, "common", "regional", (1450,1820), ("general_merchant","apothecary"), {"morale":6}, {}),
    ("tamarind_fever_draught", "Tamarind Fever Draught", "southeast_asia", ("mainland",), "consumable", None, 26, "fine", "profession", (1450,1820), ("apothecary",), {"healing":13,"heatResistance":5}, {"effects":("field_medicine",)}),
    ("tin_smiths_tool_roll", "Tin-smith's Tool Roll", "southeast_asia", ("malaya","straits"), "tool", None, 33, "superior", "profession", (1450,1820), ("general_merchant","dockyard"), {"repair":14,"artisan":10}, {"local":("tin",)}),
    ("bamboo_survey_chain", "Bamboo Survey Chain", "southeast_asia", ("mainland",), "tool", None, 29, "fine", "profession", (1450,1820), ("bookseller_cartographer","general_merchant"), {"survey":14}, {}),
    ("lontar_navigation_text", "Lontar Navigation Text", "southeast_asia", ("java","maritime"), "book_map", None, 38, "superior", "cultural", (1450,1750), ("bookseller_cartographer","ship_chandler"), {"navigation":14,"learning":5}, {"trade":True}),
    ("red_river_pilot_notes", "Red River Pilot Notes", "southeast_asia", ("dai_viet","mainland"), "book_map", None, 35, "fine", "regional", (1450,1820), ("bookseller_cartographer","ship_chandler"), {"navigation":11,"riverTrade":8}, {"settlements":("thang_long","van_don","pho_hien")}),
    ("siamese_elephant_howdah", "Siamese War Howdah", "southeast_asia", ("siam","mainland"), "equipment", "mount", 63, "rare", "polity", (1500,1820), ("horse_dealer","military_supplier"), {"mountedGuard":20,"command":9}, {"controllers":("ayutthaya_kingdom",),"evidence":("southeast_arms",)}),
    ("makassar_chain_coif", "Makassar Chain Coif", "southeast_asia", ("sulawesi","maritime"), "equipment", "head", 48, "rare", "cultural", (1550,1820), ("armourer","military_supplier"), {"armor":15,"boarding":6}, {"technology":("cast_cannon",),"trade":True}),
    ("lusong_swivel_gun_kit", "Lusong Swivel-gun Kit", "southeast_asia", ("philippines","maritime"), "tool", None, 59, "rare", "profession", (1500,1820), ("gunsmith","ship_chandler"), {"gunnery":20,"repair":8}, {"technology":("cast_cannon",),"trade":True}),
    ("ternate_clove_tonic", "Ternate Clove Tonic", "southeast_asia", ("maluku","island"), "consumable", None, 31, "superior", "regional", (1450,1820), ("apothecary","general_merchant"), {"healing":10,"morale":9}, {"settlements":("ternate","ternate_harbor","tidore","tidore_harbor")}),
    ("padded_river_boots", "Padded River Boots", "southeast_asia", ("mainland","river"), "equipment", "boots", 22, "common", "profession", (1450,1820), ("outfitter","general_merchant"), {"riverMobility":10,"armor":2}, {"effects":("river_campaigning",)}),
    ("spice_brokers_abacus", "Spice Broker's Counting Board", "southeast_asia", ("straits","maritime"), "tool", None, 46, "rare", "profession", (1450,1820), ("general_merchant","bookseller_cartographer"), {"trade":18,"accounting":10}, {"effects":("monsoon_trader",),"trade":True}),

    ("ming_paper_armour", "Ming Paper Armour", "east_asia", ("china","military"), "equipment", "chest", 37, "superior", "cultural", (1450,1700), ("armourer","military_supplier"), {"armor":12,"mobility":5}, {"evidence":("china_material",)}),
    ("fire_lance_toolkit", "Fire-lance Armourer's Kit", "east_asia", ("china","military"), "tool", None, 35, "fine", "profession", (1450,1650), ("gunsmith","military_supplier"), {"gunnery":11,"repair":9}, {"technology":("cast_cannon",)}),
    ("japanese_tanegashima", "Tanegashima Matchlock", "east_asia", ("japan","military"), "equipment", "primary", 68, "epic", "cultural", (1543,1820), ("gunsmith","military_supplier"), {"rangedPower":31,"reload":-5}, {"technology":("cast_cannon",),"effects":("volley_discipline",),"trade":True,"evidence":("japan_warfare",)}),
    ("joseon_medical_case", "Joseon Physician's Case", "east_asia", ("korea","medical"), "tool", None, 49, "rare", "profession", (1450,1820), ("apothecary",), {"medicine":20,"healing":8}, {"effects":("field_medicine",),"evidence":("korea_material",)}),
    ("moxa_treatment_packet", "Moxa Treatment Packet", "east_asia", ("china","korea","japan"), "consumable", None, 20, "common", "cultural", (1450,1820), ("apothecary","general_merchant"), {"healing":11}, {}),
    ("ginseng_restorative", "Ginseng Restorative", "east_asia", ("korea","manchuria"), "consumable", None, 34, "superior", "regional", (1450,1820), ("apothecary","general_merchant"), {"healing":14,"endurance":10}, {"trade":True}),
    ("woodblock_coastal_atlas", "Woodblock Coastal Atlas", "east_asia", ("china","scholarly"), "book_map", None, 57, "rare", "profession", (1450,1820), ("bookseller_cartographer","ship_chandler"), {"navigation":20,"learning":9}, {"institutions":("movable_type_printing",),"effects":("scholarly_method",)}),
    ("ryukyu_tribute_ledger", "Ryukyu Tribute Ledger", "east_asia", ("ryukyu","maritime"), "book_map", None, 52, "rare", "polity", (1450,1700), ("bookseller_cartographer","general_merchant"), {"trade":19,"diplomacy":9}, {"controllers":("ryukyu_kingdom",),"settlements":("shuri",),"trade":True}),
    ("ainu_matanpush", "Ainu Matanpush", "east_asia", ("ainu","frontier"), "equipment", "head", 30, "fine", "cultural", (1450,1820), ("outfitter","general_merchant"), {"coldResistance":12,"wilderness":7}, {}),
    ("tibetan_medicine_satchel", "Tibetan Medicine Satchel", "east_asia", ("tibet","medical"), "tool", None, 42, "superior", "profession", (1450,1820), ("apothecary","general_merchant"), {"medicine":16,"coldResistance":5}, {}),
    ("porcelain_medicine_jar", "Porcelain Medicine Jar", "east_asia", ("china","artisanal"), "tool", None, 27, "fine", "profession", (1450,1820), ("apothecary","general_merchant"), {"medicine":9,"supplyPreservation":9}, {"local":("porcelain",)}),
    ("kangnido_copy", "Kangnido World-map Copy", "east_asia", ("korea","scholarly"), "book_map", None, 64, "epic", "historical", (1450,1820), ("bookseller_cartographer","relic_merchant"), {"navigation":22,"learning":14}, {"evidence":("korea_material",)}),

    ("coconut_water_gourd", "Coconut-water Gourd", "pacific", ("micronesia","melanesia","polynesia"), "consumable", None, 10, "common", "regional", (1450,1820), ("general_merchant","ship_chandler"), {"endurance":8,"heatResistance":4}, {}),
    ("noni_leaf_poultice", "Noni-leaf Poultice", "pacific", ("melanesia","polynesia"), "consumable", None, 18, "fine", "cultural", (1450,1820), ("apothecary","general_merchant"), {"healing":10,"poisonResistance":4}, {"effects":("field_medicine",)}),
    ("breadfruit_voyage_ration", "Breadfruit Voyage Ration", "pacific", ("polynesia","voyaging"), "consumable", None, 16, "common", "regional", (1450,1820), ("general_merchant","ship_chandler"), {"endurance":11}, {}),
    ("tridacna_shell_adze", "Tridacna-shell Adze", "pacific", ("micronesia","island"), "tool", None, 28, "fine", "cultural", (1450,1820), ("general_merchant","dockyard"), {"woodcraft":17,"repair":8}, {}),
    ("canoe_lashing_roll", "Coconut-sennit Lashing Roll", "pacific", ("micronesia","melanesia","polynesia"), "tool", None, 24, "common", "profession", (1450,1820), ("ship_chandler","dockyard","general_merchant"), {"repair":14,"stormResistance":4}, {}),
    ("stick_navigation_chart", "Marshall Islands Stick Chart", "pacific", ("micronesia","voyaging"), "book_map", None, 48, "rare", "cultural", (1450,1820), ("bookseller_cartographer","ship_chandler"), {"navigation":21,"swellSense":10}, {"settlements":("marshall_council","nan_madol"),"evidence":("pacific_navigation",)}),
    ("palauan_storyboard_chart", "Belau Route Storyboard", "pacific", ("micronesia","voyaging"), "book_map", None, 39, "superior", "cultural", (1450,1820), ("bookseller_cartographer","general_merchant"), {"navigation":14,"memory":9}, {"settlements":("belau_council","koror")}),
    ("maori_patu", "Māori Patu", "pacific", ("aotearoa","military"), "equipment", "primary", 37, "superior", "cultural", (1450,1820), ("armourer","general_merchant"), {"meleePower":17,"concealment":7}, {}),
    ("maori_dogskin_cloak", "Māori Dogskin Cloak", "pacific", ("aotearoa","ceremonial"), "equipment", "chest", 51, "rare", "cultural", (1450,1820), ("outfitter","relic_merchant"), {"authority":15,"coldResistance":12}, {"settlements":("tamaki_makaurau","kaiapoi_pa","aotearoa_runanga")}),
    ("hawaiian_feather_helmet", "Hawaiian Feather Helmet", "pacific", ("hawaii","ceremonial"), "equipment", "head", 58, "epic", "polity", (1450,1820), ("relic_merchant",), {"authority":20,"morale":11}, {"controllers":("hawaii_chiefdom","maui_chiefdom","oahu_chiefdom","kauai_chiefdom"),"effects":("ritual_authority",),"evidence":("polynesian_societies",)}),
    ("fijian_throwing_club", "Fijian Throwing Club", "pacific", ("fiji","military"), "equipment", "primary", 34, "fine", "cultural", (1450,1820), ("armourer","general_merchant"), {"meleePower":13,"rangedPower":10}, {"settlements":("fiji_council","mua","lakeba_voyaging_center")}),
    ("reef_passage_sounding_stone", "Reef-passage Sounding Stone", "pacific", ("micronesia","melanesia","reef"), "tool", None, 32, "superior", "profession", (1450,1820), ("ship_chandler","general_merchant"), {"navigation":11,"reefSense":13}, {"effects":("reef_landing",)}),
]

# Additional independent choices fill profession, era, merchant, and high-level
# bands without turning set pieces into the only useful regional progression.
ORDINARY += [
    ("burmese_lacquer_shield", "Burmese Lacquer Shield", "southeast_asia", ("burma","mainland"), "equipment", "offhand", 44, "superior", "cultural", (1450,1820), ("armourer","military_supplier"), {"guard":18,"heatResistance":4}, {}),
    ("cham_cotton_turban", "Cham Cotton Turban", "southeast_asia", ("champa","maritime"), "equipment", "head", 23, "fine", "cultural", (1450,1820), ("outfitter","general_merchant"), {"heatResistance":9,"trade":4}, {}),
    ("visayan_kalasag", "Visayan Kalasag Shield", "southeast_asia", ("philippines","island"), "equipment", "offhand", 36, "fine", "cultural", (1450,1820), ("armourer","general_merchant"), {"guard":15,"rangedResistance":4}, {}),
    ("aceh_matchlock", "Aceh Matchlock", "southeast_asia", ("sumatra","military"), "equipment", "primary", 74, "rare", "polity", (1560,1820), ("gunsmith","military_supplier"), {"rangedPower":32,"reload":-7}, {"technology":("cast_cannon",),"events":("aceh_strait_competition",),"trade":True}),
    ("manila_galleon_pilot_book", "Manila Galleon Pilot Book", "southeast_asia", ("philippines","exploration"), "book_map", None, 88, "epic", "profession", (1570,1820), ("bookseller_cartographer","ship_chandler"), {"navigation":28,"tradeRange":16}, {"technology":("standardized_charts",),"trade":True}),
    ("javanese_bronze_gong", "Portable Javanese Bronze Gong", "southeast_asia", ("java","ceremonial"), "tool", None, 40, "superior", "cultural", (1450,1820), ("general_merchant","relic_merchant"), {"morale":16,"authority":5}, {}),
    ("palm_leaf_contract_bundle", "Palm-leaf Contract Bundle", "southeast_asia", ("straits","mercantile"), "book_map", None, 31, "fine", "profession", (1450,1820), ("general_merchant","bookseller_cartographer"), {"trade":13,"accounting":7}, {}),
    ("royal_ayutthaya_sash", "Ayutthaya Royal Service Sash", "southeast_asia", ("siam","court"), "equipment", "trinket", 69, "rare", "polity", (1569,1820), ("relic_merchant","outfitter"), {"authority":21,"diplomacy":11}, {"controllers":("ayutthaya_kingdom",),"events":("toungoo_unification_pressure",)}),
    ("percussion_jungle_musket", "Percussion Jungle Musket", "southeast_asia", ("mainland","military"), "equipment", "primary", 186, "legendary", "profession", (1807,1820), ("gunsmith","military_supplier"), {"rangedPower":59,"reload":14}, {"technology":("flintlock_drill","precision_engineering",),"trade":True}),
    ("integrated_strait_exchange_ledger", "Integrated Strait Exchange Ledger", "southeast_asia", ("straits","mercantile"), "book_map", None, 226, "epic", "profession", (1780,1820), ("bookseller_cartographer","general_merchant"), {"trade":54,"credit":30}, {"technology":("integrated_world_markets",),"institutions":("public_credit",),"trade":True}),

    ("chinese_ring_pommel_sabre", "Ring-pommel Sabre", "east_asia", ("china","military"), "equipment", "primary", 33, "fine", "cultural", (1450,1820), ("armourer","military_supplier"), {"meleePower":16,"guard":5}, {}),
    ("japanese_waraji", "Straw Waraji", "east_asia", ("japan","artisanal"), "equipment", "boots", 17, "common", "regional", (1450,1820), ("outfitter","general_merchant"), {"mobility":8,"endurance":4}, {}),
    ("mongol_deel", "Steppe Riding Deel", "east_asia", ("inner_asia","frontier"), "equipment", "chest", 34, "fine", "cultural", (1450,1820), ("outfitter","horse_dealer"), {"coldResistance":13,"mountedMobility":5}, {}),
    ("jurchen_hunting_spear", "Jurchen Hunting Spear", "east_asia", ("manchuria","frontier"), "equipment", "primary", 41, "superior", "cultural", (1450,1820), ("armourer","general_merchant"), {"meleePower":18,"wilderness":9}, {}),
    ("beijing_star_catalogue", "Beijing Star Catalogue", "east_asia", ("china","scholarly"), "book_map", None, 72, "epic", "profession", (1450,1820), ("bookseller_cartographer","relic_merchant"), {"navigation":24,"learning":16}, {"technology":("celestial_navigation",)}),
    ("sakai_gunsmith_gauge", "Sakai Gunsmith's Gauge", "east_asia", ("japan","artisanal"), "tool", None, 77, "rare", "profession", (1550,1820), ("gunsmith","general_merchant"), {"gunnery":22,"artisan":17}, {"technology":("cast_cannon",)}),
    ("joseon_rain_gauge_copy", "Joseon Rain-gauge Copy", "east_asia", ("korea","scholarly"), "tool", None, 60, "rare", "historical", (1450,1820), ("bookseller_cartographer","relic_merchant"), {"survey":22,"agriculture":10}, {"evidence":("korea_material",)}),
    ("qing_banner_quiver", "Banner Army Quiver", "east_asia", ("china","military"), "equipment", "offhand", 94, "epic", "polity", (1644,1820), ("military_supplier","relic_merchant"), {"rangedPower":19,"command":18}, {"events":("qing_transition_pressure",)}),
    ("precision_court_theodolite", "Court Survey Theodolite", "east_asia", ("china","scholarly"), "tool", None, 214, "legendary", "profession", (1750,1820), ("bookseller_cartographer","relic_merchant"), {"survey":55,"navigation":31}, {"technology":("precision_engineering","cadastral_survey"),"institutions":("scientific_societies",)}),
    ("steam_era_coastal_manual", "Steam-era Coastal Manual", "east_asia", ("maritime","exploration"), "book_map", None, 272, "relic", "profession", (1815,1820), ("bookseller_cartographer","dockyard"), {"navigation":62,"engineering":44}, {"technology":("steam_navigation","precision_engineering"),"trade":True}),

    ("tapa_working_mallet", "Tapa-working Mallet", "pacific", ("polynesia","artisanal"), "tool", None, 21, "common", "profession", (1450,1820), ("general_merchant","outfitter"), {"artisan":12,"trade":3}, {}),
    ("outrigger_sailmakers_needle", "Outrigger Sailmaker's Needle", "pacific", ("micronesia","voyaging"), "tool", None, 29, "fine", "profession", (1450,1820), ("ship_chandler","dockyard"), {"repair":15,"stormResistance":5}, {}),
    ("pandanus_voyaging_sandals", "Pandanus Voyaging Sandals", "pacific", ("micronesia","voyaging"), "equipment", "boots", 24, "fine", "cultural", (1450,1820), ("outfitter","general_merchant"), {"reefMobility":10,"endurance":5}, {}),
    ("sharkskin_hand_wraps", "Sharkskin Hand Wraps", "pacific", ("melanesia","military"), "equipment", "gloves", 31, "superior", "cultural", (1450,1820), ("outfitter","armourer"), {"grip":12,"meleePower":5}, {}),
    ("chiefly_canoe_seat", "Chiefly Canoe Seat", "pacific", ("polynesia","ceremonial"), "equipment", "mount", 46, "rare", "polity", (1450,1820), ("dockyard","relic_merchant"), {"authority":14,"navalMobility":11}, {}),
    ("taro_travel_paste", "Taro Travel Paste", "pacific", ("melanesia","polynesia"), "consumable", None, 14, "common", "regional", (1450,1820), ("general_merchant","ship_chandler"), {"endurance":9}, {}),
    ("unangan_sea_mammal_parka", "Unangan Sea-mammal Parka", "pacific", ("aleutians","island"), "equipment", "chest", 43, "rare", "cultural", (1450,1820), ("outfitter","general_merchant"), {"coldResistance":20,"stormResistance":7}, {}),
    ("contact_interpreter_lexicon", "Pacific Interpreter's Lexicon", "pacific", ("contact_ports","diplomatic"), "book_map", None, 82, "epic", "profession", (1760,1820), ("bookseller_cartographer","general_merchant"), {"diplomacy":27,"trade":15}, {"trade":True}),
    ("chronometer_voyage_box", "Chronometer Voyage Box", "pacific", ("contact_ports","exploration"), "tool", None, 205, "legendary", "profession", (1761,1820), ("bookseller_cartographer","ship_chandler"), {"navigation":52,"survey":25}, {"technology":("marine_chronometer",),"trade":True}),
    ("natural_history_island_atlas", "Natural History Island Atlas", "pacific", ("contact_ports","exploration"), "book_map", None, 258, "relic", "profession", (1780,1820), ("bookseller_cartographer","relic_merchant"), {"naturalHistory":61,"survey":38}, {"technology":("systematic_natural_history","precision_engineering"),"institutions":("scientific_societies",),"trade":True}),
]


UNIQUES = [
    ("hang_tuah_taming_sari", "Taming Sari of Hang Tuah", "southeast_asia", ("malaya","court"), "primary", 108, "legendary", (1450,1820), (), {"meleePower":38,"authority":20}, {"quest":("hang_tuah_personal_quest",),"evidence":("malay_world",)}),
    ("malacca_shahbandar_seal", "Seal of the Malacca Shahbandar", "southeast_asia", ("straits","mercantile"), "ring", 96, "legendary", (1450,1511), ("relic_merchant",), {"trade":32,"diplomacy":16}, {"controllers":("malacca_sultanate",),"settlements":("malacca",),"evidence":("sea_monsoon_world",)}),
    ("le_loi_thuan_thien_sword", "Thuận Thiên Sword Tradition", "southeast_asia", ("dai_viet","court"), "primary", 112, "relic", (1450,1820), (), {"meleePower":35,"morale":28}, {"quest":("southeast_asia_phase8_polity",),"evidence":("southeast_arms",)}),
    ("bayinnaung_white_parasol", "White Parasol of Bayinnaung", "southeast_asia", ("burma","court"), "trinket", 126, "relic", (1550,1581), ("relic_merchant",), {"command":38,"diplomacy":20}, {"controllers":("toungoo_principality",),"events":("toungoo_unification_pressure",),"evidence":("southeast_arms",)}),
    ("gowa_royal_chainshirt", "Royal Chainshirt of Gowa", "southeast_asia", ("sulawesi","military"), "chest", 103, "legendary", (1600,1700), ("relic_merchant",), {"armor":31,"boarding":15}, {"controllers":("makassar_polities",),"events":("batavia_commercial_pressure",),"evidence":("sea_monsoon_world",)}),
    ("lapulapu_kampilan", "Kampilan of Mactan", "southeast_asia", ("philippines","military"), "primary", 101, "legendary", (1521,1820), (), {"meleePower":33,"reefMobility":16}, {"quest":("southeast_strait_accord",),"evidence":("southeast_arms",)}),
    ("zheng_he_navigation_tablet", "Navigation Tablet of Zheng He's Fleets", "east_asia", ("china","maritime"), "trinket", 118, "relic", (1450,1820), (), {"navigation":38,"diplomacy":18}, {"quest":("east_asia_coastal_record",),"evidence":("china_material","ming_trade")}),
    ("qi_jiguang_jixiao_xinshu", "Qi Jiguang's Jixiao Xinshu", "east_asia", ("china","military"), "trinket", 121, "relic", (1560,1820), ("relic_merchant",), {"command":34,"training":24}, {"controllers":("ming_empire",),"events":("ming_coastal_trade_pressure",),"evidence":("ming_trade",)}),
    ("yi_sunsin_war_diary", "War Diary of Yi Sun-sin", "east_asia", ("korea","maritime"), "trinket", 132, "relic", (1598,1820), (), {"command":39,"navalGunnery":26}, {"quest":("east_asia_phase8_polity",),"events":("imjin_war_pressure",),"evidence":("korea_material",)}),
    ("tokugawa_battle_standard", "Tokugawa Battle Standard", "east_asia", ("japan","court"), "trinket", 127, "relic", (1600,1820), ("relic_merchant",), {"command":40,"morale":25}, {"controllers":("ashikaga_shogunate",),"events":("tokugawa_settlement_pressure",),"evidence":("japan_warfare",)}),
    ("xu_guangqi_agricultural_treatise", "Xu Guangqi's Agricultural Treatise", "east_asia", ("china","scholarly"), "trinket", 116, "legendary", (1639,1820), (), {"learning":35,"agriculture":25}, {"quest":("xu_guangqi_personal_quest",),"technology":("experimental_method",),"evidence":("china_material",)}),
    ("kangxi_court_compass", "Kangxi Court Survey Compass", "east_asia", ("china","scholarly"), "trinket", 145, "relic", (1680,1820), ("relic_merchant",), {"survey":40,"navigation":28}, {"events":("qing_transition_pressure",),"technology":("cadastral_survey","experimental_method"),"evidence":("china_material",)}),
    ("tupaia_chart", "Tupaia's Chart", "pacific", ("polynesia","exploration"), "trinket", 138, "relic", (1769,1820), (), {"navigation":46,"diplomacy":22}, {"quest":("pacific_stars_between_islands",),"evidence":("contact_pacific","pacific_navigation")}),
    ("kamehameha_feather_cloak", "Feather Cloak of Kamehameha", "pacific", ("hawaii","court"), "chest", 148, "relic", (1790,1820), (), {"authority":45,"armor":18}, {"quest":("kamehameha_i_personal_quest",),"events":("polynesian_unification_pressure",),"evidence":("polynesian_societies",)}),
    ("kaahumanu_council_fan", "Council Fan of Kaʻahumanu", "pacific", ("hawaii","court"), "offhand", 142, "legendary", (1800,1820), ("relic_merchant",), {"diplomacy":40,"authority":24}, {"controllers":("hawaii_chiefdom",),"events":("polynesian_unification_pressure",),"evidence":("polynesian_societies",)}),
    ("maori_te_whiti_cloak", "Chiefly Cloak of Te Pahi", "pacific", ("aotearoa","diplomatic"), "chest", 119, "legendary", (1793,1820), (), {"diplomacy":35,"coldResistance":15}, {"quest":("pacific_phase8_polity",),"evidence":("contact_pacific",)}),
    ("pohnpei_nan_madol_shell", "Nan Madol Ceremonial Shell", "pacific", ("micronesia","ceremonial"), "ring", 91, "legendary", (1450,1628), ("relic_merchant",), {"ritualAuthority":30,"navigation":12}, {"controllers":("saudeleur_dynasty",),"settlements":("nan_madol",),"evidence":("pacific_material",)}),
    ("rapa_nui_ao_staff", "Rapa Nui Ao Staff", "pacific", ("rapa_nui","ceremonial"), "offhand", 99, "legendary", (1450,1820), ("relic_merchant",), {"authority":32,"resourceStewardship":14}, {"controllers":("rapa_nui_clans",),"events":("rapa_nui_resource_pressure",),"evidence":("pacific_material",)}),
]


def expand():
    data = json.loads(CATALOG.read_text())
    existing_effects = {x["id"] for x in data["effects"]}
    data["effects"].extend({"id": ident, "kind": kind} for ident, kind in EFFECTS.items() if ident not in existing_effects)
    existing_evidence = {x["id"] for x in data["historicalEvidence"]}
    data["historicalEvidence"].extend({"id": i, "citation": c, "note": n} for i,c,n in EVIDENCE if i not in existing_evidence)

    created = []
    sets = []
    region_evidence = {"southeast_asia": ("sea_monsoon_world",), "east_asia": ("china_material",), "pacific": ("pacific_material",)}
    for set_id, set_name, region, subregions, set_effect, pieces in SET_SPECS:
        ids = []
        for ident, name, slot, level, rarity, stats in pieces:
            ids.append(ident)
            years = (1735, 1820) if set_id == "pacific_survey_set" else ((1500, 1820) if set_id == "sengoku_retainer_set" else (1450, 1820))
            technology = ("systematic_natural_history",) if set_id == "pacific_survey_set" else ()
            created.append(item(ident, name, region, subregions, "equipment", slot, level, rarity,
                                "set_piece", years, ("armourer","outfitter","military_supplier") if slot in {"head","chest","gloves","boots"} else ("general_merchant","relic_merchant","ship_chandler"),
                                stats, set_id=set_id, effects=(set_effect,), evidence=region_evidence[region],
                                technology=technology, trade=set_id == "pacific_survey_set"))
        sets.append({"id": set_id, "name": set_name, "itemTypeIds": ids,
                     "thresholds": [{"pieceCount": 2, "effectIds": [set_effect]},
                                    {"pieceCount": 3, "effectIds": ["artisan_precision" if region != "pacific" else "storm_reading"]},
                                    {"pieceCount": 4, "effectIds": [set_effect, "court_audience" if region != "pacific" else "island_wayfinding"]}]})
    for values in ORDINARY:
        ident,name,region,subs,category,slot,level,rarity,kind,years,merchants,stats,opts = values
        clean = dict(opts); ev = clean.pop("evidence", region_evidence[region])
        created.append(item(ident,name,region,subs,category,slot,level,rarity,kind,years,merchants,stats,evidence=ev,**clean))
    for ident,name,region,subs,slot,level,rarity,years,merchants,stats,opts in UNIQUES:
        clean=dict(opts); ev=clean.pop("evidence")
        created.append(item(ident,name,region,subs,"artifact",slot,level,rarity,"historical",years,merchants,stats,
                            unique=True,evidence=ev,historical_class="named_historical",price=level*70,**clean))

    generated_set_ids={x["id"] for x in sets}
    data["equipmentSets"]=[x for x in data["equipmentSets"] if x["id"] not in generated_set_ids] + sets
    generated_item_ids={x["id"] for x in created}
    data["items"]=[x for x in data["items"] if x["id"] not in generated_item_ids] + created
    CATALOG.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    expand()

#!/usr/bin/env python3
"""Deterministically author the release-scale Phase 8 progression catalogue.

The resulting JSON is authoritative.  Keeping this recipe makes the large data
pass reviewable and reproducible without making runtime content procedural.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scenario/progression/catalog.json"

# id, player-facing name, preferred year.  These are deliberately recognizable
# capabilities rather than numerical filler; every node exposes a stable hook.
ADDITIONS = {
 "military": [("arquebus_volley_drill","Arquebus Volley Drill",1490),("field_entrenchment","Field Entrenchment",1525),("regimental_organization","Regimental Organization",1570),("countermarch_fire","Countermarch Fire",1600),("bayonet_system","Socket Bayonet System",1690),("officer_academies","Officer Academies",1715),("horse_artillery","Horse Artillery",1775),("skirmisher_doctrine","Skirmisher Doctrine",1785),("general_staff_methods","General Staff Methods",1805),("rifled_infantry_trials","Rifled Infantry Trials",1815),("reserve_mobilization","Reserve Mobilization",1818),("combined_arms_columns","Combined-arms Columns",1800)],
 "naval": [("carvel_hull_construction","Carvel Hull Construction",1460),("lateen_square_rig","Composite Sailing Rigs",1490),("shipboard_artillery_decks","Shipboard Artillery Decks",1520),("naval_signal_books","Naval Signal Books",1580),("copper_sheathing","Copper Sheathing",1760),("careening_stations","Overseas Careening Stations",1600),("fleet_victualling","Fleet Victualling",1640),("naval_hospitals","Naval Hospitals",1700),("rated_warships","Rated Warship System",1720),("carronade_batteries","Carronade Batteries",1780)],
 "commercial": [("merchant_correspondence","Merchant Correspondence",1460),("warehouse_warrants","Warehouse Warrants",1510),("consular_trade_networks","Consular Trade Networks",1540),("auction_markets","Auction Markets",1580),("central_banking","Central Banking",1695),("commercial_statistics","Commercial Statistics",1740),("canal_tolls_finance","Canal Finance",1750),("brokerage_houses","Brokerage Houses",1710),("manufacturing_credit","Manufacturing Credit",1770),("global_price_bulletins","Global Price Bulletins",1800),("savings_banks","Savings Banks",1810)],
 "administrative": [("chancery_archives","Chancery Archives",1470),("trained_magistracy","Trained Magistracy",1520),("fiscal_cadastres","Fiscal Cadastres",1550),("provincial_audits","Provincial Audits",1600),("civil_service_examinations","Civil Service Examinations",1650),("population_census","Population Census",1700),("municipal_charters","Municipal Charters",1725),("codified_law","Codified Law",1760),("ministerial_cabinets","Ministerial Cabinets",1780),("merit_civil_service","Merit Civil Service",1800),("national_accounts","National Accounts",1815)],
 "scientific": [("printed_observation_tables","Printed Observation Tables",1490),("surveying_instruments","Surveying Instruments",1520),("microscopy","Microscopy",1665),("barometric_measurement","Barometric Measurement",1640),("calculus_methods","Calculus Methods",1685),("electrical_experimentation","Electrical Experimentation",1745),("chemical_classification","Chemical Classification",1770),("geological_survey","Geological Survey",1790),("metric_metrology","Metric Metrology",1795),("comparative_linguistics","Comparative Linguistics",1800),("electromagnetic_experiment","Electromagnetic Experiment",1820),("probability_statistics","Probability and Statistics",1710)],
 "agricultural": [("terrace_conservation","Terrace Conservation",1460),("regional_seed_exchange","Regional Seed Exchange",1490),("market_gardening","Market Gardening",1550),("drainage_reclamation","Drainage and Reclamation",1600),("fodder_crop_systems","Fodder Crop Systems",1650),("plantation_processing","Plantation Processing",1670),("seed_drill","Seed Drill",1701),("veterinary_husbandry","Veterinary Husbandry",1740),("soil_chemistry","Soil Chemistry",1800),("iron_ploughs","Iron Ploughs",1780)],
 "industrial": [("blast_furnace_practice","Blast Furnace Practice",1500),("wire_drawing_mills","Wire-drawing Mills",1520),("deep_mine_drainage","Deep-mine Drainage",1600),("boring_mills","Precision Boring Mills",1750),("puddling_iron","Puddling Iron",1784),("machine_tools","Machine Tools",1795),("interchangeable_parts","Interchangeable Parts",1800),("gas_lighting","Gas Lighting",1805),("high_pressure_steam","High-pressure Steam",1800),("mechanized_paper_making","Mechanized Papermaking",1803),("steam_hammer_concepts","Steam Hammer Concepts",1818)],
 "logistical": [("pack_train_contracts","Pack-train Contracts",1450),("military_magazines","Military Magazines",1510),("road_waystations","Road Waystations",1540),("river_transport_bureaus","River Transport Bureaus",1580),("standard_supply_weights","Standard Supply Weights",1620),("contract_victualling","Contract Victualling",1660),("campaign_bakeries","Campaign Bakeries",1700),("artillery_train","Artillery Train",1730),("turnpike_networks","Turnpike Networks",1750),("canal_logistics","Canal Logistics",1770),("quartermaster_corps","Quartermaster Corps",1790),("preserved_rations","Preserved Rations",1809),("steam_towage","Steam Towage",1817),("strategic_depots","Strategic Depots",1820)],
 "exploration": [("pilot_books","Pilot Books",1450),("coastal_triangulation","Coastal Triangulation",1480),("trade_wind_routes","Trade-wind Routes",1500),("monsoon_route_almanacs","Monsoon Route Almanacs",1520),("overland_caravan_surveys","Caravan Route Surveys",1550),("botanical_collecting","Botanical Collecting",1600),("longitude_lunar_distance","Lunar-distance Navigation",1675),("polar_navigation","Polar Navigation",1700),("geodetic_arcs","Geodetic Arc Surveys",1735),("pacific_charting","Pacific Charting",1760),("global_hydrography","Global Hydrography",1790),("expeditionary_ethnography","Expeditionary Ethnography",1800),("deep_sea_sounding","Deep-sea Sounding",1810),("continental_interiors","Continental Interior Surveys",1820)],
 "medical": [("quarantine_practice","Quarantine Practice",1450),("herbal_pharmacopoeia","Comparative Pharmacopoeia",1490),("surgical_anatomy","Surgical Anatomy",1540),("military_field_hospitals","Military Field Hospitals",1580),("civic_pest_hospitals","Civic Pest Hospitals",1650),("smallpox_inoculation","Smallpox Inoculation",1720),("obstetric_training","Obstetric Training",1740),("clinical_case_records","Clinical Case Records",1750),("naval_scurvy_prevention","Scurvy Prevention",1755),("vaccination","Vaccination",1796),("pathological_anatomy","Pathological Anatomy",1800),("emergency_triage","Emergency Triage",1810),("public_mortality_statistics","Mortality Statistics",1815)],
 "communications": [("courier_relays","Courier Relays",1450),("ciphered_dispatches","Ciphered Dispatches",1480),("printed_broadsheets","Printed Broadsheets",1520),("semaphore_signals","Semaphore Signals",1600),("scheduled_post","Scheduled Post",1650),("newspaper_exchanges","Newspaper Exchanges",1700),("signal_intelligence_bureaus","Signal Intelligence Bureaus",1760),("optical_telegraph","Optical Telegraph",1792),("naval_flag_signals","Standard Naval Flag Signals",1799),("lithographic_printing","Lithographic Printing",1800),("mass_postal_service","Mass Postal Service",1810),("field_signal_corps","Field Signal Corps",1815),("electrical_telegraph_concepts","Electrical Telegraph Concepts",1820)],
}

INSTITUTIONS = [
 ("merchant_diasporas","Merchant Diaspora Networks",1450,["commercial"]),("chartered_municipalities","Chartered Municipal Government",1480,["administrative"]),("artillery_offices","Permanent Artillery Offices",1520,["military"]),("royal_dockyards","Royal Dockyard System",1540,["naval"]),("commercial_courts_institution","Commercial Courts",1560,["commercial"]),("colonial_councils","Overseas Colonial Councils",1600,["administrative","exploration"]),("standing_army_establishment","Standing Army Establishment",1660,["military"]),("central_bank_institution","Central Bank",1694,["commercial"]),("agricultural_societies","Agricultural Societies",1720,["agricultural","scientific"]),("professional_medical_colleges","Professional Medical Colleges",1730,["medical"]),("patent_offices","Patent Offices",1750,["industrial","scientific"]),("abolitionist_public_sphere","Abolitionist Public Sphere",1770,["institutional"]),("representative_assemblies","Representative Assemblies",1776,["administrative"]),("metric_standardization","Metric Standardization",1795,["scientific","commercial"]),("mass_education","Mass Education",1800,["communications"]),("professional_civil_service","Professional Civil Service",1810,["administrative"]),
]

DESCRIPTIONS = {
 "military":"Improves battlefield organization, equipment, and command through {name}.", "naval":"Makes fleets safer and more effective through {name}.",
 "commercial":"Extends trustworthy exchange and market coordination through {name}.", "administrative":"Makes durable government records and decisions possible through {name}.",
 "scientific":"Turns repeatable observation into usable knowledge through {name}.", "agricultural":"Raises resilient food and commodity production through {name}.",
 "industrial":"Expands reproducible workshop and manufacturing capacity through {name}.", "logistical":"Sustains armies, cities, and routes through {name}.",
 "exploration":"Reduces uncertainty on distant routes through {name}.", "medical":"Protects crews, armies, and settlements through {name}.",
 "communications":"Carries authoritative news and orders through {name}."
}

def main():
 data=json.loads(PATH.read_text())
 tech_ids={x["id"] for x in data["technologies"]}; inst_ids={x["id"] for x in data["institutions"]}
 branches={x["id"]:x for x in data["branches"]}
 for branch, rows in ADDITIONS.items():
  if branch not in branches:
   entry=rows[0][0]; data["branches"].append({"id":branch,"name":branch.title(),"entryNodeIds":[entry]}); branches[branch]=data["branches"][-1]
  previous=branches[branch]["entryNodeIds"][0]
  for index,(ident,name,year) in enumerate(rows):
   if ident in tech_ids: previous=ident; continue
   prereqs=[] if ident in branches[branch]["entryNodeIds"] else [previous]
   # Periodic cross-tree links give alternate-history transfer real dependencies
   # while retaining more than one route through every broad field.
   if index and index % 4 == 0:
    candidates=[x for x in data["technologies"] if x["branchId"]!=branch and x["preferredYear"]<=year-10]
    if candidates: prereqs.append(max(candidates,key=lambda x:(x["preferredYear"],x["id"]))["id"])
   hook=f"progression_{ident}"
   data["unlockReferences"].append({"kind":"modifier","id":hook})
   data["technologies"].append({"id":ident,"name":name,"description":DESCRIPTIONS[branch].format(name=name.lower()),"branchId":branch,"prerequisiteIds":prereqs,"preferredYear":year,"baseCost":round(75+(year-1450)*0.82+index*4),"unlocks":[["modifier",hook]],"origin":{"regionIds":["global_exchange"],"note":"Multiple polities may develop or transfer this capability."},"evidenceIds":[f"{branch}_survey"]})
   tech_ids.add(ident); previous=ident
 for ident,name,year,fields in INSTITUTIONS:
  if ident in inst_ids: continue
  prereq=next((x[0] for f in fields for x in ADDITIONS.get(f,[]) if x[2]<=year),"professional_bureaucracy")
  hook=f"progression_{ident}"; data["unlockReferences"].append({"kind":"policy","id":hook})
  regions=["western_europe"] if year>1650 else ["western_europe","middle_east_india","east_asia"]
  data["institutions"].append({"id":ident,"name":name,"description":f"Durable organizations spread {name.lower()} unevenly through political, urban, and trade networks.","branchId":"institutional","prerequisiteIds":[prereq],"preferredYear":year,"baseCost":round(100+(year-1450)*.75),"unlocks":[["policy",hook]],"origin":{"year":year,"regionIds":regions},"adoptionRequirements":{"minimumUrbanization":10+min(20,(year-1450)//25),"requiredNodeIds":[prereq]},"diffusion":{"baseRate":.2+(year%3)*.05,"adjacentRate":.25,"tradeRate":.35+(year%4)*.05,"isolationMultiplier":.1},"evidenceIds":["institutional_survey"]})
  inst_ids.add(ident)
 evidence={x["id"] for x in data["historicalEvidence"]}
 for branch in ADDITIONS:
  ident=f"{branch}_survey"
  if ident not in evidence: data["historicalEvidence"].append({"id":ident,"citation":"Cambridge Histories and specialist global histories of technology, science, war, medicine, and trade, 1450–1820.","note":f"Supports the broad chronology and transferable {branch} capabilities; preferred years model normal cost, not invention locks."})
 if "institutional_survey" not in evidence: data["historicalEvidence"].append({"id":"institutional_survey","citation":"The Cambridge History of the World, volumes 6–7; comparative institutional histories.","note":"Supports plural origins and uneven adoption of durable reforms and organizations."})
 # Bring the original compact catalogue under the same release-scale evidence and
 # consumer contract without changing any stable node IDs or prerequisites.
 refs={(x["kind"],x["id"]) for x in data["unlockReferences"]}
 for node in data["technologies"]:
  node.setdefault("evidenceIds",[f"{node['branchId']}_survey"])
  if not node["unlocks"]:
   hook=f"progression_{node['id']}"; node["unlocks"]=[["modifier",hook]]
   if ("modifier",hook) not in refs: data["unlockReferences"].append({"kind":"modifier","id":hook}); refs.add(("modifier",hook))
 for node in data["institutions"]:
  node.setdefault("evidenceIds",["institutional_survey"])
  if not node["unlocks"]:
   hook=f"progression_{node['id']}"; node["unlocks"]=[["policy",hook]]
   if ("policy",hook) not in refs: data["unlockReferences"].append({"kind":"policy","id":hook}); refs.add(("policy",hook))
 # Deterministic canonical order keeps hand-authored original IDs stable.
 seen=set(); data["unlockReferences"]=[x for x in data["unlockReferences"] if not (tuple(x.values()) in seen or seen.add(tuple(x.values())))]
 PATH.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")

if __name__ == "__main__": main()

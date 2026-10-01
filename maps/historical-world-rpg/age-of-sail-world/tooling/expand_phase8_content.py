#!/usr/bin/env python3
"""One-time deterministic Phase 8 expansion of authored quest/treasure data.

The expanded JSON remains the scenario authority; this recipe documents the
content pass and is idempotent so maintainers can reproduce it.
"""
from __future__ import annotations

import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUESTS = ROOT / "scenario/campaign-quests.json"
TREASURES = ROOT / "scenario/treasures/age-of-sail.json"

REGIONS = {
    "europe": ("venice", "florence", "venice", "leonardo_da_vinci", "double_entry_bookkeeping", "reformation_pressure", "Adriatic Ledgers"),
    "africa": ("kilwa", "mombasa", "songhai_kingdom", "nzinga_mbande", "irrigation_hydraulics", "west_african_trade_reorientation", "Gold and Monsoon"),
    "middle_east_india": ("aden", "goa", "ottoman_empire", "piri_reis", "celestial_navigation", "indian_ocean_route_pressure", "Pilots of Two Seas"),
    "southeast_asia": ("ayutthaya", "malacca", "ayutthaya_kingdom", "hang_tuah", "naval_gunnery", "toungoo_unification_pressure", "Letters of the Strait"),
    "east_asia": ("quanzhou", "beijing", "ming_empire", "xu_guangqi", "experimental_method", "qing_transition_pressure", "Measure of the Coast"),
    "americas_caribbean": ("tenochtitlan", "cusco", "mexica_tenochtitlan", "malintzin", "new_world_crops", "mexica_succession_crisis", "Two Highland Roads"),
    "pacific": ("samoa_fono", "hawaii_royal_center", "hawaii_chiefdom", "kamehameha_i", "oceanic_seamanship", "polynesian_unification_pressure", "Council of Wayfinders"),
}


def objective(oid, text, kind, ref, guidance=None, event=None):
    value = {"id": oid, "text": text, "kind": kind, "refs": [list(ref)]}
    if guidance: value["guidance"] = guidance
    if event: value["eventId"] = event
    return value


def phase8_quests():
    result = []
    for region, (home, destination, polity, character, technology, event, title) in REGIONS.items():
        guide = {"precision": "exact", "regionId": region, "settlementId": destination}
        result.append({
            "id": f"{region}_phase8_polity".replace("middle_east_india", "india").replace("americas_caribbean", "americas"),
            "region": region, "chainKind": "regional", "title": title,
            "summary": "A regional dispute joins civic authority, commerce, learned practice, and a changing political settlement.",
            "giver": ["settlement", home], "turnIn": ["settlement", home],
            "stages": [
                {"id": "hear_petition", "title": "A Public Petition", "objectives": [objective("record_pressure", "Record the historical pressure shaping the petition.", "historical_event", ("polity", polity), event=event)], "next": ["civic_terms", "practical_terms"]},
                {"id": "civic_terms", "title": "Terms of Office", "objectives": [objective("secure_authority", "Reach terms with the current polity authority.", "diplomacy", ("polity", polity))], "next": ["deliver_terms"]},
                {"id": "practical_terms", "title": "A Practical Answer", "objectives": [objective("apply_knowledge", "Apply relevant technical knowledge to an alternate settlement.", "technology", ("technology", technology))], "next": ["deliver_terms"]},
                {"id": "deliver_terms", "title": "Carry the Settlement", "objectives": [objective("reach_destination", "Deliver the agreed terms without assuming unchanged control.", "travel", ("settlement", destination), guide)], "next": ["return_home"]},
                {"id": "return_home", "title": "Close the Record", "objectives": [objective("report_home", "Return the result to the petitioners.", "settlement", ("settlement", home), {"precision": "exact", "regionId": region, "settlementId": home, "purpose": "return_to_giver"})], "next": []},
            ],
            "rewards": [{"id": f"{region}_polity_regard", "adapter": "diplomacy", "effect": "adjust_relations", "refs": [["polity", polity]]}, {"id": f"{region}_market_credit", "adapter": "economy", "effect": "adjust_market", "refs": [["settlement", home]]}],
            "divergences": ["changed_control_uses_successor_authority", "refusal_uses_technical_path", "blocked_route_pauses_delivery"]})
        result.append({
            "id": f"{character}_personal_quest", "region": region, "chainKind": "personal", "title": f"{title}: A Personal Reckoning",
            "summary": "A recruitable companion weighs private obligations against service, office, and the player's trust.",
            "giver": ["character", character], "turnIn": ["settlement", home],
            "stages": [
                {"id": "confidence", "title": "A Confidence", "objectives": [objective("hear_companion", "Earn the companion's confidence.", "character", ("character", character))], "next": ["public_duty", "private_duty"]},
                {"id": "public_duty", "title": "Public Duty", "objectives": [objective("serve_office", "Use the companion's office to negotiate a durable answer.", "diplomacy", ("polity", polity))], "next": ["reckoning"]},
                {"id": "private_duty", "title": "Private Duty", "objectives": [objective("protect_home", "Protect the companion's personal obligation at home.", "settlement", ("settlement", home), {"precision": "exact", "regionId": region, "settlementId": home})], "next": ["reckoning"]},
                {"id": "reckoning", "title": "The Reckoning", "objectives": [objective("settle_loyalty", "Let the companion judge the chosen outcome.", "character", ("character", character))], "next": []},
            ],
            "rewards": [{"id": f"{character}_loyalty", "adapter": "character", "effect": "adjust_relationship", "refs": [["character", character]]}, {"id": f"{character}_office", "adapter": "title", "effect": "grant_title", "refs": [["polity", polity]]}],
            "divergences": ["public_path_favors_office", "private_path_favors_relationship", "changed_allegiance_preserves_personal_resolution"]})
    result.extend([
        {"id":"monsoon_breadcrumbs","region":"global","chainKind":"cross_region","title":"Monsoon Breadcrumbs","summary":"Follow merchant testimony from East Africa through India to Southeast Asia without revealing ports before their clues are earned.","giver":["settlement","mombasa"],"turnIn":["settlement","malacca"],"prerequisiteQuestIds":["africa_phase8_polity"],"stages":[{"id":"african_testimony","title":"The African Testimony","objectives":[objective("trade_mombasa","Compare cargo testimony at Mombasa.","trade",("settlement","mombasa"),{"precision":"exact","regionId":"africa","settlementId":"mombasa"})],"next":["monsoon_search"]},{"id":"monsoon_search","title":"Across the Monsoon","objectives":[objective("search_indian_ocean","Follow broad monsoon bearings.","discovery",("navigation_zone","arabian_sea_navigation"),{"precision":"region","regionId":"middle_east_india"})],"next":["malacca_account"]},{"id":"malacca_account","title":"The Eastern Account","objectives":[objective("turn_in_malacca","Deliver the reconciled account at Malacca.","settlement",("settlement","malacca"),{"precision":"exact","regionId":"southeast_asia","settlementId":"malacca","purpose":"turn_in"})],"next":[]}],"rewards":[{"id":"monsoon_route","adapter":"discovery","effect":"reveal_route","refs":[["navigation_zone","node_malacca_sea"]]}],"divergences":["unknown_transitions_never_appear_as_breadcrumbs","blocked_route_pauses_chain","changed_control_uses_civic_archive"]},
        {"id":"licensed_salvage","region":"global","chainKind":"repeatable","title":"Licensed Salvage","summary":"A bounded repeatable commission directs recovery from known wreck waters; each campaign resolution remains authoritative.","giver":["settlement","lisbon"],"turnIn":["settlement","lisbon"],"stages":[{"id":"take_contract","title":"Take a Contract","objectives":[objective("record_contract","Record a salvage contract at a known port.","institution",("institution","naval_administration"))],"next":["recover_cargo"]},{"id":"recover_cargo","title":"Recover Cargo","objectives":[objective("search_known_waters","Search only the contracted navigation region.","discovery",("navigation_zone","iberian_atlantic"),{"precision":"approximate","regionId":"europe","searchAreas":[{"x":18,"y":66,"radius":16}]})],"next":["account_salvage"]},{"id":"account_salvage","title":"Account for Salvage","objectives":[objective("return_contract","Return to the licensing office.","settlement",("settlement","lisbon"),{"precision":"exact","regionId":"europe","settlementId":"lisbon","purpose":"turn_in"})],"next":[]}],"rewards":[{"id":"salvage_pay","adapter":"economy","effect":"adjust_treasury","refs":[["polity","portugal"]]}],"divergences":["repeat_limit_is_authoritative","resolved_site_never_rerolls","depleted_sites_are_not_reissued"]}
    ])
    return result


def expand_quests():
    data = json.loads(QUESTS.read_text())
    existing = {q["id"] for q in data["quests"]}
    data["quests"].extend(q for q in phase8_quests() if q["id"] not in existing)
    personal_homes = {f"{values[3]}_personal_quest": values[0] for values in REGIONS.values()}
    for quest in data["quests"]:
        if quest["id"] in personal_homes:
            quest["turnIn"] = ["settlement", personal_homes[quest["id"]]]
    data["coverageTargets"].update({"minimumRegionalChains": 14, "minimumPersonalChains": 7, "minimumCrossRegionChains": 1, "minimumRepeatableChains": 1})
    QUESTS.write_text(json.dumps(data, indent=2) + "\n")


def expand_treasures():
    data = json.loads(TREASURES.read_text())
    candidates, treasures = {x["id"] for x in data["candidateLocations"]}, {x["id"] for x in data["treasures"]}
    for index, region in enumerate(REGIONS):
        regional_template = next(x for x in data["candidateLocations"] if x["regionId"] == region and not x["id"].startswith(f"cand_{region}_"))
        for variant, family in (("cache", "hidden_store"), ("wreck", "wreck_site"), ("ruin", "ruined_waystation")):
            cid = f"cand_{region}_{variant}"; tid = f"secret_{region}_{variant}"
            if cid not in candidates:
                candidate = copy.deepcopy(regional_template)
                candidate.update({"id":cid,"locationFamily":family,"position":{"x":12+index*9+len(variant),"y":20+index*7+len(family)%11},"searchAreas":{"approximate":{"center":{"x":20+index*8,"y":25+index*6},"radius":18},"narrowed":{"center":{"x":12+index*9+len(variant),"y":20+index*7+len(family)%11},"radius":6}},"accessible":True,"clearance":4,"inactiveRegionPolicy":"resolve_and_defer_spawn","weight":2})
                data["candidateLocations"].append(candidate)
            else:
                candidate = next(x for x in data["candidateLocations"] if x["id"] == cid)
                for field in ("regionalInstanceId", "physicalMapId", "terrainId", "navigationZoneId"):
                    candidate[field] = regional_template[field]
            if tid not in treasures:
                data["treasures"].append({"id":tid,"name":f"{region.replace('_',' ').title()} {variant.title()}","kind":"generic","candidateLocationIds":[cid],"rewardPoolId":"generic_cache_rewards","guardIds":["local_watch","rival_salvagers"],"hazardIds":["unstable_ruins"] if variant != "wreck" else ["reef_and_surf"],"encounterIds":["careful_recovery","contested_salvage"],"clueIds":["clue_region","clue_approximate","clue_narrowed","clue_exact"],"collectionPolicy":"repeatable" if variant == "cache" else "deplete",**({"repeatLimit":3} if variant == "cache" else {})})
    TREASURES.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    expand_quests(); expand_treasures()

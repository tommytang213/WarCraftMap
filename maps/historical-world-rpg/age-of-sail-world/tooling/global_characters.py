#!/usr/bin/env python3
"""Validate and deterministically project the authoritative global character roster."""
import argparse
import copy
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scenario/characters/global.json"
PHASE8_SOURCE = ROOT / "scenario/characters/phase8.json"
RELEASE_SCALE_SOURCE = ROOT / "scenario/characters/release-scale.json"
WORLD = ROOT / "scenario/world/world.json"
REPORT = ROOT / "scenario/characters/reports/coverage.json"
ROSTERS = ROOT / "scenario/rosters"
ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
REGIONS = {"europe", "africa", "middle_east_india", "southeast_asia", "east_asia", "americas_caribbean", "pacific"}
ROLES = {"sovereign", "commander", "admiral", "explorer", "navigator", "diplomat", "engineer", "scholar", "merchant", "adviser", "governor"}
OFFICE_ROLES = {"sovereign", "settlement_administrator", "province_governor", "army_commander", "fleet_commander"}


class CharacterRosterError(ValueError): pass


def load_source():
    """Compose the split authoritative catalogues without duplicating identities."""
    source=json.loads(SOURCE.read_text()); expansion=json.loads(PHASE8_SOURCE.read_text())
    extensions={x["id"]:x for x in expansion["characterExtensions"]}
    quest_aliases={
        "quest_nzinga_independence":"quest_nzinga_diplomatic_web", "quest_piri_kitab_bahriye":"quest_piri_reis_kitab",
        "quest_krishnadevaraya_raichur":"quest_krishna_rayalaseema", "quest_hang_tuah_laksamana":"quest_hang_tuah_melaka",
        "quest_hasanuddin_eastern_trade":"quest_hasanuddin_eastern_seas", "quest_yi_restore_fleet":"quest_yi_turtle_fleet",
        "quest_xu_agricultural_treatise":"quest_xu_calendar", "quest_malintzin_many_words":"quest_malintzin_words",
        "quest_tupac_amaru_rebellion":"quest_tupac_amaru_corregidor", "quest_tupaia_island_chart":"quest_tupaia_star_paths"}
    for character in source["characters"]:
        extra=extensions.pop(character["id"],None)
        if extra is None: raise CharacterRosterError(f"character {character['id']}: missing Phase 8 role metadata")
        character.update({k:v for k,v in extra.items() if k!="id"})
        character["questHookIds"]=[quest_aliases.get(x,x) for x in character["questHookIds"]]
    if extensions: raise CharacterRosterError(f"unknown character extensions: {sorted(extensions)}")
    source["characters"].extend(expansion["characters"])
    source["characterTitles"].update(expansion["characterTitles"])
    source["personalQuests"]=expansion["personalQuests"]
    source["historicalEvidence"].extend(expansion["historicalEvidence"])
    source["companionRelationships"].extend(expansion.get("companionRelationships",[]))
    source["characterTransitionPolicy"]=expansion["characterTransitionPolicy"]
    # Compact authored records contain identity/career evidence; shared mechanical
    # defaults are expanded here so catalogue scale does not duplicate boilerplate.
    release=json.loads(RELEASE_SCALE_SOURCE.read_text())
    exemplars={r:next(x for x in source["characters"] if x["regionId"]==r) for r in REGIONS}
    evidence_alias={"americas_caribbean":"americas"}
    evidence_by_region={r:next(x for x in source["historicalEvidence"] if x["id"]==f"evidence_{evidence_alias.get(r,r)}") for r in REGIONS}
    for seed in release["characters"]:
        base=copy.deepcopy(exemplars[seed["regionId"]]); ident=seed["id"]
        base.update({"id":ident,"displayName":seed["displayName"],"biography":seed["biography"],
            "availabilityWindow":{"startDate":f"{seed['careerStart']}-01-01","endDate":f"{seed['careerEnd']}-12-31"},
            "roleIds":seed["roleIds"],"authoredHistorical":True,
            "historicalEvidenceIds":[evidence_by_region[seed["regionId"]]["id"]],
            "questHookIds":[f"quest_{ident}_legacy"],"eventHookIds":[],"technologyHookIds":[],"discoveryHookIds":[],
            "officeEligibility":(["province_governor"] if set(seed["roleIds"]) & {"sovereign","governor","adviser"} else []) +
                (["army_commander"] if "commander" in seed["roleIds"] else []) + (["fleet_commander"] if "admiral" in seed["roleIds"] else []),
            "commandEligibility":(["army"] if "commander" in seed["roleIds"] else []) + (["fleet"] if "admiral" in seed["roleIds"] else [])})
        source["characters"].append(base); source["characterTitles"][ident]=seed["title"]
        source["personalQuests"].append({"id":f"quest_{ident}_legacy","title":seed["questTitle"],
            "summary":f"Resolve a defining problem from {seed['displayName']}'s documented career without forcing its historical outcome.",
            "characterId":ident,"objectives":["establish_local_support","complete_role_challenge"],"outcomes":[f"{ident}_legacy_bonus"]})
    return source


def index(values, domain):
    result = {}
    for value in values:
        ident = value.get("id")
        if not isinstance(ident, str) or not ID.fullmatch(ident): raise CharacterRosterError(f"{domain}: invalid ID {ident!r}")
        if ident in result: raise CharacterRosterError(f"{domain}: duplicate ID {ident!r}")
        result[ident] = value
    return result


def validate(source, world, equipment):
    polities=index(world["polities"],"polities"); settlements=index(world["settlements"],"settlements")
    events=index(world["events"],"events"); technologies=index(world["technologies"]+world["institutions"],"research")
    traits=index(source["traits"],"traits"); skills=index(source["skills"],"skills"); professions=index(source["professions"],"professions")
    characters=index(source["characters"],"characters")
    discoveries=index(source.get("discoveries",[]),"discoveries")
    if set(source.get("characterTitles",{})) != set(characters) or any(not x.strip() for x in source["characterTitles"].values()):
        raise CharacterRosterError("every character requires one English historical title")
    if set(source.get("coverageRegions", ())) != REGIONS or {x["regionId"] for x in characters.values()} != REGIONS:
        raise CharacterRosterError("global region coverage is incomplete")
    if len(characters) < 100 or not all(sum(x["regionId"] == region for x in characters.values()) >= 12 for region in REGIONS):
        raise CharacterRosterError("release scale requires at least 100 characters and twelve per region")
    policy=source.get("characterTransitionPolicy",{})
    if policy != {"historicalWindowsGateInitialAvailability":True,"recruitedCharactersPersistPastWindow":True,
                  "officeVacanciesUseRuntimeSuccession":True,"historicalSuccessorsNotForced":True}:
        raise CharacterRosterError("alternate-history transition policy is missing or unsafe")
    quests=index(source.get("personalQuests", []), "personal quests")
    evidence=index(source.get("historicalEvidence", []), "historical evidence")
    quest_hooks=set(); discovery_hooks=set()
    for ident,value in characters.items():
        start=date.fromisoformat(value["availabilityWindow"]["startDate"]); end=date.fromisoformat(value["availabilityWindow"]["endDate"])
        if start > end or start.year < 1450 or end.year > 1820: raise CharacterRosterError(f"character {ident}: impossible availability window")
        if value["allegiancePolityId"] not in polities: raise CharacterRosterError(f"character {ident}: missing polity")
        if not value.get("locationRules"): raise CharacterRosterError(f"character {ident}: missing location rules")
        priorities=set()
        for rule in value["locationRules"]:
            if rule["locationId"] not in settlements: raise CharacterRosterError(f"character {ident}: broken location {rule['locationId']!r}")
            if rule["priority"] in priorities: raise CharacterRosterError(f"character {ident}: ambiguous location priority")
            priorities.add(rule["priority"])
            validate_conditions(rule.get("conditions",()), ident, polities, settlements, events, technologies)
        validate_conditions(value.get("availabilityConditions",()),ident,polities,settlements,events,technologies)
        for field,catalog in (("traitIds",traits),("professionIds",professions)):
            refs=value[field]
            if len(refs)!=len(set(refs)) or any(x not in catalog for x in refs): raise CharacterRosterError(f"character {ident}: invalid {field}")
        seen=set()
        for rating in value["skills"]:
            sid=rating["skillId"]
            if sid in seen or sid not in skills or not 0 <= rating["rating"] <= 100: raise CharacterRosterError(f"character {ident}: invalid skills")
            seen.add(sid)
        loyalty=value["loyalty"]
        if loyalty["permanentState"] != "none" or not -100 <= loyalty["score"] <= 100 or not 60 <= loyalty["oathboundThreshold"] <= 100:
            raise CharacterRosterError(f"character {ident}: invalid loyalty policy")
        if any(x not in equipment for x in value["equipmentIds"]): raise CharacterRosterError(f"character {ident}: missing equipment reference")
        if any(x not in events for x in value["eventHookIds"]): raise CharacterRosterError(f"character {ident}: missing event hook")
        if any(x not in technologies for x in value["technologyHookIds"]): raise CharacterRosterError(f"character {ident}: missing technology hook")
        if any(x not in discoveries for x in value["discoveryHookIds"]): raise CharacterRosterError(f"character {ident}: missing discovery hook")
        roles=value.get("roleIds", [])
        if not roles or len(roles)!=len(set(roles)) or any(x not in ROLES for x in roles): raise CharacterRosterError(f"character {ident}: invalid gameplay roles")
        offices=value.get("officeEligibility", [])
        if len(offices)!=len(set(offices)) or any(x not in OFFICE_ROLES for x in offices): raise CharacterRosterError(f"character {ident}: invalid office eligibility")
        commands=value.get("commandEligibility", [])
        if len(commands)!=len(set(commands)) or any(x not in {"army","fleet"} for x in commands): raise CharacterRosterError(f"character {ident}: invalid command eligibility")
        if "army" in commands and "army_commander" not in offices or "fleet" in commands and "fleet_commander" not in offices:
            raise CharacterRosterError(f"character {ident}: command eligibility lacks matching office")
        if value.get("authoredHistorical") is not True: raise CharacterRosterError(f"character {ident}: historical identity must be explicit")
        refs=value.get("historicalEvidenceIds", [])
        if not refs or any(x not in evidence for x in refs): raise CharacterRosterError(f"character {ident}: missing historical evidence")
        if not value["questHookIds"]: raise CharacterRosterError(f"character {ident}: personal quest required")
        quest_hooks.update(value["questHookIds"]); discovery_hooks.update(value["discoveryHookIds"])
    if quest_hooks != set(quests): raise CharacterRosterError("personal quest catalogue and character hooks must match")
    for ident, quest in quests.items():
        cid=quest.get("characterId")
        if cid not in characters or ident not in characters[cid]["questHookIds"]: raise CharacterRosterError(f"personal quest {ident}: invalid character link")
        if not quest.get("summary") or not quest.get("objectives") or not quest.get("outcomes"): raise CharacterRosterError(f"personal quest {ident}: incomplete authored content")
    relationships=index(source["companionRelationships"],"relationships"); pairs=set()
    for ident,value in relationships.items():
        pair=frozenset((value["characterAId"],value["characterBId"]))
        if len(pair)!=2 or not pair <= set(characters) or pair in pairs: raise CharacterRosterError(f"relationship {ident}: invalid pair or cycle")
        pairs.add(pair)
    # Relationships are pairwise effects, never prerequisite edges; this also prohibits duplicate/reverse cycles.
    return quest_hooks, discovery_hooks


def validate_conditions(values, character_id, polities, settlements, events, technologies):
    for condition in values:
        kind=condition.get("kind")
        if kind in {"settlement_exists","settlement_rebuilt"} and condition.get("settlementId") not in settlements: raise CharacterRosterError(f"character {character_id}: broken settlement condition")
        if kind=="settlement_controlled_by" and (condition.get("settlementId") not in settlements or condition.get("polityId") not in polities): raise CharacterRosterError(f"character {character_id}: broken control condition")
        if kind=="event" and condition.get("id") not in events: raise CharacterRosterError(f"character {character_id}: broken event condition")
        if kind=="technology" and condition.get("id") not in technologies: raise CharacterRosterError(f"character {character_id}: broken technology condition")
        if kind not in {"settlement_exists","settlement_rebuilt","settlement_controlled_by","event","technology","quest","discovery","region_active","polity_active"}: raise CharacterRosterError(f"character {character_id}: unknown condition {kind!r}")


def equipment_catalog():
    result=set()
    for path in ROSTERS.glob("*.json"):
        result.update(json.loads(path.read_text()).get("equipment",()))
    return result


def projection(source):
    quests=[]; characters=[]
    authored_quests={x["id"]:x for x in source["personalQuests"]}
    for value in source["characters"]:
        for quest_id in value["questHookIds"]:
            quest=authored_quests[quest_id]
            quests.append({"id":quest_id,"title":quest["title"],"summary":quest["summary"],"characterId":value["id"],
                           "objectives":quest["objectives"],"outcomes":quest["outcomes"]})
        characters.append({
            "id":value["id"],"displayName":value["displayName"],"biography":value["biography"],"epithet":source["characterTitles"][value["id"]],
            "traitIds":value["traitIds"],"skills":value["skills"],"professionIds":value["professionIds"],
            "personalQuestIds":value["questHookIds"],"loyalty":{"score":value["loyalty"]["score"],"permanentState":"none"},
            "allegiancePolityId":value["allegiancePolityId"],"available":False,"recruited":False,"active":True,
            "runtimeTemplateId":"companion_hero","recruitmentCosts":value["recruitmentCosts"],"rewardIds":[],"titleGrantIds":value["titleGrantIds"]})
        characters[-1].update({"regionId":value["regionId"],"availabilityWindow":value["availabilityWindow"],
            "roleIds":value["roleIds"],"officeEligibility":value["officeEligibility"],
            "commandEligibility":value["commandEligibility"],"authoredHistorical":True,
            "historicalEvidenceIds":value["historicalEvidenceIds"]})
    return {"traits":source["traits"],"skills":source["skills"],"professions":source["professions"],"personalQuests":quests,
            "characters":characters,"relationshipThresholds":source["relationshipThresholds"],"companionRelationships":source["companionRelationships"]}


def coverage_report(source):
    characters=source["characters"]
    eras={"1450_1499":(1450,1499),"1500_1599":(1500,1599),"1600_1699":(1600,1699),
          "1700_1759":(1700,1759),"1760_1820":(1760,1820)}
    return {"format":"warcraftmap_character_coverage_v1","characterCount":len(characters),
        "personalQuestCount":len(source["personalQuests"]),
        "byRegion":{r:sum(c["regionId"]==r for c in characters) for r in sorted(REGIONS)},
        "byRole":{r:sum(r in c["roleIds"] for c in characters) for r in sorted(ROLES)},
        "byEra":{name:sum(int(c["availabilityWindow"]["startDate"][:4])<=hi and int(c["availabilityWindow"]["endDate"][:4])>=lo for c in characters)
                 for name,(lo,hi) in eras.items()},
        "authoredHistoricalCount":sum(c.get("authoredHistorical") is True for c in characters),
        "generatedMinorOfficialsExcluded":True}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--write",action="store_true"); args=parser.parse_args()
    source=load_source(); world=json.loads(WORLD.read_text()); equipment=equipment_catalog()
    validate(source,world,equipment); expected=projection(source)
    if args.write:
        world.update(copy.deepcopy(expected)); WORLD.write_text(json.dumps(world,indent=2)+"\n")
        REPORT.parent.mkdir(parents=True,exist_ok=True); REPORT.write_text(json.dumps(coverage_report(source),indent=2)+"\n")
    else:
        for key,value in expected.items():
            if world.get(key)!=value: raise CharacterRosterError(f"world projection {key} is stale; run tooling/global_characters.py --write")
    print(f"OK: {len(source['characters'])} recruitable characters across {len(REGIONS)} regions")


if __name__ == "__main__": main()

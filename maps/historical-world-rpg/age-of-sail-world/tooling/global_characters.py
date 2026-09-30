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
WORLD = ROOT / "scenario/world/world.json"
ROSTERS = ROOT / "scenario/rosters"
ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
REGIONS = {"europe", "africa", "middle_east_india", "southeast_asia", "east_asia", "americas_caribbean", "pacific"}


class CharacterRosterError(ValueError): pass


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
    if not all(sum(x["regionId"] == region for x in characters.values()) >= 2 for region in REGIONS):
        raise CharacterRosterError("every region requires at least two characters")
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
        quest_hooks.update(value["questHookIds"]); discovery_hooks.update(value["discoveryHookIds"])
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
    for value in source["characters"]:
        for quest_id in value["questHookIds"]:
            quests.append({"id":quest_id,"title":quest_id.removeprefix("quest_").replace("_"," ").title(),"summary":"A scenario-authored personal objective tied to this companion.","characterId":value["id"]})
        characters.append({
            "id":value["id"],"displayName":value["displayName"],"biography":value["biography"],"epithet":source["characterTitles"][value["id"]],
            "traitIds":value["traitIds"],"skills":value["skills"],"professionIds":value["professionIds"],
            "personalQuestIds":value["questHookIds"],"loyalty":{"score":value["loyalty"]["score"],"permanentState":"none"},
            "allegiancePolityId":value["allegiancePolityId"],"available":False,"recruited":False,"active":True,
            "runtimeTemplateId":"companion_hero","recruitmentCosts":value["recruitmentCosts"],"rewardIds":[],"titleGrantIds":value["titleGrantIds"]})
    return {"traits":source["traits"],"skills":source["skills"],"professions":source["professions"],"personalQuests":quests,
            "characters":characters,"relationshipThresholds":source["relationshipThresholds"],"companionRelationships":source["companionRelationships"]}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--write",action="store_true"); args=parser.parse_args()
    source=json.loads(SOURCE.read_text()); world=json.loads(WORLD.read_text()); equipment=equipment_catalog()
    validate(source,world,equipment); expected=projection(source)
    if args.write:
        world.update(copy.deepcopy(expected)); WORLD.write_text(json.dumps(world,indent=2)+"\n")
    else:
        for key,value in expected.items():
            if world.get(key)!=value: raise CharacterRosterError(f"world projection {key} is stale; run tooling/global_characters.py --write")
    print(f"OK: {len(source['characters'])} recruitable characters across {len(REGIONS)} regions")


if __name__ == "__main__": main()

#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_research import validate as validate_research
from validate_government import (
    validate_allegiance_transition,
    validate_government,
)
from validate_navigation import validate as validate_navigation
from validate_quest_events import validate as validate_quest_events
from validate_timeline import validate as validate_timeline

ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class ValidationError(Exception):
    pass


def fail(message: str) -> None:
    raise ValidationError(message)


def require_id(value, context):
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        fail(f"{context}: invalid stable ID {value!r}")


def unique_index(items, domain):
    result = {}
    for item in items:
        if not isinstance(item, dict):
            fail(f"{domain}: every entry must be an object")
        ident = item.get("id")
        require_id(ident, f"{domain}.id")
        if ident in result:
            fail(f"{domain}: duplicate ID {ident!r}")
        result[ident] = item
    return result


def require_unique_refs(values, domain, targets, expected_kind=None):
    if not isinstance(values, list) or not values:
        fail(f"{domain}: at least one member is required")
    seen = set()
    for ident in values:
        require_id(ident, domain)
        if ident in seen:
            fail(f"{domain}: duplicate reference {ident!r}")
        seen.add(ident)
        if ident not in targets:
            fail(f"{domain}: missing reference {ident!r}")
        if expected_kind and targets[ident].get("kind") != expected_kind:
            fail(f"{domain}: {ident!r} is not a {expected_kind}")


def require_score(value, context):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not -100 <= value <= 100:
        fail(f"{context}: must be a number between -100 and 100")


def require_references(values, domain, targets):
    if not isinstance(values, list):
        fail(f"{domain}: must be an array")
    seen = set()
    for ident in values:
        require_id(ident, domain)
        if ident in seen:
            fail(f"{domain}: duplicate reference {ident!r}")
        seen.add(ident)
        if ident not in targets:
            fail(f"{domain}: missing reference {ident!r}")


def validate_permanent_state_transition(current, requested):
    if (current, requested) != ("none", "oathbound"):
        fail(f"invalid permanent loyalty transition {current!r} -> {requested!r}")


def validate_operational_state(value, domain):
    if not isinstance(value, dict):
        fail(f"{domain}: operationalState must be an object")
    for field in ("morale", "supply", "readiness"):
        score = value.get(field)
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 100:
            fail(f"{domain}.{field}: must be a number between 0 and 100")


def validate_owned_controlled(value, domain, polities):
    for field in ("legalOwnerPolityId", "controllerPolityId"):
        if value.get(field) not in polities:
            fail(f"{domain}: {field} references {value.get(field)!r}")


def validate(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != 8:
        fail("schemaVersion must currently be 8")

    timeline = validate_timeline(data, fail)

    polity = unique_index(data.get("polities", []), "polities")
    province = unique_index(data.get("provinces", []), "provinces")
    settlement = unique_index(data.get("settlements", []), "settlements")
    settlement_service = unique_index(data.get("settlementServiceDefinitions", []), "settlementServiceDefinitions")
    settlement_template = unique_index(data.get("settlementObjectTemplates", []), "settlementObjectTemplates")
    city_core = unique_index(data.get("cityCores", []), "cityCores")
    defense_layout = unique_index(data.get("defenseLayouts", []), "defenseLayouts")
    officer = unique_index(data.get("officers", []), "officers")
    strategic_unit = unique_index(data.get("strategicUnits", []), "strategicUnits")
    army = unique_index(data.get("armies", []), "armies")
    fleet = unique_index(data.get("fleets", []), "fleets")
    trait = unique_index(data.get("traits", []), "traits")
    skill = unique_index(data.get("skills", []), "skills")
    profession = unique_index(data.get("professions", []), "professions")
    personal_quest = unique_index(data.get("personalQuests", []), "personalQuests")
    character = unique_index(data.get("characters", []), "characters")
    threshold = unique_index(data.get("relationshipThresholds", []), "relationshipThresholds")
    relationship = unique_index(data.get("companionRelationships", []), "companionRelationships")
    navigation_zones, navigation_safe_points, navigation_states = validate_navigation(
        data, fail, require_id, unique_index, strategic_unit
    )
    technologies, institutions = validate_research(data, fail, require_id, unique_index, polity, province)
    title_styles, title_grants, holdings, allegiances = validate_government(
        data, fail, require_id, unique_index, polity, province, settlement, character
    )
    quests, events = validate_quest_events(data, fail, require_id, unique_index)

    if not polity:
        fail("at least one polity is required")
    if not province:
        fail("at least one province is required")
    if not settlement:
        fail("at least one settlement is required")

    allowed_tiers = {
        "none", "knight", "baron", "count", "marquess",
        "duke", "prince", "king", "emperor"
    }
    allowed_kinds = {
        "capital", "major_city", "city", "town", "village", "port",
        "fort", "trading_post", "mission", "mine", "plantation",
        "pirate_haven"
    }

    for pid, p in polity.items():
        if p.get("sovereignTier") not in allowed_tiers:
            fail(f"polity {pid}: invalid sovereignTier")
        capital = p.get("capitalSettlementId")
        if capital not in settlement:
            fail(f"polity {pid}: missing capital settlement {capital!r}")
        seen = set()
        for province_id in p.get("provinceIds", []):
            if province_id in seen:
                fail(f"polity {pid}: duplicate province ref {province_id!r}")
            seen.add(province_id)
            if province_id not in province:
                fail(f"polity {pid}: missing province {province_id!r}")
            if province[province_id].get("legalOwnerPolityId") != pid:
                fail(
                    f"polity {pid}: province {province_id!r} has a different legal owner"
                )

    for province_id, p in province.items():
        owner = p.get("legalOwnerPolityId")
        controller = p.get("controllerPolityId")
        if owner not in polity:
            fail(f"province {province_id}: missing legal owner {owner!r}")
        if controller not in polity:
            fail(f"province {province_id}: missing controller {controller!r}")
        seen = set()
        for settlement_id in p.get("settlementIds", []):
            if settlement_id in seen:
                fail(f"province {province_id}: duplicate settlement ref {settlement_id!r}")
            seen.add(settlement_id)
            if settlement_id not in settlement:
                fail(f"province {province_id}: missing settlement {settlement_id!r}")
            if settlement[settlement_id].get("provinceId") != province_id:
                fail(
                    f"province {province_id}: settlement {settlement_id!r} points elsewhere"
                )

    for settlement_id, s in settlement.items():
        if s.get("kind") not in allowed_kinds:
            fail(f"settlement {settlement_id}: invalid kind")
        province_id = s.get("provinceId")
        if province_id not in province:
            fail(f"settlement {settlement_id}: missing province {province_id!r}")
        for field in ("legalOwnerPolityId", "controllerPolityId"):
            value = s.get(field)
            if value not in polity:
                fail(f"settlement {settlement_id}: {field} references {value!r}")
        if s.get("civilianFacilitiesInvulnerable") is not True:
            fail(
                f"settlement {settlement_id}: civilianFacilitiesInvulnerable must be true"
            )
        navigation_zone_id = s.get("navigationZoneId")
        if navigation_zone_id is not None and navigation_zone_id not in navigation_zones:
            fail(f"settlement {settlement_id}: missing navigation zone {navigation_zone_id!r}")
        if s.get("capturable"):
            for field in ("cityCoreId", "defenseLayoutId"):
                value = s.get(field)
                require_id(value, f"settlement {settlement_id}.{field}")
        core_id = s.get("cityCoreId")
        layout_id = s.get("defenseLayoutId")
        if core_id is not None and core_id not in city_core:
            fail(f"settlement {settlement_id}: missing city core {core_id!r}")
        if layout_id is not None and layout_id not in defense_layout:
            fail(f"settlement {settlement_id}: missing defense layout {layout_id!r}")
        require_references(s.get("serviceIds"), f"settlement {settlement_id}.serviceIds", settlement_service)

    for service_id, service in settlement_service.items():
        if not isinstance(service.get("name"), str) or not service["name"].strip():
            fail(f"settlement service {service_id}: name must be non-empty")
    for template_id, template in settlement_template.items():
        if template.get("kind") not in {"city_core", "defense"}:
            fail(f"settlement object template {template_id}: invalid kind")
    for core_id, core in city_core.items():
        template_id = core.get("objectTemplateId")
        if template_id not in settlement_template:
            fail(f"city core {core_id}: missing object template {template_id!r}")
        if settlement_template[template_id].get("kind") != "city_core":
            fail(f"city core {core_id}: object template {template_id!r} is not a city core")
    for layout_id, layout in defense_layout.items():
        require_references(layout.get("objectTemplateIds"), f"defense layout {layout_id}.objectTemplateIds", settlement_template)
        for template_id in layout["objectTemplateIds"]:
            if settlement_template[template_id].get("kind") != "defense":
                fail(f"defense layout {layout_id}: object template {template_id!r} is not a defense")

    for unit_id, unit in strategic_unit.items():
        domain = f"strategic unit {unit_id}"
        if unit.get("kind") not in {"formation", "ship"}:
            fail(f"{domain}: invalid kind")
        validate_owned_controlled(unit, domain, polity)
        strength = unit.get("representedStrength")
        if isinstance(strength, bool) or not isinstance(strength, int) or strength < 1:
            fail(f"{domain}: representedStrength must be a positive integer")
        require_id(unit.get("strengthUnitId"), f"{domain}.strengthUnitId")
        validate_operational_state(unit.get("operationalState"), domain)
        runtime = unit.get("runtimeInstantiation")
        if not isinstance(runtime, dict):
            fail(f"{domain}: runtimeInstantiation must be an object")
        state, count = runtime.get("state"), runtime.get("activeObjectCount")
        require_id(runtime.get("runtimeTemplateId"), f"{domain}.runtimeTemplateId")
        if state not in {"abstract", "active"}:
            fail(f"{domain}: invalid runtime state")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            fail(f"{domain}: activeObjectCount must be a non-negative integer")
        if (state == "abstract" and count != 0) or (state == "active" and count < 1):
            fail(f"{domain}: runtime state and activeObjectCount disagree")
        for officer_id in unit.get("officerIds", []):
            if officer_id not in officer:
                fail(f"{domain}: missing officer {officer_id!r}")
        commander_id = unit.get("commanderOfficerId")
        if commander_id is not None and commander_id not in officer:
            fail(f"{domain}: missing commander {commander_id!r}")

    for collection_name, groups, member_field, kind in (
        ("army", army, "formationUnitIds", "formation"),
        ("fleet", fleet, "shipUnitIds", "ship"),
    ):
        for group_id, group in groups.items():
            domain = f"{collection_name} {group_id}"
            validate_owned_controlled(group, domain, polity)
            validate_operational_state(group.get("operationalState"), domain)
            require_unique_refs(group.get(member_field), f"{domain}.{member_field}", strategic_unit, kind)
            commander_id = group.get("commanderOfficerId")
            if commander_id not in officer:
                fail(f"{domain}: missing commander {commander_id!r}")
            for officer_id in group.get("officerIds", []):
                if officer_id not in officer:
                    fail(f"{domain}: missing officer {officer_id!r}")

    for collection_name, definitions in (
        ("trait", trait), ("skill", skill), ("profession", profession)
    ):
        for definition_id, definition in definitions.items():
            for field in ("name", "description"):
                if not isinstance(definition.get(field), str) or not definition[field]:
                    fail(f"{collection_name} {definition_id}: {field} must be non-empty")

    allowed_permanent_states = {"none", "oathbound"}
    for character_id, value in character.items():
        domain = f"character {character_id}"
        for field in ("displayName", "biography"):
            if not isinstance(value.get(field), str) or not value[field]:
                fail(f"{domain}: {field} must be non-empty")
        require_references(value.get("traitIds"), f"{domain}.traitIds", trait)
        require_references(value.get("professionIds"), f"{domain}.professionIds", profession)
        require_references(value.get("personalQuestIds"), f"{domain}.personalQuestIds", personal_quest)
        ratings = value.get("skills")
        if not isinstance(ratings, list):
            fail(f"{domain}.skills: must be an array")
        seen_skills = set()
        for rating in ratings:
            if not isinstance(rating, dict):
                fail(f"{domain}.skills: every rating must be an object")
            skill_id = rating.get("skillId")
            require_id(skill_id, f"{domain}.skills.skillId")
            if skill_id in seen_skills:
                fail(f"{domain}.skills: duplicate skill {skill_id!r}")
            seen_skills.add(skill_id)
            if skill_id not in skill:
                fail(f"{domain}.skills: missing skill {skill_id!r}")
            score = rating.get("rating")
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 100:
                fail(f"{domain}.skills {skill_id}: rating must be between 0 and 100")
        loyalty = value.get("loyalty")
        if not isinstance(loyalty, dict):
            fail(f"{domain}.loyalty: must be an object")
        require_score(loyalty.get("score"), f"{domain}.loyalty.score")
        if loyalty.get("permanentState") not in allowed_permanent_states:
            fail(f"{domain}.loyalty: invalid permanentState")

    for quest_id, quest in personal_quest.items():
        character_id = quest.get("characterId")
        if character_id not in character:
            fail(f"personal quest {quest_id}: missing character {character_id!r}")
        if quest_id not in character[character_id].get("personalQuestIds", []):
            fail(f"personal quest {quest_id}: character {character_id!r} does not list the quest")

    allowed_scopes = {"loyalty", "companion_relationship"}
    allowed_consequences = {"buff", "debuff", "content_unlock"}
    for threshold_id, value in threshold.items():
        domain = f"relationship threshold {threshold_id}"
        if value.get("scope") not in allowed_scopes:
            fail(f"{domain}: invalid scope")
        minimum, maximum = value.get("minimum"), value.get("maximum")
        require_score(minimum, f"{domain}.minimum")
        require_score(maximum, f"{domain}.maximum")
        if minimum > maximum:
            fail(f"{domain}: minimum cannot exceed maximum")
        consequences = value.get("consequences")
        if not isinstance(consequences, list) or not consequences:
            fail(f"{domain}: at least one consequence is required")
        for consequence in consequences:
            if not isinstance(consequence, dict) or consequence.get("kind") not in allowed_consequences:
                fail(f"{domain}: invalid consequence")
            require_id(consequence.get("contentId"), f"{domain}.consequence.contentId")

    seen_pairs = set()
    for relationship_id, value in relationship.items():
        domain = f"companion relationship {relationship_id}"
        first, second = value.get("characterAId"), value.get("characterBId")
        if first not in character:
            fail(f"{domain}: missing character {first!r}")
        if second not in character:
            fail(f"{domain}: missing character {second!r}")
        if first == second:
            fail(f"{domain}: a character cannot have a relationship with itself")
        pair = frozenset((first, second))
        if pair in seen_pairs:
            fail(f"{domain}: duplicate companion pair")
        seen_pairs.add(pair)
        require_score(value.get("score"), f"{domain}.score")

    print(
        f"OK: {path} | "
        f"{len(polity)} polities, {len(province)} provinces, "
        f"{len(settlement)} settlements, {len(city_core)} city cores, "
        f"{len(defense_layout)} defense layouts, {len(strategic_unit)} strategic units, "
        f"{len(army)} armies, {len(fleet)} fleets, {len(character)} characters, "
        f"{len(relationship)} companion relationships, {len(technologies)} technologies, "
        f"{len(institutions)} institutions, {len(title_grants)} title grants, "
        f"{len(holdings)} territorial holdings, {len(allegiances)} allegiances, "
        f"{len(navigation_zones)} navigation zones, "
        f"{len(navigation_safe_points)} navigation safe points, "
        f"{len(navigation_states)} active unit navigation states, "
        f"{len(quests)} quests, {len(events)} events, "
        f"{len(timeline.get('schedules', []))} timeline schedules"
    )


def main():
    if len(sys.argv) != 2:
        print("usage: validate_world.py <world.json>", file=sys.stderr)
        return 2
    try:
        validate(Path(sys.argv[1]))
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

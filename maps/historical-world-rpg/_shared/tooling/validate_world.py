#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

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
    if data.get("schemaVersion") != 1:
        fail("schemaVersion must currently be 1")

    polity = unique_index(data.get("polities", []), "polities")
    province = unique_index(data.get("provinces", []), "provinces")
    settlement = unique_index(data.get("settlements", []), "settlements")
    officer = unique_index(data.get("officers", []), "officers")
    strategic_unit = unique_index(data.get("strategicUnits", []), "strategicUnits")
    army = unique_index(data.get("armies", []), "armies")
    fleet = unique_index(data.get("fleets", []), "fleets")

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
        if s.get("capturable"):
            for field in ("cityCoreId", "defenseLayoutId"):
                value = s.get(field)
                require_id(value, f"settlement {settlement_id}.{field}")

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

    print(
        f"OK: {path} | "
        f"{len(polity)} polities, {len(province)} provinces, "
        f"{len(settlement)} settlements, {len(strategic_unit)} strategic units, "
        f"{len(army)} armies, {len(fleet)} fleets"
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

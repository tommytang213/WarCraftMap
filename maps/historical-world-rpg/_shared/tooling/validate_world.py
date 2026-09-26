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


def validate(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != 1:
        fail("schemaVersion must currently be 1")

    polity = unique_index(data.get("polities", []), "polities")
    province = unique_index(data.get("provinces", []), "provinces")
    settlement = unique_index(data.get("settlements", []), "settlements")

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

    print(
        f"OK: {path} | "
        f"{len(polity)} polities, {len(province)} provinces, "
        f"{len(settlement)} settlements"
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

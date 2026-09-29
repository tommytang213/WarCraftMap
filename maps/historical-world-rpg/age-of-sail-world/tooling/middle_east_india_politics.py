#!/usr/bin/env python3
"""Validate and project the authoritative Middle East/India 1450 political baseline."""
from __future__ import annotations

import copy
import json
import re
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scenario/politics/middle-east-india-1450.json"
GEOGRAPHY = ROOT / "scenario/geography/middle_east_india.json"
WORLD = ROOT / "scenario/world/world.json"
ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
RANKS = {"none", "baron", "count", "marquess", "duke", "prince", "king", "emperor"}
RELATION_KINDS = {"vassal", "tributary"}
DIPLOMACY_KINDS = {"alliance", "rivalry", "truce", "guarantee"}


class PoliticsError(ValueError):
    pass


def _index(rows, label):
    if not isinstance(rows, list):
        raise PoliticsError(f"{label} must be an array")
    result = {}
    for row in rows:
        ident = row.get("id") if isinstance(row, dict) else None
        if not isinstance(ident, str) or not ID.fullmatch(ident):
            raise PoliticsError(f"{label}: invalid stable ID {ident!r}")
        if ident in result:
            raise PoliticsError(f"{label}: duplicate stable ID {ident!r}")
        result[ident] = row
    return result


def validate(source_path=SOURCE, world_path=WORLD, geography_path=GEOGRAPHY, require_projection=True):
    data = json.loads(Path(source_path).read_text()); world = json.loads(Path(world_path).read_text())
    geography = json.loads(Path(geography_path).read_text())
    if data.get("schemaVersion") != 1 or data.get("campaignStartDate") != "1450-01-01":
        raise PoliticsError("Middle East/India baseline must use schema 1 and campaign start 1450-01-01")
    coverage = data.get("coverageRule", {})
    if coverage.get("kind") != "exclusive_authoritative_provinces" or not coverage.get("exceptions"):
        raise PoliticsError("authoritative coverage requires explicit compression exceptions")
    instances = _index(geography.get("instances"), "geography instances")
    features = {f["id"]: instance["id"] for instance in instances.values() for f in instance.get("features", [])}
    polities = _index(data.get("polities"), "polities"); provinces = {}; owners = {}
    world_polities = _index(world.get("polities", []), "world polities")
    world_provinces = _index(world.get("provinces", []), "world provinces")
    world_settlements = _index(world.get("settlements", []), "world settlements")
    for polity_id, polity in polities.items():
        if polity.get("sovereignTier") not in RANKS or not polity.get("nativeSovereignTitle"):
            raise PoliticsError(f"polity {polity_id}: invalid sovereign title")
        default_instance = polity.get("regionalInstanceId")
        if default_instance not in instances:
            raise PoliticsError(f"polity {polity_id}: missing regional instance")
        refs = polity.get("geographicFeatureIds")
        if not isinstance(refs, list) or not refs or any(ref not in features for ref in refs):
            raise PoliticsError(f"polity {polity_id}: invalid geography references")
        local = _index(polity.get("provinces"), f"polity {polity_id} provinces")
        if not local:
            raise PoliticsError(f"polity {polity_id}: missing authoritative coverage")
        for province_id, province in local.items():
            if province_id in provinces:
                raise PoliticsError(f"authoritative coverage overlaps at province {province_id!r}")
            instance = province.get("regionalInstanceId", default_instance)
            province_refs = province.get("geographicFeatureIds", refs)
            if instance not in instances or not province_refs or any(features.get(ref) != instance for ref in province_refs):
                raise PoliticsError(f"province {province_id}: invalid regional geography")
            adjacent = province.get("adjacentProvinceIds")
            if not isinstance(adjacent, list) or len(adjacent) != len(set(adjacent)):
                raise PoliticsError(f"province {province_id}: adjacency must be unique")
            provinces[province_id] = province; owners[province_id] = polity_id
        capital = polity.get("capitalSettlementId")
        if require_projection and capital not in world_settlements and not polity.get("capitalException"):
            raise PoliticsError(f"polity {polity_id}: capital is missing and has no documented exception")
        if require_projection:
            projected = world_polities.get(polity_id)
            if projected is None or not set(local) <= set(projected.get("provinceIds", [])):
                raise PoliticsError(f"polity {polity_id}: canonical polity projection is missing or stale")
    for province_id, province in provinces.items():
        for neighbor in province["adjacentProvinceIds"]:
            if neighbor not in provinces:
                raise PoliticsError(f"province {province_id}: missing adjacent province {neighbor!r}")
            if province_id not in provinces[neighbor]["adjacentProvinceIds"]:
                raise PoliticsError(f"province adjacency is not reciprocal: {province_id!r}, {neighbor!r}")
        if require_projection:
            projected = world_provinces.get(province_id)
            if projected is None or projected.get("legalOwnerPolityId") != owners[province_id]:
                raise PoliticsError(f"province {province_id}: canonical ownership projection is missing or stale")
    relation_ids = set(); parents = {}
    for relation in data.get("sovereigntyRelationships", []):
        ident = relation.get("id"); subject = relation.get("subjectPolityId"); overlord = relation.get("overlordPolityId")
        if not isinstance(ident, str) or not ID.fullmatch(ident) or ident in relation_ids:
            raise PoliticsError("sovereignty relationship has invalid or duplicate ID")
        relation_ids.add(ident)
        if relation.get("kind") not in RELATION_KINDS or subject == overlord or subject not in polities or overlord not in polities or subject in parents:
            raise PoliticsError(f"sovereignty relationship {ident}: invalid or contradictory participants")
        if relation.get("taxRatePercent") not in range(0, 101) or not relation.get("obligations"):
            raise PoliticsError(f"sovereignty relationship {ident}: impossible grant")
        parents[subject] = overlord
    for start in parents:
        seen = set(); current = start
        while current in parents:
            if current in seen: raise PoliticsError(f"sovereignty hierarchy contains a cycle at {current!r}")
            seen.add(current); current = parents[current]
    diplomacy_ids = set()
    for relation in data.get("diplomaticRelations", []):
        ident = relation.get("id"); participants = (relation.get("firstPolityId"), relation.get("secondPolityId"))
        if not isinstance(ident, str) or not ID.fullmatch(ident) or ident in diplomacy_ids or relation.get("kind") not in DIPLOMACY_KINDS:
            raise PoliticsError("diplomatic relation has invalid ID or kind")
        diplomacy_ids.add(ident)
        if len(set(participants)) != 2 or any(p not in polities for p in participants):
            raise PoliticsError(f"diplomatic relation {ident}: invalid participants")
    conflict_ids = set()
    for conflict in data.get("activeConflicts", []):
        ident = conflict.get("id"); attackers = conflict.get("attackerPolityIds", []); defenders = conflict.get("defenderPolityIds", [])
        if not isinstance(ident, str) or not ID.fullmatch(ident) or ident in conflict_ids:
            raise PoliticsError("active conflict has invalid or duplicate ID")
        conflict_ids.add(ident)
        if not attackers or not defenders or set(attackers) & set(defenders) or any(p not in polities for p in attackers + defenders):
            raise PoliticsError(f"conflict {ident}: invalid participants")
    # Every multi-province polity must be internally reachable; islands and single provinces are valid exceptions.
    for polity_id, polity in polities.items():
        local = {p["id"] for p in polity["provinces"]}
        reached = {next(iter(local))}; pending = deque(reached)
        while pending:
            current = pending.popleft()
            for neighbor in provinces[current]["adjacentProvinceIds"]:
                if neighbor in local and neighbor not in reached: reached.add(neighbor); pending.append(neighbor)
        if reached != local: raise PoliticsError(f"polity {polity_id}: provinces are not internally reachable")
    return data


def project(data, world):
    world = copy.deepcopy(world)
    polity_ids = {p["id"] for p in data["polities"]}; province_ids = {p["id"] for polity in data["polities"] for p in polity["provinces"]}
    relations = {r["subjectPolityId"]: r for r in data["sovereigntyRelationships"]}
    world["provinces"] = [p for p in world["provinces"] if p["id"] not in province_ids]
    world["territorialHoldings"] = [h for h in world["territorialHoldings"] if h["territory"]["id"] not in province_ids]
    existing_polities = {p["id"]: p for p in world["polities"]}
    existing_settlements = {s["id"] for s in world["settlements"]}
    existing_styles = {s["polityId"] for s in world["titleStyles"]}
    for polity in data["polities"]:
        pid = polity["id"]; new_provinces = [p["id"] for p in polity["provinces"]]
        if pid in existing_polities:
            existing_polities[pid]["provinceIds"] = list(dict.fromkeys(existing_polities[pid]["provinceIds"] + new_provinces))
        else:
            record = {k: polity[k] for k in ("id", "name", "adjective", "sovereignTier", "nativeSovereignTitle", "capitalSettlementId")}
            record["provinceIds"] = new_provinces; world["polities"].append(record)
        capital = polity["capitalSettlementId"]
        if capital not in existing_settlements and not polity.get("capitalException"):
            first = polity["provinces"][0]["id"]
            world["settlements"].append({"id":capital,"name":capital.replace("_", " ").title(),"kind":"capital","provinceId":first,"legalOwnerPolityId":pid,"controllerPolityId":pid,"capturable":True,"civilianFacilitiesInvulnerable":True,"cityCoreId":"city_core_"+capital,"defenseLayoutId":"defense_"+capital,"serviceIds":["market","quest_hub"],"regionalInstanceId":polity["regionalInstanceId"],"activation":{"runtimeState":"abstract","representationTemplateId":"settlement_representation","deterministicKey":capital}})
            world["cityCores"].append({"id":"city_core_"+capital,"objectTemplateId":"capital_city_core"})
            world["defenseLayouts"].append({"id":"defense_"+capital,"objectTemplateIds":["capital_defenses"]}); existing_settlements.add(capital)
        if pid not in existing_styles:
            rank = polity["sovereignTier"] if polity["sovereignTier"] != "none" else "prince"
            world["titleStyles"].append({"id":"title_"+pid,"polityId":pid,"rankTier":rank,"nativeName":polity["nativeSovereignTitle"],"genericName":rank.title()})
            relation = relations.get(pid); vassal = relation if relation and relation["kind"] == "vassal" else None
            grantor = "grant_" + vassal["overlordPolityId"] if vassal else None
            grant = {"id":"grant_"+pid,"titleStyleId":"title_"+pid,"holder":{"kind":"polity","id":pid},"allegiancePolityId":vassal["overlordPolityId"] if vassal else pid,"sovereign":vassal is None}
            if grantor: grant["grantorTitleId"] = grantor
            world["titleGrants"].append(grant); existing_styles.add(pid)
            if vassal: world["allegiances"].append({"id":"allegiance_"+pid,"subject":{"kind":"polity","id":pid},"polityId":vassal["overlordPolityId"]})
    holdings_by_owner = {}
    for h in world["territorialHoldings"]: holdings_by_owner.setdefault(h["legalOwner"]["id"], h["id"])
    province_records = []
    for polity in data["polities"]:
        pid = polity["id"]; relation = relations.get(pid)
        for province in polity["provinces"]:
            capital_ids = [polity["capitalSettlementId"]] if polity["capitalSettlementId"] in existing_settlements and province is polity["provinces"][0] and not polity.get("capitalException") else []
            world["provinces"].append({"id":province["id"],"name":province["name"],"administrativeType":province["administrativeType"],"legalOwnerPolityId":pid,"controllerPolityId":pid,"settlementIds":capital_ids})
            holding = {"id":"holding_"+province["id"],"territory":{"kind":"province","id":province["id"]},"legalOwner":{"kind":"polity","id":pid},"controllerPolityId":pid,"governingPolityId":pid,"sovereignPolityId":relation["overlordPolityId"] if relation else pid,"autonomyPercent":70 if relation else 35,"overlordTaxRatePercent":relation["taxRatePercent"] if relation else 0,"upkeepRatePercent":5,"obligations":[{"kind":"service","value":1}] if relation else []}
            if relation: holding["overlordHoldingId"] = holdings_by_owner[relation["overlordPolityId"]]
            world["territorialHoldings"].append(holding); province_records.append(holding); holdings_by_owner.setdefault(pid, holding["id"])
    return world


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        if argv == ["--write"]:
            data = validate(require_projection=False)
            WORLD.write_text(json.dumps(project(data, json.loads(WORLD.read_text())), ensure_ascii=False, indent=2) + "\n")
        elif argv: raise PoliticsError("usage: middle_east_india_politics.py [--write]")
        data = validate()
        print(f"Middle East/India politics valid: {len(data['polities'])} polities, {sum(len(p['provinces']) for p in data['polities'])} provinces, {len(data['sovereigntyRelationships'])} sovereignty relationships, {len(data['activeConflicts'])} conflicts")
    except (OSError, json.JSONDecodeError, PoliticsError, KeyError) as error:
        print(f"Middle East/India politics validation failed: {error}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__": raise SystemExit(main())

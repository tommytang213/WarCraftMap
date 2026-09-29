#!/usr/bin/env python3
"""Validate Europe 1450 political source data and its canonical-world projection."""
from __future__ import annotations

import json
import re
import sys
from collections import deque
from pathlib import Path

ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class ValidationError(ValueError):
    pass


def fail(message):
    raise ValidationError(message)


def index(items, domain):
    result = {}
    for item in items:
        ident = item.get("id") if isinstance(item, dict) else None
        if not isinstance(ident, str) or not ID.fullmatch(ident): fail(f"{domain}: invalid stable ID {ident!r}")
        if ident in result: fail(f"{domain}: duplicate stable ID {ident!r}")
        result[ident] = item
    return result


def validate(source_path, world_path=None, geography_path=None):
    root = source_path.resolve().parents[2]
    world_path = world_path or root / "scenario/world/world.json"
    geography_path = geography_path or root / "scenario/geography/europe.json"
    data=json.loads(source_path.read_text(encoding="utf-8")); world=json.loads(world_path.read_text(encoding="utf-8")); geography=json.loads(geography_path.read_text(encoding="utf-8"))
    if data.get("schemaVersion") != 1 or data.get("campaignStartDate") != "1450-01-01": fail("Europe baseline must use schema 1 and campaign start 1450-01-01")
    if data.get("coverageRule") != {"kind":"exclusive_authoritative_provinces","exceptions":[]}: fail("authoritative coverage must be exclusive with explicit exceptions")
    instances=index(geography.get("instances",[]),"geography instances")
    features={f["id"] for instance in instances.values() for f in instance.get("features",[])}
    polities=index(data.get("polities",[]),"European polities"); provinces={}; province_owner={}
    world_polities=index(world.get("polities",[]),"world polities"); world_provinces=index(world.get("provinces",[]),"world provinces"); settlements=index(world.get("settlements",[]),"world settlements")
    relationship_ids=set(); conflict_ids=set()
    for pid, polity in polities.items():
        instance=polity.get("regionalInstanceId")
        if instance not in instances: fail(f"polity {pid}: missing regional instance {instance!r}")
        refs=polity.get("geographicFeatureIds")
        if not isinstance(refs,list) or not refs: fail(f"polity {pid}: geographicFeatureIds must not be empty")
        for ref in refs:
            if ref not in features: fail(f"polity {pid}: missing geographic feature {ref!r}")
        local=index(polity.get("provinces",[]),f"polity {pid} provinces")
        if not local: fail(f"polity {pid}: at least one authoritative province is required")
        for province_id, province in local.items():
            if province.get("regionalInstanceId") != instance: fail(f"province {province_id}: must be assigned to polity regional instance {instance!r}")
            province_features=province.get("geographicFeatureIds")
            if not isinstance(province_features,list) or not province_features or any(ref not in features for ref in province_features): fail(f"province {province_id}: invalid geographic feature references")
            if province_id in provinces: fail(f"authoritative coverage overlaps at province {province_id!r}")
            provinces[province_id]=province; province_owner[province_id]=pid
        capital=polity.get("capitalSettlementId")
        if capital not in settlements: fail(f"polity {pid}: capital {capital!r} is missing and has no documented exception")
        if settlements[capital].get("provinceId") not in local: fail(f"polity {pid}: capital is outside its authoritative provinces")
        projected=world_polities.get(pid)
        projected_ids=[] if projected is None else projected.get("provinceIds",[])
        if [province_id for province_id in projected_ids if province_id in local] != list(local): fail(f"polity {pid}: canonical world projection is missing or stale")
        capital_province=settlements[capital]["provinceId"]; reached={capital_province}; queue=deque([capital_province])
        while queue:
            current=queue.popleft()
            for neighbor in local[current].get("adjacentProvinceIds",[]):
                if neighbor in local and neighbor not in reached: reached.add(neighbor); queue.append(neighbor)
        if reached != set(local): fail(f"polity {pid}: province {sorted(set(local)-reached)[0]!r} is unreachable from its capital topology")
    for province_id, province in provinces.items():
        adjacent=province.get("adjacentProvinceIds")
        if not isinstance(adjacent,list) or len(adjacent)!=len(set(adjacent)): fail(f"province {province_id}: adjacency must be a unique array")
        for neighbor in adjacent:
            if neighbor not in provinces: fail(f"province {province_id}: missing adjacent province {neighbor!r}")
        projected=world_provinces.get(province_id)
        if projected is None or projected.get("legalOwnerPolityId")!=province_owner[province_id]: fail(f"province {province_id}: canonical ownership projection is missing or stale")
    if any(ident not in world_provinces for ident in provinces): fail("canonical world has unassigned authoritative province coverage")
    for domain, records in (("vassalage",data.get("vassalage",[])),("personal unions",data.get("personalUnions",[]))):
        for record in records:
            ident=record.get("id")
            if not isinstance(ident,str) or not ID.fullmatch(ident) or ident in relationship_ids: fail(f"{domain}: duplicate or invalid ID {ident!r}")
            relationship_ids.add(ident)
            refs=[record.get("subjectPolityId"),record.get("overlordPolityId")] if domain=="vassalage" else [record.get("seniorPolityId"),*record.get("juniorPolityIds",[])]
            if len(refs)!=len(set(refs)) or any(ref not in polities for ref in refs): fail(f"{domain} {ident}: invalid participants")
    parents={x["subjectPolityId"]:x["overlordPolityId"] for x in data.get("vassalage",[])}
    for start in parents:
        seen=set(); current=start
        while current in parents:
            if current in seen: fail(f"vassal hierarchy contains a cycle at {current!r}")
            seen.add(current); current=parents[current]
    for conflict in data.get("activeConflicts",[]):
        ident=conflict.get("id")
        if not isinstance(ident,str) or not ID.fullmatch(ident) or ident in conflict_ids: fail(f"active conflicts: duplicate or invalid ID {ident!r}")
        conflict_ids.add(ident); attackers=conflict.get("attackerPolityIds",[]); defenders=conflict.get("defenderPolityIds",[])
        if not attackers or not defenders or set(attackers)&set(defenders) or any(x not in polities for x in attackers+defenders): fail(f"conflict {ident}: invalid or inactive participants")
    print(f"OK: {source_path} | {len(polities)} polities, {len(provinces)} provinces, {len(relationship_ids)} sovereignty relationships, {len(conflict_ids)} active conflicts")
    return data


if __name__ == "__main__":
    try: validate(Path(sys.argv[1]))
    except (OSError,json.JSONDecodeError,ValidationError) as exc: print(f"ERROR: {exc}",file=sys.stderr); raise SystemExit(1)

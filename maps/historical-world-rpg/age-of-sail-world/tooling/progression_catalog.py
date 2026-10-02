#!/usr/bin/env python3
"""Validate and project the authoritative Age of Sail progression catalog."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scenario/progression/catalog.json"
WORLD = ROOT / "scenario/world/world.json"
KINDS = {"unit", "building", "ability", "policy", "modifier"}


class CatalogError(ValueError):
    pass


def _index(rows, domain):
    if not isinstance(rows, list):
        raise CatalogError(f"{domain}: expected array")
    result = {}
    for row in rows:
        ident = row.get("id") if isinstance(row, dict) else None
        if not isinstance(ident, str) or not ident or ident in result:
            raise CatalogError(f"{domain}: invalid or duplicate ID {ident!r}")
        result[ident] = row
    return result


def validate(source_path=SOURCE, world_path=WORLD, require_projection=True):
    data = json.loads(Path(source_path).read_text(encoding="utf-8"))
    world = json.loads(Path(world_path).read_text(encoding="utf-8"))
    if data.get("format") != "age_of_sail_progression_v1":
        raise CatalogError("unsupported catalog format")
    years = data.get("campaignYears", {})
    if years != {"start": 1450, "end": 1820}:
        raise CatalogError("catalog campaign years must match 1450–1820")
    branches = _index(data.get("branches"), "branches")
    technologies = _index(data.get("technologies"), "technologies")
    institutions = _index(data.get("institutions"), "institutions")
    overlap = set(technologies) & set(institutions)
    if overlap:
        raise CatalogError(f"duplicate research ID {sorted(overlap)[0]!r}")
    nodes = {**technologies, **institutions}
    references = {(x.get("kind"), x.get("id")) for x in data.get("unlockReferences", [])}
    if len(references) != len(data.get("unlockReferences", [])) or any(k not in KINDS for k, _ in references):
        raise CatalogError("invalid or duplicate unlock reference")

    entries = set()
    for branch_id, branch in branches.items():
        branch_entries = branch.get("entryNodeIds")
        if not isinstance(branch_entries, list) or not branch_entries:
            raise CatalogError(f"branch {branch_id}: missing entry nodes")
        for node_id in branch_entries:
            if node_id not in nodes or nodes[node_id].get("branchId") != branch_id:
                raise CatalogError(f"branch {branch_id}: invalid entry {node_id!r}")
        entries.update(branch_entries)

    dependents = {ident: [] for ident in nodes}
    for ident, node in nodes.items():
        if node.get("branchId") not in branches:
            raise CatalogError(f"node {ident}: invalid branch")
        prerequisites = node.get("prerequisiteIds")
        if not isinstance(prerequisites, list) or len(prerequisites) != len(set(prerequisites)):
            raise CatalogError(f"node {ident}: invalid prerequisites")
        for prerequisite in prerequisites:
            if prerequisite not in nodes:
                raise CatalogError(f"node {ident}: missing prerequisite {prerequisite!r}")
            dependents[prerequisite].append(ident)
        preferred = node.get("preferredYear")
        cost = node.get("baseCost")
        if isinstance(preferred, bool) or not isinstance(preferred, int) or not 1450 <= preferred <= 1820:
            raise CatalogError(f"node {ident}: preferred year outside campaign")
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost <= 0:
            raise CatalogError(f"node {ident}: invalid base cost")
        unlocks = node.get("unlocks")
        if not isinstance(unlocks, list) or len({tuple(x) for x in unlocks}) != len(unlocks):
            raise CatalogError(f"node {ident}: invalid unlocks")
        for unlock in unlocks:
            if not isinstance(unlock, list) or len(unlock) != 2 or tuple(unlock) not in references:
                raise CatalogError(f"node {ident}: undeclared unlock {unlock!r}")

    visiting, visited = set(), set()
    def visit(ident):
        if ident in visiting:
            raise CatalogError(f"research cycle at {ident!r}")
        if ident not in visited:
            visiting.add(ident)
            for prerequisite in nodes[ident]["prerequisiteIds"]:
                visit(prerequisite)
            visiting.remove(ident)
            visited.add(ident)
    for ident in sorted(nodes):
        visit(ident)
    reachable, pending = set(entries), list(entries)
    while pending:
        for dependent in dependents[pending.pop()]:
            if dependent not in reachable and set(nodes[dependent]["prerequisiteIds"]) <= reachable:
                reachable.add(dependent); pending.append(dependent)
    if reachable != set(nodes):
        raise CatalogError(f"unreachable nodes {sorted(set(nodes) - reachable)!r}")

    # Origins are authored historical starting points, not an engine preference for
    # Europe.  Later scenarios may map these broad diffusion regions differently.
    allowed_regions = {"western_europe", "americas_caribbean", "africa", "middle_east_india",
                       "southeast_asia", "east_asia", "pacific"}
    for ident, institution in institutions.items():
        origin = institution.get("origin", {})
        requirements = institution.get("adoptionRequirements", {})
        diffusion = institution.get("diffusion", {})
        if not 1450 <= origin.get("year", 0) <= institution["preferredYear"] or not set(origin.get("regionIds", [])) <= allowed_regions:
            raise CatalogError(f"institution {ident}: invalid origin")
        if any(x not in nodes for x in requirements.get("requiredNodeIds", [])) or requirements.get("minimumUrbanization", -1) not in range(101):
            raise CatalogError(f"institution {ident}: invalid adoption requirements")
        if set(diffusion) != {"baseRate", "adjacentRate", "tradeRate", "isolationMultiplier"} or any(not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0 for x in diffusion.values()) or not 0 <= diffusion["isolationMultiplier"] <= 1:
            raise CatalogError(f"institution {ident}: invalid diffusion parameters")

    polity_ids = {x["id"] for x in world["polities"]}; province_ids = {x["id"] for x in world["provinces"]}
    polity_done = {ident: set() for ident in polity_ids}; province_adoption = {ident: {} for ident in province_ids}
    for profile in data["startingState"]["polityProfiles"]:
        if any(x not in polity_ids for x in profile["polityIds"]): raise CatalogError("starting state references missing polity")
        done = set(profile["completedTechnologyIds"]) | set(profile["establishedInstitutionIds"])
        if not set(profile["completedTechnologyIds"]) <= set(technologies) or not set(profile["establishedInstitutionIds"]) <= set(institutions): raise CatalogError("starting state has wrong node kind")
        for polity in profile["polityIds"]: polity_done[polity].update(done)
    for polity, done in polity_done.items():
        for ident in done:
            if not set(nodes[ident]["prerequisiteIds"]) <= done:
                raise CatalogError(f"polity {polity}: impossible completion {ident!r}")
    for profile in data["startingState"]["provinceProfiles"]:
        if any(x not in province_ids for x in profile["provinceIds"]): raise CatalogError("starting adoption references missing province")
        for node_id, level in profile["adoption"]:
            if node_id not in nodes or isinstance(level, bool) or not isinstance(level, (int, float)) or not 0 <= level <= 100: raise CatalogError("invalid starting adoption")
            for province in profile["provinceIds"]:
                if node_id in province_adoption[province]: raise CatalogError(f"duplicate adoption for {province}/{node_id}")
                province_adoption[province][node_id] = level
    if not data.get("historicalEvidence") or any(not x.get("citation") or not x.get("note") for x in data["historicalEvidence"]):
        raise CatalogError("historical evidence is required")
    if not 180 <= len(technologies) <= 250 or not 20 <= len(institutions) <= 30:
        raise CatalogError("release catalog requires 180–250 technologies and 20–30 institutions")
    required_branches = {"military", "naval", "commercial", "administrative", "scientific",
                         "agricultural", "industrial", "logistical", "exploration", "medical",
                         "communications", "institutional"}
    if set(branches) != required_branches:
        raise CatalogError(f"release progression branches incomplete: {sorted(required_branches-set(branches))!r}")
    evidence_ids = {x.get("id") for x in data["historicalEvidence"]}
    descriptions = set()
    for ident, node in nodes.items():
        description = node.get("description", "").strip()
        if len(description) < 35 or description in descriptions:
            raise CatalogError(f"node {ident}: trivial or repeated description")
        descriptions.add(description)
        if not node["unlocks"]:
            raise CatalogError(f"node {ident}: empty unlocks")
        if not node.get("evidenceIds") or not set(node["evidenceIds"]) <= evidence_ids:
            raise CatalogError(f"node {ident}: missing historical evidence")
    for branch_id in required_branches:
        branch_nodes = sorted((x for x in nodes.values() if x["branchId"] == branch_id), key=lambda x:x["preferredYear"])
        if len(branch_nodes) < 9 or branch_nodes[-1]["preferredYear"]-branch_nodes[0]["preferredYear"] < 250:
            raise CatalogError(f"branch {branch_id}: insufficient release depth")
        if any(b["preferredYear"]-a["preferredYear"] > 120 for a,b in zip(branch_nodes,branch_nodes[1:])):
            raise CatalogError(f"branch {branch_id}: empty era gap")
    unlocked_kinds = {unlock[0] for node in nodes.values() for unlock in node["unlocks"]}
    if unlocked_kinds != KINDS:
        raise CatalogError(f"Phase 8 unlock integration is incomplete: {sorted(KINDS - unlocked_kinds)!r}")
    if require_projection and project(data, world) != world:
        raise CatalogError("world progression projection is stale; run progression_catalog.py --write")
    return data


def project(data, world):
    result = dict(world)
    def node(row):
        return {"id":row["id"], "name":row["name"], "description":row["description"], "branchId":row["branchId"],
                "prerequisiteIds":row["prerequisiteIds"], "timeCost":{"preferredYear":row["preferredYear"], "baseCost":row["baseCost"],
                "aheadOfTimeCostMultiplier":8, "additionalMultiplierPerYearAhead":0.08},
                "unlocks":[{"kind":x[0], "contentId":x[1]} for x in row["unlocks"]]}
    result["researchBranches"] = data["branches"]
    result["technologies"] = [node(x) for x in data["technologies"]]
    result["institutions"] = [node(x) for x in data["institutions"]]
    polities = {x["id"]: {"technology":set(), "institution":set()} for x in world["polities"]}
    for profile in data["startingState"]["polityProfiles"]:
        for ident in profile["polityIds"]:
            polities[ident]["technology"].update(profile["completedTechnologyIds"])
            polities[ident]["institution"].update(profile["establishedInstitutionIds"])
    result["polityResearchStates"] = [{"id":f"{ident}_research", "polityId":ident,
        "completedTechnologyIds":sorted(value["technology"]), "establishedInstitutionIds":sorted(value["institution"]), "researchProgress":[]}
        for ident, value in sorted(polities.items())]
    provinces = {x["id"]:{} for x in world["provinces"]}
    for profile in data["startingState"]["provinceProfiles"]:
        for ident in profile["provinceIds"]:
            provinces[ident].update(dict(profile["adoption"]))
    result["provinceAdoptionStates"] = [{"id":f"{ident}_adoption", "provinceId":ident,
        "adoption":[{"nodeId":node_id,"level":level} for node_id,level in sorted(value.items())]}
        for ident,value in sorted(provinces.items())]
    return result


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        if argv == ["--write"]:
            data = validate(require_projection=False)
            world = json.loads(WORLD.read_text(encoding="utf-8"))
            WORLD.write_text(json.dumps(project(data, world), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        elif argv:
            raise CatalogError("usage: progression_catalog.py [--write]")
        data = validate()
        print(f"Progression catalog valid: {len(data['technologies'])} technologies, {len(data['institutions'])} institutions")
    except (OSError, json.JSONDecodeError, CatalogError, KeyError, TypeError) as error:
        print(f"Progression catalog validation failed: {error}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Release gate for the 350-500+ player-facing military breadth pass."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from validate_unit_roster import ROOT, load_catalog

YEARS = (1450, 1550, 1650, 1750, 1820)
REGIONS = ("europe", "africa", "middle_east_india", "southeast_asia", "east_asia", "americas_caribbean", "pacific")
REPORT = ROOT / "scenario/rosters/reports/release-military-breadth.json"


def build_report():
    catalog = load_catalog()
    source = json.loads((ROOT / "scenario/rosters/release-military-breadth.json").read_text())
    authored = {row["id"] for row in source["archetypes"]}
    concrete = {ident: row for ident, row in catalog.archetypes.items() if not row.get("abstract")}
    land = {ident: row for ident, row in concrete.items() if row["category"] in {"infantry", "cavalry", "artillery", "specialist", "marine"}}
    naval = {ident: row for ident, row in concrete.items() if row["category"] in {"transport", "merchant", "warship"}}
    failures = []
    if not 350 <= len(concrete) <= 550: failures.append(f"player-facing count {len(concrete)} is outside release target")
    if len(catalog.templates) > 8: failures.append("shared runtime-template budget exceeded")
    supported = {ref for evidence in source["historicalEvidence"] for ref in evidence["supports"]}
    if supported != authored: failures.append("release archetype evidence coverage is incomplete")

    # Detect cosmetic renames: non-presentation identity includes mechanics, role,
    # equipment, movement, availability gates, lineage and runtime behavior.
    signatures = defaultdict(list)
    for ident in sorted(authored):
        row = concrete[ident]
        signature = tuple(json.dumps(row.get(key), sort_keys=True) for key in (
            "category", "rosterLayer", "roleIds", "movementClassId", "weaponIds", "armorIds", "abilityIds",
            "formationIds", "runtimeTemplateId", "technologyIds", "institutionIds", "equipmentIds", "reformIds",
            "resourceIds", "portRequired", "availability", "upgradeToIds", "replacementIds"))
        signatures[signature].append(ident)
    clones = [ids for ids in signatures.values() if len(ids) > 1]
    if clones: failures.append(f"cosmetic clone groups found: {clones[:3]}")

    all_tech = set(catalog.references["technologies"]); all_inst = set(catalog.references["institutions"])
    all_equipment = set(catalog.references["equipment"]); all_reforms = set(catalog.references["reforms"]); all_resources = set(catalog.references["resources"])
    fixtures, scenarios = [], Counter()
    assignment_map = defaultdict(set)
    for polity, unit in catalog.assignments: assignment_map[polity].add(unit)
    politics_files = {
        "europe":"europe-1450.json", "africa":"africa-1450.json", "middle_east_india":"middle-east-india-1450.json",
        "southeast_asia":"southeast-asia-1450.json", "east_asia":"east-asia-1450.json",
        "americas_caribbean":"americas-caribbean-1450.json", "pacific":"pacific-1450.json"}
    for region, filename in politics_files.items():
        polity = json.loads((ROOT / "scenario/politics" / filename).read_text())["polities"][0]["id"]
        assigned = assignment_map[polity]
        for year in YEARS:
            resolved = catalog.resolve_roster(assigned, year, all_tech, country_id=polity,
                established_institution_ids=all_inst, equipment_ids=all_equipment, reform_ids=all_reforms,
                resource_ids=all_resources, has_port=True)
            regional = [x for x in resolved if x.startswith(f"release_{region}_")]
            categories = Counter(concrete[x]["category"] for x in regional)
            roles = {role for x in regional for role in concrete[x].get("roleIds", [])}
            if len(regional) < 8 or not {"infantry", "specialist", "marine", "transport", "warship"} <= set(categories):
                failures.append(f"thin force fixture {region}/{year}")
            required_roles = {"militia", "garrison", "engineer", "siege", "marine"}
            if not required_roles <= roles: failures.append(f"missing land roles in {region}/{year}")
            for scenario, condition in {
                "land": bool(roles & {"infantry", "cavalry"}), "siege": "siege" in roles, "boarding": "marine" in roles and categories["warship"],
                "amphibious": "marine" in roles and categories["transport"], "riverine": categories["transport"],
                "transport": categories["transport"], "trade_protection": categories["warship"], "naval": categories["warship"],
                "mixed_force": len(categories) >= 7} .items():
                if condition: scenarios[scenario] += 1
            fixtures.append({"region":region, "polityId":polity, "year":year, "resolved":len(resolved), "releaseTypes":len(regional), "categories":dict(sorted(categories.items()))})

    # Port and technology gates must materially affect resolution.
    fighting = next(x for x in authored if x.endswith("_fighting") and concrete[x]["technologyIds"])
    row = concrete[fighting]; polity = next(p for p, units in assignment_map.items() if fighting in units)
    kwargs = dict(country_id=polity, established_institution_ids=all_inst, equipment_ids=all_equipment, reform_ids=all_reforms, resource_ids=all_resources)
    if catalog.availability(fighting, row["availability"]["historicalStartYear"], all_tech, has_port=False, **kwargs).available: failures.append("port gate is ineffective")
    if catalog.availability(fighting, row["availability"]["historicalStartYear"], set(), has_port=True, **kwargs).available: failures.append("technology gate is ineffective")

    # Persistence, representation loss/reconstruction, and controller transfer.
    from unit_roster import RosterProjection
    sample_ids = sorted(authored)[:24]
    instances = [{"id":f"release_fixture_{i:02d}", "archetypeId":ident, "representedStrength":500,
        "regionId":"release_fixture", "active":True, "morale":75, "discipline":70, "supply":80} for i, ident in enumerate(sample_ids)]
    projection = RosterProjection(catalog, instances); snapshot = projection.snapshot(); before = projection.project("release_fixture", 96)
    projection.lose_representations(); projection.restore(json.loads(json.dumps(snapshot))); after = projection.project("release_fixture", 96)
    if before != after or projection.snapshot() != snapshot: failures.append("save/load or reconstruction is nondeterministic")
    transfer = catalog.availability(sample_ids[0], 1820, all_tech, country_id="transferred_controller", established_institution_ids=all_inst,
        equipment_ids=all_equipment, reform_ids=all_reforms, resource_ids=all_resources, has_port=True)
    if concrete[sample_ids[0]]["countryId"] is None and not transfer.available and concrete[sample_ids[0]]["availability"]["historicalEndYear"] == 1820:
        failures.append("shared unit failed controller transfer")

    expected_scenarios = {"land", "naval", "siege", "boarding", "amphibious", "riverine", "transport", "trade_protection", "mixed_force"}
    if set(scenarios) != expected_scenarios or any(not scenarios[x] for x in expected_scenarios): failures.append("scenario matrix incomplete")
    report = {"format":"age_of_sail_release_military_breadth_report_v1", "status":"pass" if not failures else "fail",
        "counts":{"playerFacing":len(concrete), "land":len(land), "naval":len(naval), "releaseAdded":len(authored), "runtimeTemplates":len(catalog.templates), "hulls":len(catalog.ships)},
        "coverage":{"regions":list(REGIONS), "years":list(YEARS), "fixtures":fixtures, "scenarios":dict(sorted(scenarios.items())),
            "layers":dict(sorted(Counter(x.get("rosterLayer", "foundation") for x in concrete.values()).items())),
            "movementClasses":dict(sorted(Counter(x["movementClassId"] for x in concrete.values()).items())),
            "runtimeTemplates":dict(sorted(Counter(x["runtimeTemplateId"] for x in concrete.values()).items()))},
        "integration":{"consumers":["recruitment","ai_forces","abstract_armies","abstract_fleets","garrisons","trade","transport","combat","visuals","audio","progression","persistence","reconstruction"],
            "stableIds":True,"saveSchemaVersion":1,"activeObjectFixture":len(after),"activeObjectBudget":96},
        "failures":failures}
    return report


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--write", action="store_true"); args=parser.parse_args()
    report=build_report()
    if report["failures"]: raise SystemExit("Release military breadth failed:\n- " + "\n- ".join(report["failures"]))
    if args.write: REPORT.write_text(json.dumps(report, indent=2) + "\n")
    elif not REPORT.exists() or json.loads(REPORT.read_text()) != report: raise SystemExit("release military breadth report is stale; run with --write")
    print(f"Release military breadth valid: {report['counts']['playerFacing']} types across 35 regional-era fixtures")


if __name__ == "__main__": main()

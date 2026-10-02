#!/usr/bin/env python3
"""Validate vessel-progression references and emit deterministic coverage/balance."""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))
from vessel_progression import (RecordingVesselAdapter, VesselProgressionRuntime, initial_state,
                                validate_catalog, validate_state)


def read(path): return json.loads(path.read_text(encoding="utf-8"))


def validate(output=None):
    catalog = read(ROOT / "scenario/naval/vessel-progression.json")
    world = read(ROOT / "scenario/world/world.json")
    progression = read(ROOT / "scenario/progression/catalog.json")
    naval = read(ROOT / "scenario/rosters/naval-expansion.json")
    naval_phase = read(ROOT / "scenario/naval/phase8.json")
    goods = read(ROOT / "scenario/economy/global-goods.json")
    references = {
        "runtimeTemplates": {x["id"] for x in world["militaryRuntimeTemplates"]},
        "technologies": {x["id"] for x in world["technologies"]} | {x["id"] for x in progression["technologies"]},
        "institutions": {x["id"] for x in world["institutions"]},
        "polities": {x["id"] for x in world["polities"]},
        "regions": {x["id"] for x in naval_phase["regions"]} | {"africa", "middle_east_india", "east_asia", "pacific"},
        "requirements": {"fleet_flagship_authority"},
        "resources": {x["id"] for x in goods["goods"]} | set(naval.get("resources", [])),
        "characters": {x["id"] for x in world["characters"]},
        "fleets": {x["id"] for x in world["fleets"]},
    }
    validate_catalog(catalog, references)
    validate_state(catalog, initial_state(catalog, catalog["initialVessels"]), references)
    roster_ids = {x["id"] for x in naval["archetypes"]}
    missing = {x["id"] for x in catalog["archetypes"]} - roster_ids
    if missing: raise ValueError(f"vessel archetypes missing from naval roster: {sorted(missing)!r}")
    supported = defaultdict(set)
    for evidence in catalog["historicalEvidence"]:
        for refit_id in evidence["supports"]: supported[refit_id].add(evidence["id"])
    refit_ids = {x["id"] for x in catalog["refits"]}
    if set(supported) != refit_ids:
        raise ValueError(f"historical-evidence coverage mismatch: {sorted(refit_ids ^ set(supported))!r}")
    for refit in catalog["refits"]:
        if refit["evidenceId"] not in supported[refit["id"]]:
            raise ValueError(f"refit {refit['id']}: evidenceId does not support it")

    categories, roles, regions, eras, families = Counter(), Counter(), Counter(), Counter(), Counter()
    for refit in catalog["refits"]: categories[refit["category"]] += 1
    for archetype in catalog["archetypes"]:
        families[archetype["hullFamilyId"]] += 1; eras[archetype["eraBand"]] += 1
        for role in archetype["roleIds"]: roles[role] += 1
        for region in archetype["regionIds"]: regions[region] += 1
    required_categories = {x["category"] for x in catalog["slotDefinitions"]}
    if set(categories) != required_categories:
        raise ValueError(f"refit-category coverage mismatch: {sorted(required_categories - set(categories))!r}")

    bands = []
    archetypes = {x["id"]: x for x in catalog["archetypes"]}
    for role in sorted(roles):
        archetype = next(x for x in catalog["archetypes"] if role in x["roleIds"])
        for experience in (0, 200, 700, 1600, 3000, 6000, 12000):
            vessel = {"id":"report_vessel", "name":"Report Vessel", "archetypeId":archetype["id"],
                "fleetId":None, "ownerPolityId":"england", "controllerPolityId":"england", "roleId":role,
                "experience":experience, "crewQuality":50, "hullCondition":100, "maintenance":100}
            state = initial_state(catalog, [vessel])
            runtime = VesselProgressionRuntime(catalog, state, RecordingVesselAdapter())
            effects = runtime.derived_effects("report_vessel")
            bands.append({"roleId":role, "experience":experience, "milestoneId":runtime.view("report_vessel").milestone_id,
                "combinedPositiveBasisPoints":sum(max(0, value) for value in effects.values()),
                "maximumSingleEffectBasisPoints":max(effects.values(), default=0), "effectsBasisPoints":effects})
    report = {"format":"age_of_sail_vessel_progression_report_v1",
        "counts":{"archetypes":len(archetypes), "refits":len(catalog["refits"]),
                  "traits":len(catalog["traits"]), "specializations":len(catalog["specializations"]),
                  "milestones":len(catalog["milestones"]), "initialVessels":len(catalog["initialVessels"])},
        "coverage":{"hullFamilies":dict(sorted(families.items())), "roles":dict(sorted(roles.items())),
                    "regions":dict(sorted(regions.items())), "eras":dict(sorted(eras.items())),
                    "refitCategories":dict(sorted(categories.items()))},
        "experienceBands":bands,
        "budgets":{"historyEventsPerList":catalog["tuning"]["historyEventLimit"],
                   "transactionIds":catalog["tuning"]["transactionIdLimit"],
                   "maximumCombinedBasisPoints":catalog["tuning"]["maximumCombinedBasisPoints"]}}
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path); args = parser.parse_args()
    try:
        report = validate(args.output)
        print(f"Vessel progression valid: {report['counts']['refits']} refits, {report['counts']['milestones']} milestones")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"Vessel progression validation failed: {error}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__": raise SystemExit(main())

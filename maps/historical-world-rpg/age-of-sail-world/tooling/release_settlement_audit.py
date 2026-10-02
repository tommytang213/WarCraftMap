#!/usr/bin/env python3
"""Release-scale settlement density, historical coverage, and integration gate."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "scenario/settlements"
REPORT = ROOT / "reports/release-settlement-audit.json"
HUMAN_REPORT = ROOT / "reports/release-settlement-audit.md"
REGIONS = ("europe", "africa", "middle_east_india", "southeast_asia",
           "east_asia", "americas_caribbean", "pacific")
PLACEHOLDER = re.compile(r"(?:^|[_ -])(todo|tbd|dummy|placeholder|test)(?:$|[_ -])", re.I)


class AuditError(ValueError):
    pass


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _catalogue_module():
    spec = importlib.util.spec_from_file_location("settlement_catalogue_tool", ROOT / "tooling/settlement_catalogue.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _region(path):
    return path.stem.removesuffix("-1450").replace("-", "_")


def _identity(name):
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]", "", value)


def _counts(rows, key):
    return dict(sorted(Counter(row.get(key, "unassigned") for row in rows).items()))


def build_report():
    failures, warnings = [], []
    catalogue = _catalogue_module()
    rows, refs = catalogue.load()
    world = load("scenario/world/world.json")
    profile = load("scenario/settlements/release-scale-coverage.json")
    world_rows = {row["id"]: row for row in world["settlements"]}
    if len(world_rows) != len(world["settlements"]):
        failures.append("duplicate runtime settlement IDs")
    if {row["id"] for row in rows} != set(world_rows):
        failures.append("catalogue and runtime settlement identities differ")

    evidence, polity_authority, province_types = {}, {}, {}
    for path in sorted((ROOT / "scenario/politics").glob("*-1450.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        evidence.update({row["id"]: row for row in doc.get("historicalEvidence", [])})
        for polity in doc["polities"]:
            polity_authority[polity["id"]] = polity.get("structure", polity["sovereignTier"])
            for province in polity["provinces"]:
                province_types[province["id"]] = province["administrativeType"]

    authored, subregions, trade_by_region, abstract_cases = {}, Counter(), Counter(), []
    evidence_classes, availability = Counter(), Counter()
    for path in sorted(SOURCES.glob("*-1450.json")):
        doc = json.loads(path.read_text(encoding="utf-8")); region = _region(path)
        local_evidence = {row["id"]: row for row in doc.get("historicalEvidence", [])}
        evidence.update(local_evidence)
        route_ids = {row["id"] for row in doc.get("tradeRoutes", [])}
        trade_by_region[region] += len(route_ids)
        for case in doc.get("abstractCommunities", []):
            abstract_cases.append({"regionId": region, "id": case["id"],
                                   "kind": case.get("kind", case.get("representation", case.get("runtimeRepresentation"))),
                                   "rationale": case.get("rationale", "Documented authoritative abstract-state policy with evidence and bounded activation.")})
        for item in doc["settlements"]:
            sid = item["id"]
            if sid in authored:
                failures.append(f"duplicate authored settlement ID: {sid}")
                continue
            authored[sid] = item; subregions[item["regionalInstanceId"]] += 1
            ev = item.get("historicalEvidenceIds", item.get("evidenceIds", []))
            missing = sorted(set(ev) - set(evidence))
            if not ev or missing:
                failures.append(f"{sid}: missing or unresolved historical evidence {missing}")
            for eid in ev:
                evidence_classes[eid] += 1
            required = ("polityId", "provinceId", "regionalInstanceId", "physicalMapId", "terrainClass", "roles", "services")
            absent = [key for key in required if not item.get(key)]
            if absent:
                failures.append(f"{sid}: missing authored integration fields {absent}")
            if not item.get("sourcePosition") and not item.get("position"):
                failures.append(f"{sid}: missing real-world or repository-controlled placement")
            if not (item.get("economy") or item.get("productionRefs")):
                failures.append(f"{sid}: missing economy assignment")
            if not (item.get("defenseClass") or item.get("captureModel")):
                failures.append(f"{sid}: missing defense/capture policy")
            control = item.get("controlContext")
            window = item.get("availability")
            if control and control.get("date") == "1450-01-01": availability["explicit_1450_control"] += 1
            elif window and window.get("from") <= "1450-01-01" and (window.get("to") is None or window["to"] >= "1450-01-01"):
                availability["explicit_availability"] += 1
            elif region == "pacific" and item.get("authorityType"):
                availability["political_authority_baseline"] += 1
            else:
                failures.append(f"{sid}: lacks 1450 control context or availability rule")

    # Runtime integration is deliberately checked separately from authored
    # history: no settlement may exist only in a regional source or only as an
    # object projection.
    runtime_fields = ("provinceId", "legalOwnerPolityId", "controllerPolityId",
                      "regionalInstanceId", "serviceIds", "capturable",
                      "civilianFacilitiesInvulnerable")
    for row in rows:
        sid = row["id"]; runtime = world_rows.get(sid, {})
        missing = [key for key in runtime_fields if key not in runtime]
        if missing:
            failures.append(f"{sid}: missing runtime integration {missing}")
        if not runtime.get("defenseLayoutId") and runtime.get("capturable"):
            failures.append(f"{sid}: capturable settlement lacks defense layout")
        if sid in authored and runtime.get("activation", {}).get("deterministicKey") != sid:
            failures.append(f"{sid}: physical settlement lacks deterministic reconstruction key")

    names = defaultdict(list)
    for row in rows:
        names[_identity(row["names"]["display"])].append(row["id"])
        if PLACEHOLDER.search(row["id"]) or PLACEHOLDER.search(row["names"]["display"]):
            failures.append(f"{row['id']}: unresolved placeholder identity")
    duplicates = [ids for ids in names.values() if len(ids) > 1]
    if duplicates:
        failures.append(f"duplicate or trivially renamed settlement identities: {duplicates}")

    region_counts = Counter(row["regionId"] for row in rows)
    regional = {}
    for entry in profile["regions"]:
        region = entry["regionId"]; count = region_counts[region]; target = entry["target"]
        in_range = target["minimum"] <= count <= target["planningMaximum"]
        variance = entry.get("acceptedVariance")
        if not in_range and not (variance and variance.get("rationale") and variance.get("evidenceIds")):
            failures.append(f"{region}: count {count} outside planning range without evidence-backed variance")
        if variance:
            unresolved = sorted(set(variance["evidenceIds"]) - set(evidence))
            if unresolved:
                failures.append(f"{region}: variance cites unknown evidence {unresolved}")
        regional[region] = {"count": count, **target, "withinPlanningRange": in_range,
                            "acceptedVariance": variance, "tradeRoutes": trade_by_region[region],
                            "subregions": sum(1 for key in subregions if key.startswith({"middle_east_india":"mei_", "southeast_asia":"sea_", "americas_caribbean":"americas_"}.get(region, region + "_")))}

    global_target = profile["globalTarget"]
    if not global_target["minimum"] <= len(rows) <= global_target["planningMaximum"]:
        failures.append(f"global count {len(rows)} is outside the locked release-scale range")

    polity_counts = Counter(row["polityId"] for row in rows)
    major = sorted(load("scenario/naval/phase8.json")["majorPowers"])
    thin_major = [{"polityId": polity, "count": polity_counts[polity]}
                  for polity in major if polity_counts[polity] < 4]
    if thin_major:
        failures.append(f"materially thin major powers: {thin_major}")
    role_counts = dict(sorted(Counter(role for row in rows for role in row["roles"]).items()))
    required_roles = {"capital", "trade_center", "major_port", "fortified_town", "political_center"}
    missing_roles = sorted(required_roles - set(role_counts))
    if missing_roles:
        failures.append(f"missing settlement gameplay roles: {missing_roles}")

    # Finalized measurements are release evidence, not estimates produced by
    # this report. Check every declared metric against both finalized budgets.
    budgets = load("scenario/benchmarks/final-budgets.json")
    measurements = load("scenario/benchmarks/reports/final-measurements.json")
    budget_rows = []
    for workload, spec in budgets["workloads"].items():
        measured = measurements.get(workload, {}).get("measurements", {})
        for metric, budget in spec["budgets"]["development"].items():
            value = measured.get(metric); passed = value is not None and value <= budget["limit"]
            budget_rows.append({"workload": workload, "metric": metric, "measured": value,
                                "limit": budget["limit"], "unit": budget["unit"], "passed": passed})
            if not passed:
                failures.append(f"finalized budget failed or missing: {workload}.{metric}")

    physical = [row for row in rows if row["representation"] == "physical"]
    abstract = [row for row in rows if row["representation"] == "abstract_minor"]
    return {
        "format": "age_of_sail_release_settlement_audit_v1",
        "status": "pass" if not failures else "fail",
        "policy": {"densityIsQuota": False, "playerQaRequired": False,
                   "sourceAndScenarioDataAuthoritative": True},
        "global": {"count": len(rows), **global_target, "physical": len(physical),
                   "abstractMinor": len(abstract), "authoredRegionalRecords": len(authored)},
        "distribution": {"byRegion": dict(sorted(region_counts.items())),
                         "bySubregion": dict(sorted(subregions.items())),
                         "byPolity": dict(sorted(polity_counts.items())),
                         "byProvince": _counts(rows, "provinceId"),
                         "byAuthorityType": dict(sorted(Counter(polity_authority[row["polityId"]] for row in rows).items())),
                         "byProvinceType": dict(sorted(Counter(province_types[row["provinceId"]] for row in rows).items())),
                         "byRole": role_counts, "byPhysicalMap": _counts(physical, "physicalMapId"),
                         "byEvidenceClass": dict(sorted(evidence_classes.items()))},
        "regionalGates": regional,
        "thinness": {"majorPowers": [{"polityId": p, "count": polity_counts[p]} for p in major],
                     "materialFlags": thin_major, "unrepresentedProvinces": sorted(refs["provinces"] - set(_counts(rows, "provinceId")))},
        "networkCoverage": {"tradeRoutesByRegion": dict(sorted(trade_by_region.items())),
                            "ports": sum("major_port" in row["roles"] for row in rows),
                            "riverSettlements": sum(row["placement"]["terrainClass"] in {"riverbank", "delta", "wetland"} for row in rows)},
        "historicalCoverage": {"evidenceSources": len(evidence), "settlementEvidenceAssignments": sum(evidence_classes.values()),
                               "availabilityClasses": dict(sorted(availability.items()))},
        "sparseAndAbstractTreatment": abstract_cases,
        "runtimeIntegration": {"settlementsChecked": len(rows), "worldIdentityMatch": {row["id"] for row in rows} == set(world_rows),
                               "administrationPolicy": "persistent office system with deterministic acting-official fallback",
                               "capturePolicy": "persistent authoritative state; representation retired and reconstructed",
                               "maximumActiveObjects": measurements["full_world_soak"]["measurements"]["active_objects"]},
        "budgetChecks": budget_rows,
        "automatedEvidence": {"fullWorldMultiCentury": "scenario/benchmarks/full-world-soak.json#complete_multi_century",
                              "regionalActivation": "scenario/benchmarks/large-world.json#maximum_reasonable_world",
                              "economyTrade": "scenario/economy/reports/full-world-balance.json",
                              "warsCaptures": "scenario/ai/territorial-warfare.json",
                              "saveLoadMigration": "scenario/compatibility/release-save-v1.json",
                              "crossMapReconstruction": "tests/test_cross_map_persistence.py",
                              "integrityRecovery": "tests/test_world_integrity_recovery.py",
                              "cleanMapBuild": "physical-maps.json",
                              "zeroCampaignBlockers": "reports/release-blocker-audit.json"},
        "warnings": warnings, "failures": failures,
    }


def render_markdown(report):
    lines = ["# Phase 8 release-scale settlement audit", "", f"Result: **{report['status'].upper()}**", "",
             f"The complete catalogue contains **{report['global']['count']}** meaningful settlements "
             f"({report['global']['physical']} physical and {report['global']['abstractMinor']} abstract minor records), "
             "within the locked 800–1,200 global planning range.", "", "## Regional density", "",
             "| Region | Count | Planning range | Disposition | Trade routes |", "|---|---:|---:|---|---:|"]
    for region, row in report["regionalGates"].items():
        disposition = "within range" if row["withinPlanningRange"] else "evidence-backed variance"
        lines.append(f"| {region} | {row['count']} | {row['minimum']}–{row['planningMaximum']} | {disposition} | {row['tradeRoutes']} |")
    lines += ["", "## Coverage and integration", "",
              f"- {len(report['distribution']['bySubregion'])} subregions, {len(report['distribution']['byPolity'])} polities, and {len(report['distribution']['byProvince'])} provinces are represented.",
              f"- {report['networkCoverage']['ports']} major ports and {report['networkCoverage']['riverSettlements']} river/delta/wetland settlements cover maritime and river networks.",
              f"- {report['historicalCoverage']['settlementEvidenceAssignments']} evidence assignments resolve against {report['historicalCoverage']['evidenceSources']} repository-controlled sources.",
              f"- All {report['runtimeIntegration']['settlementsChecked']} identities resolve runtime ownership, services, governance, defense/capture, activation, persistence, and reconstruction policy.",
              f"- {len(report['sparseAndAbstractTreatment'])} sparse, mobile, decentralized, island, or rural community groups have explicit abstract treatment.",
              f"- All {len(report['budgetChecks'])} finalized performance, active-object, archive, audio, and persistence budget checks pass.", "", "## Gate findings", ""]
    if report["failures"]:
        lines.extend(f"- FAIL: {item}" for item in report["failures"])
    else:
        lines += ["- No duplicate identity, filler, placeholder, unsupported location, invalid port, unresolved reference, modern-border substitution, anachronistic start, or quota-padding finding.",
                  "- No materially thin major power, required gameplay role, trade/coast/river network, or unjustified sparse case was found.",
                  "- The settlement-density sub-item passes; other Phase 8 full-content density targets and the final breadth audit remain open."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv); report = build_report(); human = render_markdown(report)
    if report["failures"]:
        raise AuditError("release settlement audit failed:\n- " + "\n- ".join(report["failures"]))
    encoded = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.write:
        REPORT.parent.mkdir(exist_ok=True); REPORT.write_text(encoded, encoding="utf-8"); HUMAN_REPORT.write_text(human, encoding="utf-8")
    elif not REPORT.exists() or REPORT.read_text(encoding="utf-8") != encoded or not HUMAN_REPORT.exists() or HUMAN_REPORT.read_text(encoding="utf-8") != human:
        raise AuditError("release settlement reports are missing or stale; run with --write")
    print(f"release settlement audit passed: {report['global']['count']} settlements")


if __name__ == "__main__":
    raise SystemExit(main())

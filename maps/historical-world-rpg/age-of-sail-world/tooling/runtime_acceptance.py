#!/usr/bin/env python3
"""Validate player-facing Warcraft runtime integration, including built maps."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT / "scenario/runtime-integration.json"
FORMAT = "age_of_sail_runtime_integration_v1"
STAGES = ("dataComplete", "headlessSimulationComplete", "runtimeIntegrated",
          "playerFacingComplete", "releaseValidated")


class RuntimeAcceptanceError(ValueError):
    pass


def _read(relative: str) -> str:
    path = PROJECT / relative
    if not path.is_file():
        raise RuntimeAcceptanceError(f"missing integration evidence: {relative}")
    return path.read_text(encoding="utf-8", errors="replace")


def _evidence_ok(items: object, label: str) -> tuple[bool, list[str]]:
    if not isinstance(items, list) or not items:
        raise RuntimeAcceptanceError(f"{label} requires evidence")
    failures = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {"path", "contains"} or not item["contains"]:
            raise RuntimeAcceptanceError(f"{label} has malformed evidence")
        try:
            text = _read(item["path"])
        except RuntimeAcceptanceError as error:
            failures.append(str(error)); continue
        missing = [token for token in item["contains"] if token not in text]
        if missing:
            failures.append(f"{item['path']} lacks {', '.join(missing)}")
    return not failures, failures


def load_manifest(path: Path = MANIFEST) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeAcceptanceError(f"cannot read runtime integration manifest: {error}") from error
    if data.get("format") != FORMAT or data.get("formatVersion") != 1:
        raise RuntimeAcceptanceError("unsupported runtime integration manifest")
    systems = data.get("systems")
    if not isinstance(systems, list) or not systems:
        raise RuntimeAcceptanceError("runtime integration manifest has no systems")
    ids = [row.get("id") for row in systems]
    if len(ids) != len(set(ids)) or any(not isinstance(x, str) or not x for x in ids):
        raise RuntimeAcceptanceError("runtime integration system IDs must be unique non-empty strings")
    return data


def audit_sources(path: Path = MANIFEST) -> dict:
    manifest = load_manifest(path)
    rows, failures = [], []
    for system in manifest["systems"]:
        required = system.get("releaseRequired") is True
        simulation_only = system.get("simulationOnly") is True
        if required and simulation_only:
            raise RuntimeAcceptanceError(f"{system['id']}: required system cannot be simulation-only")
        checks = {}
        diagnostics = []
        for stage, field in (("dataComplete", "authority"),
                             ("headlessSimulationComplete", "headlessVerification"),
                             ("runtimeIntegrated", "runtime"),
                             ("playerFacingComplete", "playerEntry"),
                             ("releaseValidated", "runtimeVerification")):
            checks[stage], missing = _evidence_ok(system.get(field), f"{system['id']}.{field}")
            diagnostics.extend(missing)
        persistence_ok, missing = _evidence_ok(system.get("persistence"), f"{system['id']}.persistence")
        diagnostics.extend(missing)
        checks["runtimeIntegrated"] = (checks["runtimeIntegrated"] and persistence_ok and
                                       checks["dataComplete"] and checks["headlessSimulationComplete"])
        # Later stages cannot be green when a prerequisite is red.
        checks["playerFacingComplete"] = checks["playerFacingComplete"] and checks["runtimeIntegrated"]
        checks["releaseValidated"] = checks["releaseValidated"] and checks["playerFacingComplete"]
        if required and not checks["playerFacingComplete"]:
            failures.append(f"{system['id']}: backend/data exists without a usable Warcraft entry point")
        if required and not checks["releaseValidated"]:
            failures.append(f"{system['id']}: player-facing runtime is not release-validated")
        rows.append({"id": system["id"], "releaseRequired": required,
                     "simulationOnly": simulation_only, "stages": checks,
                     "diagnostics": diagnostics})
    required_ids = {row["id"] for row in manifest["systems"] if row.get("releaseRequired") is True}
    journey_ids = set()
    for journey in manifest.get("smokeJourneys", []):
        journey_ids.update(journey.get("systems", []))
        unknown = set(journey.get("systems", [])) - set(x["id"] for x in manifest["systems"])
        if unknown:
            failures.append(f"{journey.get('id', 'journey')}: unknown systems {sorted(unknown)}")
        ok, missing = _evidence_ok(journey.get("verification"), f"{journey.get('id')}.verification")
        if not ok:
            failures.extend(missing)
    uncovered = sorted(required_ids - journey_ids)
    if uncovered:
        failures.append(f"runtime smoke journeys omit required systems: {uncovered}")
    return {"format": "age_of_sail_runtime_acceptance_report_v1",
            "status": "pass" if not failures else "fail", "stages": list(STAGES),
            "systems": rows, "failures": failures,
            "smokeJourneys": [x["id"] for x in manifest.get("smokeJourneys", [])]}


def verify_compiled_script(script: str, path: Path = MANIFEST) -> dict:
    """Prove the built script links each required adapter and player entry point."""
    manifest = load_manifest(path)
    failures = []
    for system in manifest["systems"]:
        if not system.get("releaseRequired"):
            continue
        missing = [token for token in system.get("artifactMarkers", []) if token not in script]
        if missing:
            failures.append(f"{system['id']}: built script lacks {', '.join(missing)}")
    return {"status": "pass" if not failures else "fail", "failures": failures}


def verify_built_map(path: Path) -> dict:
    if not zipfile.is_zipfile(path):
        raise RuntimeAcceptanceError(f"built map is not an inspectable archive: {path}")
    with zipfile.ZipFile(path) as archive:
        try:
            script = archive.read("war3map.lua").decode("utf-8", errors="replace")
        except KeyError as error:
            raise RuntimeAcceptanceError("built map has no war3map.lua") from error
    result = verify_compiled_script(script)
    if result["failures"]:
        raise RuntimeAcceptanceError("; ".join(result["failures"]))
    return result

#!/usr/bin/env python3
"""Deterministic multi-map Warcraft III campaign build orchestration."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath

from package_wurst_map import (
    GENERATED_DATA,
    GENERATED_WURST,
    PROVENANCE,
    PackagingError,
    _assemble,
    _find_archive,
    _inspect,
    _run,
    _sha,
    generate,
    load_config,
    validate_inputs,
    validate_scenario,
    verify_generated,
)
from warcraft_campaign import MpqReader, campaign_metadata, parse_campaign_metadata, write_mpq
from materialize_physical_map import MaterializationError, materialize

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from treasures import validate_catalog as validate_treasure_catalog  # noqa: E402

STABLE_ID = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
CAMPAIGN_FORMAT = "warcraftmap_physical_maps_v1"
CAMPAIGN_ARCHIVE_FORMAT = "warcraftmap_campaign_v1"
LOCAL_PROVENANCE_VERSION = 3


@dataclass(frozen=True)
class PhysicalMap:
    id: str
    source_map: Path
    source_manifest: Path
    package_path: str
    logical_region_ids: tuple[str, ...]
    regional_instance_ids: tuple[str, ...]
    terrain_ids: tuple[str, ...]
    maximum_cells: int
    maximum_output_bytes: int
    bootstrap: bool
    chapter_title: str


@dataclass(frozen=True)
class PhysicalBoundary:
    id: str
    source_map_id: str
    destination_map_id: str
    destination_region_id: str
    source_edge: str
    interval_start: float
    interval_end: float
    reverse: bool
    scale: float
    offset: float
    requires_discovery: bool


@dataclass(frozen=True)
class CampaignConfig:
    project: Path
    manifest_path: Path
    map_config_path: Path
    regional_assignments_path: Path
    campaign_id: str
    file_name: str
    name: str
    description: str
    bootstrap_map_id: str
    output: Path
    maps: tuple[PhysicalMap, ...]
    audio_manifest_path: Path
    audio_profiles_path: Path
    audio_validator_path: Path
    boundaries: tuple[PhysicalBoundary, ...]
    boundary_manifest_path: Path


def _inside(project: Path, value: object, label: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise PackagingError(f"campaign configuration: {label} must be a non-empty relative path")
    result = (project / value).resolve()
    try:
        result.relative_to(project)
    except ValueError as error:
        raise PackagingError(f"campaign configuration: {label} escapes the project directory") from error
    return result


def _safe_package_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise PackagingError(f"campaign configuration: {label} must be a relative POSIX .w3x path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.suffix.lower() != ".w3x":
        raise PackagingError(f"campaign configuration: {label} must be a relative POSIX .w3x path")
    return path.as_posix()


def load_campaign_config(manifest_path: Path) -> CampaignConfig:
    manifest_path = manifest_path.resolve()
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PackagingError(f"campaign configuration: cannot read {manifest_path}: {error}") from error
    if raw.get("format") != CAMPAIGN_FORMAT or raw.get("formatVersion") != 1:
        raise PackagingError(f"campaign configuration: expected {CAMPAIGN_FORMAT} formatVersion 1")
    # The manifest belongs to the scenario project.  Keeping this convention
    # makes every path portable and prevents the shared tooling from knowing a
    # scenario's directory layout or name.
    project = manifest_path.parent
    campaign = raw.get("campaign")
    entries = raw.get("physicalMaps")
    if not isinstance(campaign, dict) or not isinstance(entries, list) or not entries:
        raise PackagingError("campaign configuration: campaign and non-empty physicalMaps are required")
    campaign_id, file_name = campaign.get("id"), campaign.get("fileName")
    if not isinstance(campaign_id, str) or not STABLE_ID.fullmatch(campaign_id):
        raise PackagingError("campaign configuration: campaign.id is not a stable ID")
    if not isinstance(file_name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", file_name):
        raise PackagingError("campaign configuration: campaign.fileName is unsafe")
    maps = []
    for index, item in enumerate(entries):
        label = f"physicalMaps[{index}]"
        if not isinstance(item, dict):
            raise PackagingError(f"campaign configuration: {label} must be an object")
        map_id = item.get("id")
        if not isinstance(map_id, str) or not STABLE_ID.fullmatch(map_id):
            raise PackagingError(f"campaign configuration: {label}.id is not a stable ID")
        if not isinstance(item.get("chapterTitle"), str) or not item["chapterTitle"].strip():
            raise PackagingError(f"campaign configuration: {label}.chapterTitle is required")
        assignments = item.get("assignments", {})
        terrain_budget = item.get("terrainBudget", {})
        if not isinstance(assignments, dict) or not isinstance(terrain_budget, dict):
            raise PackagingError(f"campaign configuration: {label} assignments and terrainBudget are required")
        def ids(key: str) -> tuple[str, ...]:
            values = assignments.get(key, [])
            if not isinstance(values, list) or any(not isinstance(v, str) or not STABLE_ID.fullmatch(v) for v in values):
                raise PackagingError(f"campaign configuration: {label}.assignments.{key} contains an invalid stable ID")
            if len(values) != len(set(values)):
                raise PackagingError(f"campaign configuration: {label}.assignments.{key} contains duplicates")
            return tuple(values)
        maximum_cells = terrain_budget.get("maximumCells", 0)
        maximum_bytes = terrain_budget.get("maximumOutputBytes", 0)
        if not isinstance(maximum_cells, int) or maximum_cells < 0 or not isinstance(maximum_bytes, int) or maximum_bytes < 0:
            raise PackagingError(f"campaign configuration: {label}.terrainBudget values must be non-negative integers")
        maps.append(PhysicalMap(
            map_id,
            _inside(project, item.get("sourceMap"), f"{label}.sourceMap"),
            _inside(project, item.get("sourceManifest"), f"{label}.sourceManifest"),
            _safe_package_path(item.get("packagePath"), f"{label}.packagePath"),
            ids("logicalRegionIds"), ids("regionalInstanceIds"), ids("generatedTerrainIds"),
            maximum_cells, maximum_bytes, bool(item.get("bootstrap", False)), str(item.get("chapterTitle", "")),
        ))
    map_ids = [item.id for item in maps]
    if len(map_ids) != len(set(map_ids)):
        raise PackagingError("campaign configuration: duplicate physical map IDs")
    package_paths = [item.package_path.casefold() for item in maps]
    if len(package_paths) != len(set(package_paths)):
        raise PackagingError("campaign configuration: conflicting package paths")
    bootstrap_id = campaign.get("bootstrapMapId")
    bootstrap_maps = [item.id for item in maps if item.bootstrap]
    if bootstrap_id not in map_ids or bootstrap_maps != [bootstrap_id]:
        raise PackagingError("campaign configuration: bootstrapMapId must identify the one bootstrap physical map")
    if maps[0].id != bootstrap_id:
        raise PackagingError("campaign configuration: bootstrap map must be the first chapter")
    boundary_path = _inside(project, raw.get("boundaryManifest"), "boundaryManifest")
    try:
        boundary_raw = json.loads(boundary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PackagingError(f"campaign configuration: cannot read boundary manifest: {error}") from error
    if boundary_raw.get("format") != "warcraftmap_physical_boundaries_v1" or boundary_raw.get("formatVersion") != 1:
        raise PackagingError("campaign configuration: unsupported physical boundary manifest")
    boundaries = []
    boundary_ids = set()
    occupied = set()
    map_by_id = {item.id: item for item in maps}
    single_map_compatibility = len(maps) == 2 and maps[0].bootstrap and not maps[1].bootstrap
    for index, item in enumerate(boundary_raw.get("boundaries", [])):
        label = f"boundaries[{index}]"
        boundary_id = item.get("id")
        source = item.get("sourceMapId")
        destination = item.get("destinationMapId")
        edge = item.get("sourceEdge")
        interval = item.get("sourceInterval")
        destination_region = item.get("destinationRegionId")
        transform = item.get("arrivalTransform", {})
        if not isinstance(boundary_id, str) or not STABLE_ID.fullmatch(boundary_id) or boundary_id in boundary_ids:
            raise PackagingError(f"campaign configuration: {label}.id is invalid or duplicated")
        if single_map_compatibility and (source not in map_by_id or destination not in map_by_id):
            continue
        if source not in map_by_id or destination not in map_by_id or source == bootstrap_id or destination == bootstrap_id or source == destination:
            raise PackagingError(f"campaign configuration: {label} references an invalid physical map")
        if edge not in {"north", "east", "south", "west"} or not isinstance(interval, list) or len(interval) != 2 or not all(isinstance(v, (int, float)) for v in interval) or not 0 <= interval[0] < interval[1] <= 1:
            raise PackagingError(f"campaign configuration: {label} has an invalid reachable edge interval")
        if destination_region not in map_by_id[destination].logical_region_ids:
            raise PackagingError(f"campaign configuration: {label} has an invalid destination region")
        scale, offset = transform.get("scale", 1.0), transform.get("offset", 0.0)
        reverse = transform.get("reverse", False)
        if not isinstance(scale, (int, float)) or scale <= 0 or not isinstance(offset, (int, float)) or not isinstance(reverse, bool):
            raise PackagingError(f"campaign configuration: {label} has an invalid arrival transform")
        key = (source, edge, float(interval[0]), float(interval[1]))
        if key in occupied:
            raise PackagingError(f"campaign configuration: {label} duplicates an interaction interval")
        occupied.add(key); boundary_ids.add(boundary_id)
        boundaries.append(PhysicalBoundary(boundary_id, source, destination, destination_region, edge,
            float(interval[0]), float(interval[1]), reverse, float(scale), float(offset), bool(item.get("requiresDiscovery", False))))
    if not boundaries and not single_map_compatibility:
        raise PackagingError("campaign configuration: physical boundary manifest has no boundaries")
    directed = {(item.source_map_id, item.destination_map_id) for item in boundaries}
    for source, destination in directed:
        if (destination, source) not in directed:
            raise PackagingError(f"campaign configuration: authored route {source} -> {destination} has no reverse boundary")
    reachable = {bootstrap_id}
    # Origin handoff reaches every content component via at least one configured start.
    frontier = {item.id for item in maps if not item.bootstrap and item.regional_instance_ids}
    graph_seen = {next(iter(frontier))} if frontier else set()
    while True:
        expanded = graph_seen | {b.destination_map_id for b in boundaries if b.source_map_id in graph_seen}
        if expanded == graph_seen: break
        graph_seen = expanded
    missing_routes = {item.id for item in maps if not item.bootstrap and item.regional_instance_ids} - graph_seen
    if missing_routes and not single_map_compatibility:
        raise PackagingError("campaign configuration: physical maps are disconnected from boundary travel: " + ", ".join(sorted(missing_routes)))
    if not isinstance(campaign.get("name"), str) or not campaign["name"].strip() or not isinstance(campaign.get("description"), str) or not campaign["description"].strip():
        raise PackagingError("campaign configuration: campaign name and description are required")
    return CampaignConfig(
        project, manifest_path, _inside(project, raw.get("mapBuildConfig", "package.json"), "mapBuildConfig"),
        _inside(project, raw.get("regionalAssignments"), "regionalAssignments"),
        campaign_id, file_name, str(campaign.get("name", "")), str(campaign.get("description", "")), bootstrap_id,
        _inside(project, raw.get("outputDirectory", "_build/release"), "outputDirectory") / f"{file_name}.w3n",
        tuple(maps),
        _inside(project, raw.get("audioManifest"), "audioManifest"),
        _inside(project, raw.get("audioProfiles"), "audioProfiles"),
        _inside(project, raw.get("audioValidator"), "audioValidator"), tuple(boundaries), boundary_path,
    )


def validate_campaign(config: CampaignConfig) -> dict:
    base = load_config(config.map_config_path)
    try:
        world = json.loads(base.scenario_file.read_text(encoding="utf-8"))
        presentation = json.loads(config.regional_assignments_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PackagingError(f"campaign validation stage failed: {error}") from error
    result = subprocess.run([sys.executable, str(config.audio_validator_path), "--check"], cwd=config.project, text=True, capture_output=True)
    if result.returncode:
        raise PackagingError("campaign audio validation stage failed: " + ((result.stderr or result.stdout).strip() or "validator failed"))
    try:
        world["audioManifest"] = json.loads(config.audio_manifest_path.read_text(encoding="utf-8"))
        world["audioProfiles"] = json.loads(config.audio_profiles_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PackagingError(f"campaign audio validation stage failed: {error}") from error
    regions = {item["id"] for item in world["regionalGeography"]["regions"]}
    instance_regions = presentation.get("regionalInstanceRegions", {})
    terrain_ids = {item[0] for item in base.regional_terrain}
    assigned: dict[str, str] = {}
    for physical in config.maps:
        missing = [path for path in (physical.source_map, physical.source_manifest) if not path.exists()]
        if missing:
            raise PackagingError(f"campaign inputs stage failed [{physical.id}]: missing source input {missing[0]}")
        invalid_regions = set(physical.logical_region_ids) - regions
        invalid_instances = set(physical.regional_instance_ids) - set(instance_regions)
        invalid_terrain = set(physical.terrain_ids) - terrain_ids
        if invalid_regions or invalid_instances or invalid_terrain:
            invalid = sorted(invalid_regions | invalid_instances | invalid_terrain)
            raise PackagingError(f"campaign validation stage failed [{physical.id}]: invalid region assignment(s): {', '.join(invalid)}")
        for instance_id in physical.regional_instance_ids:
            if instance_regions[instance_id] not in physical.logical_region_ids:
                raise PackagingError(f"campaign validation stage failed [{physical.id}]: {instance_id} is outside its logical region")
            if instance_id in assigned:
                raise PackagingError(f"campaign validation stage failed: regional instance {instance_id} is assigned to both {assigned[instance_id]} and {physical.id}")
            assigned[instance_id] = physical.id
    required = {item["regionalInstanceId"] for item in world.get("settlements", []) if item.get("regionalInstanceId")}
    missing = required - set(assigned)
    if missing:
        raise PackagingError("campaign validation stage failed: unassigned required content: " + ", ".join(sorted(missing)))
    treasure_path = config.project / "scenario/treasures/age-of-sail.json"
    try:
        treasure_catalog = json.loads(treasure_path.read_text(encoding="utf-8"))
        validate_treasure_catalog(treasure_catalog, {
            "regions": regions,
            "regionalInstances": set(instance_regions),
        })
        physical_by_instance = {instance: item.id for item in config.maps for instance in item.regional_instance_ids}
        configured_physical_ids = {item.id for item in config.maps}
        for candidate in treasure_catalog["candidateLocations"]:
            expected = physical_by_instance.get(candidate["regionalInstanceId"])
            # A single-map compatibility package legitimately remaps every authored
            # assignment. In the normal manifest an extant authored map must own it.
            if candidate["physicalMapId"] in configured_physical_ids and candidate["physicalMapId"] != expected:
                raise PackagingError(f"treasure candidate {candidate['id']}: physical map does not own regional instance")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise PackagingError(f"campaign treasure validation stage failed: {error}") from error
    world["treasureCatalog"] = treasure_catalog
    return world


def _localize_runtime(config: CampaignConfig, world: dict, physical: PhysicalMap, generated: Path) -> None:
    runtime_path = generated / GENERATED_DATA
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    instance_ids = set(physical.regional_instance_ids)
    settlements = [item for item in world.get("settlements", []) if item.get("regionalInstanceId") in instance_ids]
    treasure_catalog = world.get("treasureCatalog", {})
    local_candidates = [item for item in treasure_catalog.get("candidateLocations", []) if item.get("regionalInstanceId") in instance_ids]
    local_candidate_ids = {item["id"] for item in local_candidates}
    local_treasures = [item for item in treasure_catalog.get("treasures", []) if local_candidate_ids.intersection(item.get("candidateLocationIds", []))]
    province_ids = {item["provinceId"] for item in settlements}
    provinces = [item for item in world.get("provinces", []) if item["id"] in province_ids]
    polity_ids = {item.get("legalOwnerPolityId") for item in provinces} | {item.get("controllerPolityId") for item in provinces}
    polities = [item for item in world.get("polities", []) if item["id"] in polity_ids]
    map_for_instance = {instance_id: item.id for item in config.maps
                        for instance_id in item.regional_instance_ids}
    settlements_by_polity = {}
    for item in world.get("settlements", []):
        settlements_by_polity.setdefault(item.get("legalOwnerPolityId"), []).append(item)
    origins = []
    for polity in world.get("polities", []):
        owned = sorted(settlements_by_polity.get(polity["id"], []), key=lambda row: row["id"])
        capital = next((row for row in owned if row["id"] == polity.get("capitalSettlementId")), None)
        start = capital or (owned[0] if owned else None)
        if start is None or start.get("regionalInstanceId") not in map_for_instance:
            raise PackagingError(f"origin selection: polity {polity['id']} has no valid physical start")
        origins.append({"polityId": polity["id"], "name": polity["name"],
            "startingLocation": {"physicalMapId": map_for_instance[start["regionalInstanceId"]],
                "regionalInstanceId": start["regionalInstanceId"], "settlementId": start["id"]}})
    origins.sort(key=lambda row: (row["name"].casefold(), row["polityId"]))
    runtime.update({
        "physicalMap": {
            "id": physical.id, "bootstrap": physical.bootstrap, "packagePath": physical.package_path,
            "logicalRegionIds": list(physical.logical_region_ids), "regionalInstanceIds": list(physical.regional_instance_ids),
        },
        "polityDefinitions": polities,
        # Global onboarding data is intentionally not localized to the current
        # map: every active 1450 origin must remain selectable on bootstrap.
        "newCampaignOrigins": origins,
        "provinceDefinitions": provinces,
        "settlementDefinitions": settlements,
        "treasureDefinitions": local_treasures,
        "treasureCandidateLocations": local_candidates,
        "physicalBoundaries": [{
            "id": item.id, "sourceMapId": item.source_map_id,
            "destinationMapId": item.destination_map_id,
            "destinationPackagePath": next(x.package_path for x in config.maps if x.id == item.destination_map_id),
            "destinationRegionId": item.destination_region_id, "sourceEdge": item.source_edge,
            "sourceInterval": [item.interval_start, item.interval_end],
            "arrivalTransform": {"reverse": item.reverse, "scale": item.scale, "offset": item.offset},
            "requiresDiscovery": item.requires_discovery,
        } for item in config.boundaries if item.source_map_id == physical.id],
        "provinceHoldings": [item for item in world.get("territorialHoldings", []) if item.get("territory", {}).get("kind") == "province" and item["territory"]["id"] in province_ids],
        "audio": {
            "authority": "presentation_only",
            "manifest": world["audioManifest"],
            "profiles": {
                **world["audioProfiles"],
                "profiles": [row for row in world["audioProfiles"]["profiles"] if not row.get("match", {}).get("region_id") or row["match"]["region_id"] in physical.logical_region_ids],
            },
            "physicalMapId": physical.id,
        },
    })
    runtime_path.write_text(json.dumps(runtime, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    wurst_path = generated / GENERATED_WURST
    text = wurst_path.read_text(encoding="utf-8")
    origin_configuration = "public function configureGeneratedOrigins(NewCampaignOriginController controller)\n"
    for origin in origins:
        start = origin["startingLocation"]
        package_path = next(item.package_path for item in config.maps if item.id == start["physicalMapId"])
        values = [origin["polityId"], origin["name"], start["physicalMapId"], package_path,
                  start["regionalInstanceId"], start["settlementId"]]
        args = ", ".join(json.dumps(value, ensure_ascii=False) for value in values)
        origin_configuration += f"\tcontroller.add({args})\n"
    text = text.replace(
        "public function configureGeneratedOrigins(NewCampaignOriginController controller)\n\tskip\n",
        origin_configuration,
    )
    boundary_configuration = "public function configureGeneratedPhysicalBoundaries(PhysicalBoundaryRegistry registry)\n"
    package_by_id = {item.id: item.package_path for item in config.maps}
    local_boundaries = [item for item in config.boundaries if item.source_map_id == physical.id]
    for boundary in local_boundaries:
        values = [boundary.id, boundary.source_map_id, boundary.destination_map_id,
                  package_by_id[boundary.destination_map_id], boundary.destination_region_id,
                  boundary.source_edge]
        args = ", ".join(json.dumps(value) for value in values)
        boundary_configuration += (f"\tregistry.add({args}, {boundary.interval_start}, {boundary.interval_end}, "
            f"{str(boundary.reverse).lower()}, {boundary.scale}, {boundary.offset}, "
            f"{str(boundary.requires_discovery).lower()})\n")
    if not local_boundaries:
        boundary_configuration += "\tskip\n"
    text = text.replace(
        "public function configureGeneratedPhysicalBoundaries(PhysicalBoundaryRegistry registry)\n\tskip\n",
        boundary_configuration,
    )
    identity_pattern = r'public constant string PHYSICAL_MAP_ID = "[^"]*"'
    if len(re.findall(identity_pattern, text)) != 1:
        raise PackagingError(
            f"runtime localization stage failed [{physical.id}]: generated ScenarioData must declare exactly one PHYSICAL_MAP_ID"
        )
    text = re.sub(identity_pattern, f'public constant string PHYSICAL_MAP_ID = "{physical.id}"', text)
    wurst_path.write_text(text, encoding="utf-8")
    provenance_path = generated / PROVENANCE
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["physicalMap"] = physical.id
    provenance["localizationVersion"] = LOCAL_PROVENANCE_VERSION
    provenance["inputs"][str(physical.source_manifest.relative_to(config.project.parent))] = _sha(physical.source_manifest)
    provenance["inputs"][str(config.manifest_path.relative_to(config.project.parent))] = _sha(config.manifest_path)
    provenance["inputs"][str(config.boundary_manifest_path.relative_to(config.project.parent))] = _sha(config.boundary_manifest_path)
    provenance["inputs"][str(config.regional_assignments_path.relative_to(config.project.parent))] = _sha(config.regional_assignments_path)
    provenance["inputs"][str(config.audio_manifest_path.relative_to(config.project.parent))] = _sha(config.audio_manifest_path)
    provenance["inputs"][str(config.audio_profiles_path.relative_to(config.project.parent))] = _sha(config.audio_profiles_path)
    provenance["inputs"][str(config.audio_validator_path.relative_to(config.project.parent))] = _sha(config.audio_validator_path)
    provenance["inputs"]["@generator/package_wurst_campaign.py"] = _sha(Path(__file__))
    provenance["inputs"]["@generator/materialize_physical_map.py"] = _sha(Path(__file__).with_name("materialize_physical_map.py"))
    provenance["outputs"][GENERATED_DATA] = _sha(runtime_path)
    provenance["outputs"][GENERATED_WURST] = _sha(wurst_path)
    provenance_path.write_text(json.dumps(provenance, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _validate_budget(base, physical: PhysicalMap, generated: Path) -> None:
    cells = output_bytes = 0
    for terrain_id in physical.terrain_ids:
        source = dict(base.regional_terrain)[terrain_id]
        raw = json.loads(source.read_text(encoding="utf-8"))
        if raw.get("formatVersion") == 2:
            cells += sum(item["grid"][0] * item["grid"][1] for item in raw["instancePolicies"])
        else:
            cells += raw["grid"]["width"] * raw["grid"]["height"]
        output_bytes += (generated / f"terrain-{terrain_id}.json").stat().st_size
    if cells > physical.maximum_cells or output_bytes > physical.maximum_output_bytes:
        raise PackagingError(
            f"terrain budget stage failed [{physical.id}]: cells {cells}/{physical.maximum_cells}, "
            f"generated bytes {output_bytes}/{physical.maximum_output_bytes}"
        )


def _write_campaign(output: Path, config: CampaignConfig, built: list[tuple[PhysicalMap, Path]]) -> None:
    manifest = {
        "format": CAMPAIGN_ARCHIVE_FORMAT, "formatVersion": 1, "campaignId": config.campaign_id,
        "name": config.name, "bootstrapMapId": config.bootstrap_map_id,
        "maps": [{"id": item.id, "packagePath": item.package_path, "sha256": _sha(archive), "bootstrap": item.bootstrap} for item, archive in built],
    }
    # Regional maps remain campaign members so SetNextLevel can reach them, but
    # only the bootstrap is player-selectable. This prevents bypassing origin
    # selection from the Custom Campaign chapter list.
    maps = [(item.chapter_title, item.package_path) for item, _ in built]
    chapters = [(item.chapter_title, item.package_path) for item, _ in built if item.bootstrap]
    files = {
        "war3campaign.w3f": campaign_metadata(config.name, config.description, maps, chapters),
        "campaign-manifest.json": (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode(),
        "(listfile)": ("\r\n".join(["war3campaign.w3f", "campaign-manifest.json", *(x.package_path for x, _ in built)]) + "\r\n").encode(),
    }
    files.update((item.package_path, archive.read_bytes()) for item, archive in built)
    write_mpq(output, files)


def inspect_campaign(config: CampaignConfig, archive: Path) -> None:
    try:
        reader = MpqReader(archive)
        metadata = parse_campaign_metadata(reader.read("war3campaign.w3f"))
        manifest = json.loads(reader.read("campaign-manifest.json"))
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as error:
        raise PackagingError(f"campaign inspection stage failed: invalid Warcraft MPQ campaign: {error}") from error
    expected_chapters = [(item.chapter_title, item.package_path) for item in config.maps]
    if not config.name or not config.description or metadata["name"] != config.name or metadata["description"] != config.description:
        raise PackagingError("campaign inspection stage failed: campaign title or description is absent or malformed")
    expected_order = [("", path) for _, path in expected_chapters]
    expected_buttons = [(1, item.chapter_title, item.chapter_title, item.package_path) for item in config.maps if item.bootstrap]
    if metadata["version"] != 3 or metadata["flags"] != 2 or metadata["backgroundVersion"] != 0 or metadata["maps"] != expected_order or metadata["buttons"] != expected_buttons:
        raise PackagingError("campaign inspection stage failed: chapter metadata or ordering is invalid")
    if not expected_chapters or expected_chapters[0][1] != next(x.package_path for x in config.maps if x.id == config.bootstrap_map_id):
        raise PackagingError("campaign inspection stage failed: first chapter is not the bootstrap map")
    if manifest.get("format") != CAMPAIGN_ARCHIVE_FORMAT or manifest.get("bootstrapMapId") != config.bootstrap_map_id:
        raise PackagingError("campaign inspection stage failed: campaign metadata is invalid")
    if {item["id"] for item in manifest.get("maps", [])} != {item.id for item in config.maps}:
        raise PackagingError("campaign inspection stage failed: physical map IDs are incomplete")
    for item in manifest["maps"]:
        try:
            payload = reader.read(item["packagePath"])
        except KeyError as error:
            raise PackagingError(f"campaign inspection stage failed [{item['id']}]: chapter points to missing map") from error
        if _sha_bytes(payload) != item["sha256"]:
            raise PackagingError(f"campaign inspection stage failed [{item['id']}]: packaged map checksum differs")


def _inspect_audio_runtime(physical: PhysicalMap, generated: Path) -> None:
    """Inspect staged data before Grill converts the map folder to MPQ."""
    try:
        runtime = json.loads((generated / GENERATED_DATA).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PackagingError(f"campaign inspection stage failed [{physical.id}]: invalid runtime playback data: {error}") from error
    audio = runtime.get("audio", {})
    if audio.get("authority") != "presentation_only" or audio.get("physicalMapId") != physical.id:
        raise PackagingError(f"campaign inspection stage failed [{physical.id}]: invalid audio playback data")
    if audio.get("manifest", {}).get("format") != "warcraftmap_audio_manifest_v1" or not audio.get("profiles", {}).get("profiles"):
        raise PackagingError(f"campaign inspection stage failed [{physical.id}]: missing audio manifest or profiles")


def _inspect_physical_map(physical: PhysicalMap, archive: Path) -> None:
    """Parse the built W3X and prove binaries match its localized manifest."""
    reader = None
    zipped = None
    try:
        if zipfile.is_zipfile(archive):
            zipped = zipfile.ZipFile(archive)
            read = zipped.read
        else:
            reader = MpqReader(archive)
            read = reader.read
        w3e, wpm, units = read("war3map.w3e"), read("war3map.wpm"), read("war3mapUnits.doo")
        runtime = json.loads(read(f"runtime/{GENERATED_DATA}"))
        if physical.bootstrap:
            return
        manifest = json.loads(read("runtime/physical-map.json"))
        offset = 13
        ground = struct.unpack_from("<I", w3e, offset)[0]; offset += 4 + ground * 4
        cliffs = struct.unpack_from("<I", w3e, offset)[0]; offset += 4 + cliffs * 4
        terrain_width, terrain_height = struct.unpack_from("<II", w3e, offset)
        width, height = terrain_width - 1, terrain_height - 1
        path_width, path_height = struct.unpack_from("<II", wpm, 8)
        object_count = struct.unpack_from("<I", units, 12)[0]
        expected_settlements = {x["id"] for x in runtime.get("settlementDefinitions", [])}
        represented = {x["id"] for x in manifest.get("objects", {}).get("settlements", [])}
        if w3e[:4] != b"W3E!" or len(w3e) != offset + 16 + terrain_width * terrain_height * 7:
            raise ValueError("malformed materialized terrain")
        if wpm[:4] != b"MP3W" or (path_width, path_height) != (width * 4, height * 4) or len(wpm) != 16 + path_width * path_height:
            raise ValueError("materialized pathing does not match terrain")
        if manifest.get("physicalMapId") != physical.id or manifest.get("terrain", {}).get("width") != width or manifest.get("terrain", {}).get("height") != height:
            raise ValueError("physical manifest does not match terrain")
        expected_objects = len(represented) + manifest.get("objects", {}).get("worldMarkerCount", 0) + 1
        if expected_settlements != represented or object_count != expected_objects or manifest["objects"].get("spawnCount") != 1:
            raise ValueError("settlement/port/spawn objects do not match localized runtime")
        if width * height > 256 * 256 or object_count > 8192:
            raise ValueError("Warcraft physical-map budget exceeded")
    except (KeyError, OSError, ValueError, json.JSONDecodeError, struct.error) as error:
        raise PackagingError(f"campaign inspection stage failed [{physical.id}]: {error}") from error
    finally:
        if zipped is not None:
            zipped.close()


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def clean(config: CampaignConfig) -> None:
    root = config.project / "_build"
    if root.exists():
        shutil.rmtree(root)


def build_campaign(manifest_path: Path, grill: str | None = None, clean_first: bool = True) -> Path:
    config = load_campaign_config(manifest_path)
    base = load_config(config.map_config_path)
    executable = validate_inputs(base, grill)
    if clean_first:
        clean(config)
    validate_scenario(base)
    world = validate_campaign(config)
    built = []
    for physical in config.maps:
        # A physical-map entry owns its source folder and source manifest.  The
        # scenario-wide build configuration supplies the reusable Wurst and
        # generation settings, but must not silently force every entry to use
        # the bootstrap map's source inputs.
        map_config = replace(base, source_map=physical.source_map, manifest=physical.source_manifest)
        validate_inputs(map_config, executable)
        map_root = config.project / "_build/maps" / physical.id
        generated = map_root / "generated"
        generate(map_config, generated)
        _localize_runtime(config, world, physical, generated)
        _inspect_audio_runtime(physical, generated)
        verify_generated(map_config, generated)
        _validate_budget(map_config, physical, generated)
        compile_root = _assemble(map_config, map_root, generated, physical.terrain_ids)
        runtime = json.loads((generated / GENERATED_DATA).read_text(encoding="utf-8"))
        try:
            materialize(config.project, compile_root / "map" / map_config.source_map.name,
                        generated, physical, runtime)
        except (OSError, KeyError, ValueError, MaterializationError) as error:
            raise PackagingError(f"physical map materialization stage failed [{physical.id}]: {error}") from error
        _run(f"Wurst dependency installation [{physical.id}]", [executable, "install"], compile_root)
        _run(f"Wurst compilation [{physical.id}]", [executable, "typecheck"], compile_root)
        _run(f"map assembly [{physical.id}]", [executable, "build", str(Path("map") / map_config.source_map.name)], compile_root)
        archive = _find_archive(compile_root / "_build")
        _inspect(map_config, archive, compile_root, physical.terrain_ids)
        _inspect_physical_map(physical, archive)
        destination = map_root / f"{physical.id}.w3x"
        shutil.copyfile(archive, destination)
        built.append((physical, destination))
    _write_campaign(config.output, config, built)
    inspect_campaign(config, config.output)
    print(f"campaign archive: {config.output}")
    return config.output


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) not in (1, 2) or (len(argv) == 2 and argv[0] != "clean"):
        print("usage: package_wurst_campaign.py [clean] MANIFEST", file=sys.stderr)
        return 2
    try:
        config = load_campaign_config(Path(argv[-1]))
        clean(config) if len(argv) == 2 else build_campaign(Path(argv[-1]))
    except (PackagingError, OSError, KeyError) as error:
        print(f"campaign packaging failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

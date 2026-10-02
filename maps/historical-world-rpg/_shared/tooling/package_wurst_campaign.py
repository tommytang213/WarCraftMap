#!/usr/bin/env python3
"""Deterministic multi-map Warcraft III campaign build orchestration."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from treasures import validate_catalog as validate_treasure_catalog  # noqa: E402

STABLE_ID = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
CAMPAIGN_FORMAT = "warcraftmap_physical_maps_v1"
CAMPAIGN_ARCHIVE_FORMAT = "warcraftmap_campaign_v1"
LOCAL_PROVENANCE_VERSION = 1


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
        _inside(project, raw.get("audioValidator"), "audioValidator"),
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
    runtime.update({
        "physicalMap": {
            "id": physical.id, "bootstrap": physical.bootstrap, "packagePath": physical.package_path,
            "logicalRegionIds": list(physical.logical_region_ids), "regionalInstanceIds": list(physical.regional_instance_ids),
        },
        "polityDefinitions": polities,
        "provinceDefinitions": provinces,
        "settlementDefinitions": settlements,
        "treasureDefinitions": local_treasures,
        "treasureCandidateLocations": local_candidates,
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
    encoded = json.dumps(runtime, ensure_ascii=False, sort_keys=True, separators=(",", ":")).replace("\\", "\\\\").replace('"', '\\"')
    text = re.sub(r'public constant string SCENARIO_RUNTIME_JSON = ".*"', f'public constant string SCENARIO_RUNTIME_JSON = "{encoded}"', text)
    text += f'\npublic constant string PHYSICAL_MAP_ID = "{physical.id}"\n'
    wurst_path.write_text(text, encoding="utf-8")
    provenance_path = generated / PROVENANCE
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["physicalMap"] = physical.id
    provenance["localizationVersion"] = LOCAL_PROVENANCE_VERSION
    provenance["inputs"][str(physical.source_manifest.relative_to(config.project.parent))] = _sha(physical.source_manifest)
    provenance["inputs"][str(config.manifest_path.relative_to(config.project.parent))] = _sha(config.manifest_path)
    provenance["inputs"][str(config.regional_assignments_path.relative_to(config.project.parent))] = _sha(config.regional_assignments_path)
    provenance["inputs"][str(config.audio_manifest_path.relative_to(config.project.parent))] = _sha(config.audio_manifest_path)
    provenance["inputs"][str(config.audio_profiles_path.relative_to(config.project.parent))] = _sha(config.audio_profiles_path)
    provenance["inputs"][str(config.audio_validator_path.relative_to(config.project.parent))] = _sha(config.audio_validator_path)
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
    # The configured order is the authored chapter order.  In particular the
    # bootstrap is first, rather than relying on an archive member sort order.
    chapters = [(item.chapter_title, item.package_path) for item, _ in built]
    files = {
        "war3campaign.w3f": campaign_metadata(config.name, config.description, chapters),
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
    if metadata["version"] != 1 or metadata["maps"] != expected_chapters or [(x[1], x[2]) for x in metadata["buttons"]] != expected_chapters:
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
        _run(f"Wurst dependency installation [{physical.id}]", [executable, "install"], compile_root)
        _run(f"Wurst compilation [{physical.id}]", [executable, "typecheck"], compile_root)
        _run(f"map assembly [{physical.id}]", [executable, "build", str(Path("map") / map_config.source_map.name)], compile_root)
        archive = _find_archive(compile_root / "_build")
        _inspect(map_config, archive, compile_root, physical.terrain_ids)
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

"""Generate setting identity and map/region lookup for the shared runtime."""
import json
import re
from scenario_inputs import configuration


def write_settings(project, destination):
    config = configuration(project)
    release = config["release"]
    cache = release.get("cacheFile", "Campaign.w3v")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.w3v", cache):
        raise ValueError("configuration: invalid campaign cache filename")
    world = json.loads((project / config["scenario"]["data"]).read_text())
    regions = [row["id"] for row in world["regionalGeography"]["regions"]]
    known = config["scenario"].get("initiallyKnownRegionIds", [])
    if set(known) - set(regions):
        raise ValueError("configuration: unknown initially known region")
    manifest = project / "physical-maps.json"
    physical_maps = json.loads(manifest.read_text()) if manifest.is_file() else None
    selector = physical_maps["campaign"]["bootstrapMapId"] if physical_maps else ""
    lines = ["package ScenarioSettings", "",
             "public constant string CAMPAIGN_CACHE_FILE = " + json.dumps(cache),
             "public constant string SCENARIO_CAMPAIGN_ID = " + json.dumps(physical_maps["campaign"]["id"] if physical_maps else cache),
             "public constant string SCENARIO_BOOTSTRAP_MAP_ID = " + json.dumps(selector),
             "public constant string SCENARIO_BOOTSTRAP_MESSAGE = " + json.dumps(release["bootstrapMarkers"][0]),
             "", "public function scenarioRegionCount() returns int", f"\treturn {len(regions)}",
             "", "public function scenarioRegionId(int index) returns string"]
    for i, region in enumerate(regions):
        lines += [f"\tif index == {i}", "\t\treturn " + json.dumps(region)]
    lines += ['\treturn ""', "", "public function scenarioRegionInitiallyKnown(string id) returns boolean"]
    for region in known:
        lines += ["\tif id == " + json.dumps(region), "\t\treturn true"]
    lines += ["\treturn false", "", "public function scenarioLogicalRegion(string mapId) returns string"]
    if physical_maps:
        for physical in physical_maps["physicalMaps"]:
            logical = physical["assignments"]["logicalRegionIds"]
            if logical:
                lines += ["\tif mapId == " + json.dumps(physical["id"]), "\t\treturn " + json.dumps(logical[0])]
    lines += ['\treturn ""', ""]
    # Stable military locations use logical regions, physical chapters or legacy
    # regional instances. Resolve all three through authored assignments, never
    # ID prefixes or a fallback region that could authorize unrelated holdings.
    lines += ["public function scenarioAuthorityRegion(string locationId) returns string"]
    authority_regions = {region: region for region in regions}
    if physical_maps:
        for physical in physical_maps["physicalMaps"]:
            logical = physical["assignments"]["logicalRegionIds"]
            if len(logical) == 1:
                for location in [physical["id"], *physical["assignments"]["regionalInstanceIds"]]:
                    if location in authority_regions and authority_regions[location] != logical[0]:
                        raise ValueError("configuration: ambiguous authority region " + location)
                    authority_regions[location] = logical[0]
    for location, region in sorted(authority_regions.items()):
        lines += ["\tif locationId == " + json.dumps(location), "\t\treturn " + json.dumps(region)]
    lines += ['\treturn ""', ""]
    # Recovery can target any packaged regional map, including maps without an
    # origin or a boundary adjacent to the currently loaded map. Never use a
    # path supplied by a saved document as loader input.
    lines += ["public function scenarioPhysicalMapPath(string mapId) returns string"]
    if physical_maps:
        for physical in physical_maps["physicalMaps"]:
            if physical["assignments"]["logicalRegionIds"] and not physical.get("bootstrap", False):
                lines += ["\tif mapId == " + json.dumps(physical["id"]),
                          "\t\treturn " + json.dumps(physical["packagePath"])]
    lines += ['\treturn ""', ""]
    (destination / "ScenarioSettings.wurst").write_text("\n".join(lines))

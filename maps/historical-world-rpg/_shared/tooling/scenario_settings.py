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
    (destination / "ScenarioSettings.wurst").write_text("\n".join(lines))

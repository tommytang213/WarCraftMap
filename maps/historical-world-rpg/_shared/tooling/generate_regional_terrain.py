#!/usr/bin/env python3
"""Deterministically rasterize scenario-owned regional geography into build inputs."""
from __future__ import annotations

import argparse
import json
import math
import time
from collections import deque
from pathlib import Path


class TerrainGenerationError(ValueError):
    pass


SURFACES = {"void": 0, "land": 1, "navigable_sea": 2, "decorative_water": 3}
MOVEMENT_CLASSES = {"land", "naval", "amphibious", "flying"}


def _point_in_polygon(x: float, y: float, polygon: list[list[float]]) -> bool:
    inside = False
    previous = polygon[-1]
    for current in polygon:
        x1, y1 = previous
        x2, y2 = current
        if (y1 > y) != (y2 > y):
            crossing = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < crossing:
                inside = not inside
        previous = current
    return inside


def _index(records: object, label: str) -> dict[str, dict]:
    if not isinstance(records, list):
        raise TerrainGenerationError(f"{label} must be an array")
    result = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            raise TerrainGenerationError(f"{label} entries require stable ids")
        if record["id"] in result:
            raise TerrainGenerationError(f"{label} contains duplicate id {record['id']!r}")
        result[record["id"]] = record
    return result


def _cell(source: dict, point: list[float]) -> tuple[int, int]:
    minimum_x, minimum_y, maximum_x, maximum_y = source["coordinateSystem"]["bounds"]
    grid = source["grid"]
    x = round((point[0] - minimum_x) * (grid["width"] - 1) / (maximum_x - minimum_x))
    y = round((point[1] - minimum_y) * (grid["height"] - 1) / (maximum_y - minimum_y))
    return x, y


def _runs(values: list[int]) -> list[list[int]]:
    result = []
    for value in values:
        if result and result[-1][0] == value:
            result[-1][1] += 1
        else:
            result.append([value, 1])
    return result


def _reachable(graph: dict[str, set[str]], start: str) -> set[str]:
    found, pending = set(), deque([start])
    while pending:
        current = pending.popleft()
        if current in found:
            continue
        found.add(current)
        pending.extend(sorted(graph[current] - found))
    return found


def _validate(source: dict, regional_geography: dict | None) -> tuple[dict, dict, dict]:
    if source.get("formatVersion") != 1:
        raise TerrainGenerationError("formatVersion must be 1")
    if source.get("coordinateSystem", {}).get("northUp") is not True:
        raise TerrainGenerationError("coordinate system must be north-up")
    bounds = source.get("coordinateSystem", {}).get("bounds")
    if not isinstance(bounds, list) or len(bounds) != 4 or bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
        raise TerrainGenerationError("coordinateSystem.bounds is invalid")
    grid = source.get("grid", {})
    if not all(isinstance(grid.get(key), int) and grid[key] > 1 for key in ("width", "height", "cellSizeWarcraft")):
        raise TerrainGenerationError("grid dimensions and cell size must be positive integers")
    surfaces = _index(source.get("surfaces"), "surfaces")
    waters = _index(source.get("waterBodies"), "waterBodies")
    features = _index(source.get("linearFeatures"), "linearFeatures")
    zones = _index(source.get("navigationZones"), "navigationZones")
    chokepoints = _index(source.get("chokepoints"), "chokepoints")
    if not surfaces or not waters or not zones:
        raise TerrainGenerationError("land surfaces, water bodies, and navigation zones are required")
    for item in (*surfaces.values(), *waters.values()):
        if item.get("kind") not in set(SURFACES) - {"void"}:
            raise TerrainGenerationError(f"{item['id']}: unsupported surface kind")
        polygon = item.get("polygon")
        if not isinstance(polygon, list) or len(polygon) < 3:
            raise TerrainGenerationError(f"{item['id']}: polygon requires at least three points")
    for zone in zones.values():
        if zone.get("surface") not in SURFACES:
            raise TerrainGenerationError(f"zone {zone['id']}: invalid surface")
        classes = zone.get("movementClasses")
        if not isinstance(classes, list) or not classes or not set(classes) <= MOVEMENT_CLASSES:
            raise TerrainGenerationError(f"zone {zone['id']}: invalid movement classes")
    connections = source.get("connections")
    if not isinstance(connections, list):
        raise TerrainGenerationError("connections must be an array")
    for connection in connections:
        if connection.get("from") not in zones or connection.get("to") not in zones:
            raise TerrainGenerationError("navigation connection references a missing zone")
        classes = set(connection.get("movementClasses", []))
        if not classes or not classes <= set(zones[connection["from"]]["movementClasses"]) & set(zones[connection["to"]]["movementClasses"]):
            raise TerrainGenerationError("navigation connection has incompatible movement classes")
        if connection.get("via") is not None and connection["via"] not in chokepoints:
            raise TerrainGenerationError("navigation connection references a missing chokepoint")
    for chokepoint in chokepoints.values():
        connected = chokepoint.get("connects")
        if not isinstance(connected, list) or len(connected) != 2 or any(item not in waters for item in connected):
            raise TerrainGenerationError(f"chokepoint {chokepoint['id']}: connects must reference two water bodies")
    for crossing in source.get("crossings", []):
        if crossing.get("featureId") not in features:
            raise TerrainGenerationError(f"crossing {crossing.get('id', '<missing>')}: feature is missing")
    anchors = _index(source.get("transitionAnchors"), "transitionAnchors")
    for anchor in anchors.values():
        zone = zones.get(anchor.get("zoneId"))
        if zone is None:
            raise TerrainGenerationError(f"anchor {anchor['id']}: zone is missing")
        if not set(anchor.get("movementClasses", [])) <= set(zone["movementClasses"]):
            raise TerrainGenerationError(f"anchor {anchor['id']}: zone movement classes are incompatible")
        x, y = anchor.get("at", [None, None])
        if not all(isinstance(value, (int, float)) for value in (x, y)) or not (bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]):
            raise TerrainGenerationError(f"anchor {anchor['id']}: position is outside coordinate bounds")
    if regional_geography is not None:
        runtime = {item["id"]: item for item in regional_geography.get("anchors", []) if item.get("regionId") == source["regionId"]}
        for anchor in anchors.values():
            runtime_id = anchor.get("runtimeAnchorId", anchor["id"])
            target = runtime.get(runtime_id)
            if target is None:
                raise TerrainGenerationError(f"anchor {anchor['id']}: runtime anchor {runtime_id!r} is missing")
            if not set(anchor["movementClasses"]) <= set(target["movementClasses"]):
                raise TerrainGenerationError(f"anchor {anchor['id']}: runtime movement classes are incompatible")
            if anchor.get("runtimeAnchorId") is None and anchor["at"] != [target["position"]["x"], target["position"]["y"]]:
                raise TerrainGenerationError(f"anchor {anchor['id']}: runtime position does not align")
    return zones, chokepoints, features


def generate(source: dict, regional_geography: dict | None = None) -> dict:
    started = time.perf_counter()
    zones, chokepoints, features = _validate(source, regional_geography)
    width, height = source["grid"]["width"], source["grid"]["height"]
    minimum_x, minimum_y, maximum_x, maximum_y = source["coordinateSystem"]["bounds"]
    cells = []
    for y in range(height):
        py = minimum_y + (y + 0.5) * (maximum_y - minimum_y) / height
        for x in range(width):
            px = minimum_x + (x + 0.5) * (maximum_x - minimum_x) / width
            surface = "void"
            if any(_point_in_polygon(px, py, item["polygon"]) for item in source["waterBodies"] if item["kind"] == "navigable_sea"):
                surface = "navigable_sea"
            if any(_point_in_polygon(px, py, item["polygon"]) for item in source["surfaces"] if item["kind"] == "land"):
                surface = "land"
            if any(_point_in_polygon(px, py, item["polygon"]) for item in source["waterBodies"] if item["kind"] == "navigable_sea" and item.get("overlaysLand") is True):
                surface = "navigable_sea"
            if any(_point_in_polygon(px, py, item["polygon"]) for item in source["waterBodies"] if item["kind"] == "decorative_water"):
                surface = "decorative_water"
            cells.append(SURFACES[surface])

    # Declared chokepoints are explicit playability distortions and therefore win
    # over generalized coast polygons.
    for chokepoint in chokepoints.values():
        cx, cy = _cell(source, chokepoint["at"])
        radius = max(1, math.ceil(chokepoint["minimumWidthCells"] / 2))
        for y in range(max(0, cy - radius), min(height, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(width, cx + radius + 1)):
                cells[y * width + x] = SURFACES["navigable_sea"]

    graphs = {movement: {zone: set() for zone in zones if movement in zones[zone]["movementClasses"]} for movement in sorted(MOVEMENT_CLASSES)}
    for connection in source["connections"]:
        for movement in connection["movementClasses"]:
            graphs[movement][connection["from"]].add(connection["to"])
            graphs[movement][connection["to"]].add(connection["from"])
    connectivity = {}
    for movement, graph in graphs.items():
        connectivity[movement] = {zone: sorted(_reachable(graph, zone)) for zone in sorted(graph)}

    encoded = _runs(cells)
    counts = {name: cells.count(value) for name, value in SURFACES.items()}
    output = {
        "formatVersion": 1,
        "regionId": source["regionId"],
        "coordinateSystem": source["coordinateSystem"],
        "grid": source["grid"],
        "surfaceEncoding": {"legend": SURFACES, "order": "southwest-row-major", "runs": encoded},
        "surfaceCounts": counts,
        "features": {"linear": list(features.values()), "chokepoints": list(chokepoints.values()), "crossings": source.get("crossings", [])},
        "navigation": {"zones": list(zones.values()), "connections": source["connections"], "connectivity": connectivity},
        "transitionAnchors": source["transitionAnchors"],
        "landmarks": source.get("landmarks", []),
        "declaredDistortions": source["provenance"]["declaredDistortions"],
        "statistics": {"cellCount": len(cells), "encodedRuns": len(encoded), "featureCount": len(source["surfaces"]) + len(source["waterBodies"]) + len(features) + len(chokepoints)},
    }
    budgets = source["budgets"]
    elapsed_ms = (time.perf_counter() - started) * 1000
    checks = {
        "cellCount": (output["statistics"]["cellCount"], budgets["maximumCells"]),
        "encodedRuns": (len(encoded), budgets["maximumEncodedRuns"]),
        "featureCount": (output["statistics"]["featureCount"], budgets["maximumFeatures"]),
    }
    for label, (actual, maximum) in checks.items():
        if actual > maximum:
            raise TerrainGenerationError(f"budget exceeded: {label} {actual} > {maximum}")
    if elapsed_ms > budgets["maximumGenerationMilliseconds"]:
        raise TerrainGenerationError(f"budget exceeded: generation time {elapsed_ms:.1f}ms > {budgets['maximumGenerationMilliseconds']}ms")
    serialized = canonical_bytes(output)
    if len(serialized) > budgets["maximumOutputBytes"]:
        raise TerrainGenerationError(f"budget exceeded: output size {len(serialized)} > {budgets['maximumOutputBytes']}")
    output["statistics"]["outputBytes"] = len(serialized)
    return output


def canonical_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--world", type=Path)
    args = parser.parse_args(argv)
    try:
        source = json.loads(args.source.read_text(encoding="utf-8"))
        world = json.loads(args.world.read_text(encoding="utf-8"))["regionalGeography"] if args.world else None
        result = generate(source, world)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_bytes(result))
    except (OSError, json.JSONDecodeError, KeyError, TerrainGenerationError) as error:
        print(f"terrain generation failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

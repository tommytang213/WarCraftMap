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


def _generate_instance_collection(source: dict, regional_geography: dict | None, authority: dict | None) -> dict:
    """Generate map-scoped rasters from an authoritative multi-instance geography.

    The format deliberately keeps the geography in the scenario authority file;
    this configuration only declares raster/pathing policy and budgets.
    """
    if authority is None or authority.get("graphRegionId") != source.get("regionId"):
        raise TerrainGenerationError("multi-instance terrain requires its matching geography authority")
    policies = _index(source.get("instancePolicies"), "instancePolicies")
    instances = _index(authority.get("instances"), "geography instances")
    if set(policies) != set(instances):
        raise TerrainGenerationError("instancePolicies must cover every authoritative geography instance")
    topology = authority.get("navigationTopology", {})
    nodes = _index(topology.get("nodes"), "navigation nodes")
    links = _index(topology.get("links"), "navigation links")
    graphs = {kind: {node: set() for node in nodes} for kind in sorted(MOVEMENT_CLASSES)}
    for link in links.values():
        for kind in link.get("movementClasses", []):
            if kind not in MOVEMENT_CLASSES:
                raise TerrainGenerationError(f"navigation link {link['id']}: invalid movement class")
            graphs[kind][link["from"]].add(link["to"]); graphs[kind][link["to"]].add(link["from"])
    forbidden = {node for node, value in nodes.items() if value.get("class") in {"decorative_water", "impassable_barrier"}}
    if any(graphs[kind][node] for kind in graphs for node in forbidden):
        raise TerrainGenerationError("navigation cannot route through decorative water or impassable barriers")
    results, total_cells, total_bytes = [], 0, 0
    anchors_by_id = _index(authority.get("boundaryAnchors"), "boundaryAnchors")
    for anchor in anchors_by_id.values():
        if anchor.get("pairId"):
            pair = anchors_by_id.get(anchor["pairId"])
            if pair is None or pair.get("pairId") != anchor["id"] or pair.get("source") != anchor.get("source"):
                raise TerrainGenerationError(f"boundary anchor {anchor['id']}: seam correspondence is invalid")
    runtime_anchors = {a["id"]: a for a in (regional_geography or {}).get("anchors", [])}
    for anchor in anchors_by_id.values():
        if anchor.get("globalAnchorId"):
            target = runtime_anchors.get(anchor["globalAnchorId"])
            if target is None or target.get("regionId") != source["regionId"]:
                raise TerrainGenerationError(f"boundary anchor {anchor['id']}: global entry anchor is missing")
    for instance_id in sorted(instances):
        instance, policy = instances[instance_id], policies[instance_id]
        bounds = instance["localBounds"]; width, height = policy["grid"]
        if not all(isinstance(v, int) and v > 1 for v in (width, height)):
            raise TerrainGenerationError(f"{instance_id}: grid must contain positive integer dimensions")
        cells = [SURFACES["navigable_sea"]] * (width * height)
        def paint_polygon(polygon, value):
            for y in range(height):
                py = bounds["minY"] + (y + .5) * (bounds["maxY"] - bounds["minY"]) / height
                for x in range(width):
                    px = bounds["minX"] + (x + .5) * (bounds["maxX"] - bounds["minX"]) / width
                    if _point_in_polygon(px, py, polygon): cells[y * width + x] = value
        for polygon in policy.get("landMasks", []): paint_polygon(polygon, SURFACES["land"])
        feature_output = []
        origin, scale, offset = instance["transform"]["sourceOrigin"], instance["transform"]["scale"], instance["transform"]["offset"]
        for feature in instance["features"]:
            transformed = [[round((p[0]-origin[0])*scale[0]+offset[0], 2), round((p[1]-origin[1])*scale[1]+offset[1], 2)] for p in feature["points"]]
            feature_output.append({**feature, "points": transformed})
            if feature["kind"] == "island" and len(transformed) >= 3: paint_polygon(transformed, SURFACES["land"])
        # Isolated/decorative water is never made navigable by a generalized
        # island polygon; it has final precedence in the surface raster.
        for polygon in policy.get("decorativeWaterMasks", []): paint_polygon(polygon, SURFACES["decorative_water"])
        encoded = _runs(cells)
        item = {"id": instance_id, "name": instance["name"], "bounds": bounds,
                "grid": {"width": width, "height": height, "cellSizeWarcraft": source["cellSizeWarcraft"]},
                "surfaceEncoding": {"legend": SURFACES, "order": "southwest-row-major", "runs": encoded},
                "surfaceCounts": {name: cells.count(value) for name, value in SURFACES.items()},
                "features": feature_output,
                "navigationNodeIds": sorted(n for n, value in nodes.items() if value["instanceId"] == instance_id),
                "boundaryAnchors": sorted((a for a in authority["boundaryAnchors"] if a["instanceId"] == instance_id), key=lambda a:a["id"]),
                "statistics": {"cellCount": len(cells), "encodedRuns": len(encoded), "featureCount": len(feature_output)}}
        encoded_bytes = len(canonical_bytes(item)); budget = policy["budget"]
        checks = (("cells", len(cells), budget["maximumCells"]), ("runs", len(encoded), budget["maximumEncodedRuns"]),
                  ("features", len(feature_output), budget["maximumFeatures"]), ("output bytes", encoded_bytes, budget["maximumOutputBytes"]))
        for label, actual, maximum in checks:
            if actual > maximum: raise TerrainGenerationError(f"{instance_id}: {label} budget exceeded: {actual} > {maximum}")
        item["statistics"]["outputBytes"] = encoded_bytes; total_cells += len(cells); total_bytes += encoded_bytes; results.append(item)
    anchors = sorted(authority["boundaryAnchors"], key=lambda a:a["id"])
    return {"formatVersion": 2, "regionId": source["regionId"], "authorityId": authority["id"],
            "declaredDistortions": source["declaredDistortions"], "instances": results,
            "navigation": {"nodes": list(nodes.values()), "links": list(links.values()),
                "connectivity": {kind: {node: sorted(_reachable(graph, node)) for node in sorted(graph)} for kind, graph in graphs.items()}},
            "transitionAnchors": anchors,
            "statistics": {"instanceCount": len(results), "cellCount": total_cells, "instanceOutputBytes": total_bytes}}


def generate(source: dict, regional_geography: dict | None = None, authority: dict | None = None) -> dict:
    started = time.perf_counter()
    if source.get("formatVersion") == 2:
        result = _generate_instance_collection(source, regional_geography, authority)
        maximum = source["budgets"]["maximumGenerationMilliseconds"]
        elapsed = (time.perf_counter() - started) * 1000
        if elapsed > maximum: raise TerrainGenerationError(f"budget exceeded: generation time {elapsed:.1f}ms > {maximum}ms")
        if len(canonical_bytes(result)) > source["budgets"]["maximumOutputBytes"]:
            raise TerrainGenerationError("budget exceeded: aggregate output size")
        return result
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

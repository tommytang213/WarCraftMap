#!/usr/bin/env python3
"""Validate and deterministically derive Africa spatial reference inputs."""
from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("regional_geography", Path(__file__).with_name("europe_geography.py"))
_core = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_core)
GeographyError = _core.GeographyError
transform_point = _core.transform_point
generate = _core.generate
MOVEMENT_CLASSES = {"land", "naval", "amphibious", "flying"}

def validate(source, world):
    instances, anchors = _core.validate(source, world)
    features = {feature["id"]: feature for instance in source["instances"] for feature in instance["features"]}
    for instance in source["instances"]:
        classes = set(instance.get("movementClasses", []))
        if not classes or not classes <= MOVEMENT_CLASSES:
            raise GeographyError(f"instance {instance['id']}: invalid movement classes")
        density = instance.get("density", {})
        if density.get("profile") not in {"sparse", "balanced", "dense"}:
            raise GeographyError(f"instance {instance['id']}: invalid density profile")
        for key in ("maxLandmarksPer100Cells", "maxTraversalNodesPer100Cells"):
            value = density.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= 10:
                raise GeographyError(f"instance {instance['id']}: invalid density bound {key}")
    for anchor_id, anchor in anchors.items():
        classes = anchor.get("movementClasses")
        if not isinstance(classes, list) or not classes or len(classes) != len(set(classes)) or not set(classes) <= MOVEMENT_CLASSES:
            raise GeographyError(f"anchor {anchor_id}: invalid movement classes")
        global_id = anchor.get("globalAnchorId")
        if global_id:
            global_anchor = next(item for item in world["regionalGeography"]["anchors"] if item["id"] == global_id)
            if not set(classes) <= set(global_anchor["movementClasses"]):
                raise GeographyError(f"anchor {anchor_id}: movement classes exceed global anchor {global_id}")
    occupied = set(instances) | set(anchors) | set(features) | {item["id"] for item in source["distortions"]}
    corridor_ids = set()
    for corridor in source.get("corridors", []):
        corridor_id = corridor.get("id")
        if not isinstance(corridor_id, str) or not _core.ID_RE.fullmatch(corridor_id) or corridor_id in occupied | corridor_ids:
            raise GeographyError(f"corridors: invalid or duplicate stable ID {corridor_id!r}")
        corridor_ids.add(corridor_id)
        if corridor.get("fromAnchorId") not in anchors or corridor.get("toAnchorId") not in anchors:
            raise GeographyError(f"corridor {corridor_id}: missing anchor reference")
        classes = set(corridor.get("movementClasses", []))
        if not classes or not classes <= MOVEMENT_CLASSES:
            raise GeographyError(f"corridor {corridor_id}: invalid movement classes")
        if not classes <= set(anchors[corridor["fromAnchorId"]]["movementClasses"]) or not classes <= set(anchors[corridor["toAnchorId"]]["movementClasses"]):
            raise GeographyError(f"corridor {corridor_id}: endpoint movement classes are incompatible")
        via = corridor.get("viaFeatureIds")
        if not isinstance(via, list) or not via or any(feature_id not in features for feature_id in via):
            raise GeographyError(f"corridor {corridor_id}: missing authoritative feature reference")

    # Every movement network must connect all instances which advertise that class;
    # inland-only and island-only instances are intentionally absent from the other network.
    for movement in ("land", "naval"):
        edges = []
        nodes = set()
        for anchor in anchors.values():
            if anchor.get("pairId") and movement in anchor.get("movementClasses", []):
                pair = anchors[anchor["pairId"]]
                edges.append((anchor["instanceId"], pair["instanceId"]))
                nodes.update(edges[-1])
        expected_nodes = {item["id"] for item in source["instances"] if movement in item["movementClasses"]}
        if nodes != expected_nodes:
            raise GeographyError(f"Africa {movement} network coverage mismatch: expected {sorted(expected_nodes)}, got {sorted(nodes)}")
        if nodes:
            reached = {next(iter(nodes))}
            while True:
                expanded = reached | {b for a, b in edges if a in reached} | {a for a, b in edges if b in reached}
                if expanded == reached: break
                reached = expanded
            if reached != nodes:
                raise GeographyError(f"Africa {movement} instance graph is disconnected: {sorted(nodes-reached)}")

    # Check physical travel independently so a flying-only global edge cannot
    # mask a broken African land or sea connection.
    geography = world["regionalGeography"]
    for movement in ("land", "naval"):
        graph = {}
        for edge in geography["boundaries"] + geography["routes"]:
            if movement not in edge["movementClasses"]:
                continue
            first, second = edge["from"]["regionId"], edge["to"]["regionId"]
            graph.setdefault(first, set()).add(second)
            graph.setdefault(second, set()).add(first)
        if source["graphRegionId"] not in graph:
            raise GeographyError(f"Africa has no global {movement} connection")
        reached = {source["graphRegionId"]}
        pending = [source["graphRegionId"]]
        while pending:
            current = pending.pop()
            for neighbour in graph[current] - reached:
                reached.add(neighbour)
                pending.append(neighbour)
        if reached != set(graph):
            raise GeographyError(f"global {movement} graph is disconnected: {sorted(set(graph)-reached)}")
    return instances, anchors

def main(argv=None):
    import argparse, json, sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "scenario/geography/africa.json")
    parser.add_argument("--world", type=Path, default=ROOT / "scenario/world/world.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        source=json.loads(args.source.read_text(encoding="utf-8")); world=json.loads(args.world.read_text(encoding="utf-8"))
        validate(source, world)
        output=generate(source, world)
        if args.output: args.output.write_text(output, encoding="utf-8")
        print(f"Africa geography valid: {len(source['instances'])} instances, {sum(len(i['features']) for i in source['instances'])} features, {len(source['boundaryAnchors'])} anchors")
    except (OSError, json.JSONDecodeError, GeographyError) as error:
        print(f"Africa geography validation failed: {error}", file=sys.stderr); return 1
    return 0
if __name__ == "__main__": raise SystemExit(main())

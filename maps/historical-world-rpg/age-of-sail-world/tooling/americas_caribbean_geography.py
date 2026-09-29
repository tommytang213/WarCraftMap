#!/usr/bin/env python3
"""Validate and deterministically derive Americas/Caribbean spatial inputs."""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "scenario/geography/americas_caribbean.json"
DEFAULT_WORLD = ROOT / "scenario/world/world.json"
DEFAULT_MAPS = ROOT / "physical-maps.json"
_spec = importlib.util.spec_from_file_location("regional_coordinate_validation", Path(__file__).with_name("europe_geography.py"))
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
GeographyError = _base.GeographyError
MOVEMENT_CLASSES = {"land", "naval", "amphibious", "flying"}
NODE_CLASSES = {"land", "navigable_sea", "navigable_river", "island_coast", "impassable_barrier", "decorative_water"}
EXTRA_KINDS = {"archipelago", "lake", "desert_barrier", "traversal_corridor"}
REQUIRED_CORRIDORS = {
    "north_american_overland", "mississippi_navigation", "great_lakes_corridor",
    "panama_crossing", "caribbean_sea_lane", "amazon_navigation",
    "andean_overland", "south_american_overland", "atlantic_approach", "pacific_approach",
}
REQUIRED_GLOBAL_EDGES = {"north_atlantic_crossing", "south_atlantic_crossing", "pacific_americas_crossing"}


def _with_inventory(function, *args):
    original = _base.KINDS
    try:
        _base.KINDS = original | EXTRA_KINDS
        return function(*args)
    finally:
        _base.KINDS = original


def _reachable(nodes, links, start, movement):
    graph = defaultdict(set)
    for link in links:
        if movement in link["movementClasses"]:
            graph[link["from"]].add(link["to"])
            graph[link["to"]].add(link["from"])
    found, pending = set(), deque([start])
    while pending:
        node = pending.popleft()
        if node not in found:
            found.add(node)
            pending.extend(graph[node] - found)
    return found


def validate(source, world, physical_maps=None):
    instances, anchors = _with_inventory(_base.validate, source, world)
    geography = world["regionalGeography"]
    graph_anchors = _base._index(geography["anchors"], "global anchors")
    graph_edges = {item["id"]: item for group in ("boundaries", "routes") for item in geography[group]}
    if not REQUIRED_GLOBAL_EDGES <= set(graph_edges):
        raise GeographyError("global graph is missing an Americas transition contract")
    for anchor in anchors.values():
        global_id = anchor.get("globalAnchorId")
        if global_id and anchor.get("movementClasses") != graph_anchors[global_id].get("movementClasses"):
            raise GeographyError(f"anchor {anchor['id']}: movement classes differ from global endpoint")

    if physical_maps is None:
        physical_maps = json.loads(DEFAULT_MAPS.read_text(encoding="utf-8"))
    maps = _base._index(physical_maps.get("physicalMaps", []), "physical maps")
    assigned = {}
    for map_id, item in maps.items():
        for instance_id in item.get("assignments", {}).get("regionalInstanceIds", []):
            if instance_id in instances:
                if instance_id in assigned:
                    raise GeographyError(f"instance {instance_id}: assigned to multiple physical maps")
                assigned[instance_id] = map_id
    for instance_id, instance in instances.items():
        if instance.get("physicalMapId") not in maps or assigned.get(instance_id) != instance.get("physicalMapId"):
            raise GeographyError(f"instance {instance_id}: invalid physical-map reference or assignment")

    corridors = _base._index(source.get("requiredTraversalConnections", []), "requiredTraversalConnections")
    if set(corridors) != REQUIRED_CORRIDORS:
        raise GeographyError("requiredTraversalConnections: acceptance-critical corridor inventory mismatch")
    nodes = _base._index(source.get("navigationTopology", {}).get("nodes", []), "navigation nodes")
    links = _base._index(source.get("navigationTopology", {}).get("links", []), "navigation links")
    occupied = set(instances) | set(anchors) | {f["id"] for i in source["instances"] for f in i["features"]} | {d["id"] for d in source["distortions"]}
    if occupied & (set(nodes) | set(links) | set(corridors)) or set(nodes) & (set(links) | set(corridors)) or set(links) & set(corridors):
        raise GeographyError("navigation topology: stable IDs must be globally unique")
    for node_id, node in nodes.items():
        if node.get("instanceId") not in instances or node.get("class") not in NODE_CLASSES:
            raise GeographyError(f"navigation node {node_id}: invalid instance or class")
    for link_id, link in links.items():
        if link.get("from") not in nodes or link.get("to") not in nodes or link["from"] == link["to"]:
            raise GeographyError(f"navigation link {link_id}: invalid endpoint")
        movement = set(link.get("movementClasses", []))
        classes = {nodes[link["from"]]["class"], nodes[link["to"]]["class"]}
        if not movement or not movement <= MOVEMENT_CLASSES:
            raise GeographyError(f"navigation link {link_id}: invalid movement classes")
        if classes & {"decorative_water", "impassable_barrier"}:
            raise GeographyError(f"navigation link {link_id}: routes cannot cross isolated water or impassable barriers")
        water = {"navigable_sea", "navigable_river", "island_coast"}
        if "naval" in movement and not classes <= water:
            raise GeographyError(f"navigation link {link_id}: naval route leaves navigable water")
        if "land" in movement and classes & water:
            raise GeographyError(f"navigation link {link_id}: land route enters water")
    for corridor_id, corridor in corridors.items():
        start, end = corridor.get("fromNodeId"), corridor.get("toNodeId")
        movement = set(corridor.get("movementClasses", []))
        if start not in nodes or end not in nodes or not movement or not movement <= MOVEMENT_CLASSES:
            raise GeographyError(f"connection {corridor_id}: invalid nodes or movement classes")
        for mode in movement:
            if end not in _reachable(nodes, links.values(), start, mode):
                raise GeographyError(f"connection {corridor_id}: {mode} route is disconnected")
    density = source.get("densityRules", {})
    for instance_id, instance in instances.items():
        count = len(instance["features"])
        if not density.get("minFeaturesPerInstance", 0) <= count <= density.get("maxFeaturesPerInstance", -1):
            raise GeographyError(f"instance {instance_id}: feature density outside declared range")
        complexity = instance.get("complexity", {})
        if (not 0 < complexity.get("generationWeight", 0) <= 1 or complexity.get("terrainBands", 0) > 6
                or complexity.get("waterBodies", 0) > 5 or complexity.get("pathingChokepoints", 0) > 7):
            raise GeographyError(f"instance {instance_id}: complexity budget exceeded")
    ratio = len(anchors) / len(instances)
    if not density.get("minAnchorsPerInstance", 0) <= ratio <= density.get("maxAnchorsPerInstance", -1):
        raise GeographyError("regional anchor density outside declared range")
    return instances, anchors


def generate(source, world, physical_maps=None):
    validate(source, world, physical_maps)
    return _with_inventory(_base.generate, source, world)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--world", type=Path, default=DEFAULT_WORLD)
    parser.add_argument("--physical-maps", type=Path, default=DEFAULT_MAPS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        source = json.loads(args.source.read_text(encoding="utf-8"))
        world = json.loads(args.world.read_text(encoding="utf-8"))
        maps = json.loads(args.physical_maps.read_text(encoding="utf-8"))
        output = generate(source, world, maps)
        if args.output:
            args.output.write_text(output, encoding="utf-8")
        print(f"Americas/Caribbean geography valid: {len(source['instances'])} instances, {sum(len(i['features']) for i in source['instances'])} features, {len(source['boundaryAnchors'])} anchors")
    except (OSError, json.JSONDecodeError, GeographyError) as error:
        print(f"Americas/Caribbean geography validation failed: {error}", file=__import__("sys").stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


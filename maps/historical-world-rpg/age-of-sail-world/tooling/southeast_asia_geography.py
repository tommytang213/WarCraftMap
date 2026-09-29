#!/usr/bin/env python3
"""Validate and deterministically derive Southeast Asia spatial inputs."""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "scenario" / "geography" / "southeast_asia.json"
DEFAULT_WORLD = ROOT / "scenario" / "world" / "world.json"
_spec = importlib.util.spec_from_file_location("regional_coordinate_validation", Path(__file__).with_name("europe_geography.py"))
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
GeographyError = _base.GeographyError
MOVEMENT_CLASSES = {"land", "naval", "amphibious", "flying"}
NODE_CLASSES = {"land", "navigable_sea", "island_coast", "impassable_barrier", "decorative_water"}
REQUIRED_CORRIDORS = {"mainland_corridor", "bay_of_bengal_approach", "malacca_corridor", "south_china_sea_route", "sunda_java_route", "philippine_route", "eastern_archipelago_route"}


def _with_inventory(function, *args):
    original = _base.KINDS
    try:
        _base.KINDS = original | {"archipelago", "traversal_corridor"}
        return function(*args)
    finally:
        _base.KINDS = original


def _reachable(nodes, links, start, movement):
    graph = defaultdict(set)
    for link in links:
        if movement in link["movementClasses"]:
            graph[link["from"]].add(link["to"]); graph[link["to"]].add(link["from"])
    found, pending = set(), deque([start])
    while pending:
        node = pending.popleft()
        if node not in found:
            found.add(node); pending.extend(graph[node] - found)
    return found


def validate(source, world):
    """Validate source geography, global seams, topology, density, and corridors."""
    instances, anchors = _with_inventory(_base.validate, source, world)
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
        if not movement or not movement <= MOVEMENT_CLASSES:
            raise GeographyError(f"navigation link {link_id}: invalid movement classes")
        classes = {nodes[link["from"]]["class"], nodes[link["to"]]["class"]}
        if "decorative_water" in classes or "impassable_barrier" in classes:
            raise GeographyError(f"navigation link {link_id}: routes cannot cross decorative water or impassable barriers")
        if "naval" in movement and not classes <= {"navigable_sea", "island_coast"}:
            raise GeographyError(f"navigation link {link_id}: naval route leaves navigable water")
        if "land" in movement and classes & {"navigable_sea", "island_coast"}:
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
    ratio = len(anchors) / len(instances)
    if not density.get("minAnchorsPerInstance", 0) <= ratio <= density.get("maxAnchorsPerInstance", -1):
        raise GeographyError("regional anchor density outside declared range")
    return instances, anchors


def generate(source, world):
    validate(source, world)
    return _with_inventory(_base.generate, source, world)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--world", type=Path, default=DEFAULT_WORLD)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        source = json.loads(args.source.read_text(encoding="utf-8")); world = json.loads(args.world.read_text(encoding="utf-8"))
        output = generate(source, world)
        if args.output: args.output.write_text(output, encoding="utf-8")
        print(f"Southeast Asia geography valid: {len(source['instances'])} instances, {sum(len(i['features']) for i in source['instances'])} features, {len(source['boundaryAnchors'])} anchors")
    except (OSError, json.JSONDecodeError, GeographyError) as error:
        print(f"Southeast Asia geography validation failed: {error}", file=__import__("sys").stderr); return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

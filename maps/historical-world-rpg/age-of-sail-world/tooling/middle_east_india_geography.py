#!/usr/bin/env python3
"""Validate and deterministically derive Middle East/India spatial inputs."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "scenario" / "geography" / "middle_east_india.json"
DEFAULT_WORLD = ROOT / "scenario" / "world" / "world.json"

_spec = importlib.util.spec_from_file_location("regional_coordinate_validation", Path(__file__).with_name("europe_geography.py"))
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
GeographyError = _base.GeographyError
MOVEMENT_CLASSES = {"land", "naval", "amphibious", "flying"}
REQUIRED_CONNECTIONS = {"route_eastern_mediterranean", "route_red_sea", "route_persian_gulf", "route_arabian_sea", "route_central_asia", "route_southeast_asia"}


def _with_feature_inventory(function, *args):
    original = _base.KINDS
    try:
        _base.KINDS = original | {"desert_barrier"}
        return function(*args)
    finally:
        _base.KINDS = original


def validate(source, world):
    """Validate scenario-owned instances, seams, graph bindings, and budgets."""
    result = _with_feature_inventory(_base.validate, source, world)
    anchors = {item["id"]: item for item in source.get("boundaryAnchors", [])}
    connections = _base._index(source.get("requiredTraversalConnections", []), "requiredTraversalConnections")
    if set(connections) != REQUIRED_CONNECTIONS:
        raise GeographyError("requiredTraversalConnections: acceptance-critical route inventory mismatch")
    occupied = set(result[0]) | set(anchors) | {feature["id"] for instance in source["instances"] for feature in instance["features"]}
    if occupied & set(connections):
        raise GeographyError("requiredTraversalConnections: stable IDs must be globally unique")
    for connection_id, connection in connections.items():
        route_anchors = connection.get("anchorIds")
        movement = set(connection.get("movementClasses", []))
        if not isinstance(route_anchors, list) or not route_anchors or any(anchor_id not in anchors for anchor_id in route_anchors):
            raise GeographyError(f"connection {connection_id}: missing boundary anchor")
        if not movement or not movement <= MOVEMENT_CLASSES:
            raise GeographyError(f"connection {connection_id}: invalid movement classes")
        if any(not movement <= set(anchors[anchor_id]["movementClasses"]) for anchor_id in route_anchors):
            raise GeographyError(f"connection {connection_id}: incompatible anchor movement classes")
    return result


def generate(source, world):
    """Return canonical derived source/local coordinates without becoming authority."""
    validate(source, world)
    return _with_feature_inventory(_base.generate, source, world)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--world", type=Path, default=DEFAULT_WORLD)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        source = json.loads(args.source.read_text(encoding="utf-8"))
        world = json.loads(args.world.read_text(encoding="utf-8"))
        output = generate(source, world)
        if args.output:
            args.output.write_text(output, encoding="utf-8")
        print(f"Middle East/India geography valid: {len(source['instances'])} instances, "
              f"{sum(len(i['features']) for i in source['instances'])} features, "
              f"{len(source['boundaryAnchors'])} anchors")
    except (OSError, json.JSONDecodeError, GeographyError) as error:
        print(f"Middle East/India geography validation failed: {error}", file=__import__("sys").stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

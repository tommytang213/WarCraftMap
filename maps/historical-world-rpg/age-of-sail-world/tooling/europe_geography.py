#!/usr/bin/env python3
"""Validate and deterministically derive Europe terrain inputs from scenario data."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "scenario" / "geography" / "europe.json"
DEFAULT_WORLD = ROOT / "scenario" / "world" / "world.json"
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
KINDS = {"coastline", "island", "strait", "river", "mountain_barrier"}


class GeographyError(ValueError):
    pass


def _index(items, label):
    result = {}
    for item in items:
        ident = item.get("id") if isinstance(item, dict) else None
        if not isinstance(ident, str) or not ID_RE.fullmatch(ident):
            raise GeographyError(f"{label}: invalid stable ID {ident!r}")
        if ident in result:
            raise GeographyError(f"{label}: duplicate stable ID {ident!r}")
        result[ident] = item
    return result


def _finite_pair(value, label):
    if not isinstance(value, list) or len(value) != 2 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value):
        raise GeographyError(f"{label}: expected two finite coordinates")


def transform_point(instance, source, precision, distortion=None):
    """Apply the scenario-owned affine transform and an explicitly declared offset."""
    transform = instance["transform"]
    origin, scale, offset = transform["sourceOrigin"], transform["scale"], transform["offset"]
    delta = (distortion or {}).get("offset", [0, 0])
    return [round((source[i] - origin[i]) * scale[i] + offset[i] + delta[i], precision) for i in range(2)]


def _inside(point, bounds, tolerance=0):
    return (bounds["minX"] - tolerance <= point[0] <= bounds["maxX"] + tolerance and
            bounds["minY"] - tolerance <= point[1] <= bounds["maxY"] + tolerance)


def validate(source, world):
    if source.get("schemaVersion") != 1:
        raise GeographyError("schemaVersion must be 1")
    rules = source.get("coordinateRules", {})
    if rules.get("sourceCrs") != "EPSG:4326" or rules.get("axisOrder") != ["longitude", "latitude"]:
        raise GeographyError("coordinateRules: EPSG:4326 longitude/latitude is required")
    precision = rules.get("precisionDecimals")
    if not isinstance(precision, int) or not 0 <= precision <= 6:
        raise GeographyError("coordinateRules.precisionDecimals must be between 0 and 6")

    geography = world.get("regionalGeography", {})
    graph_regions = _index(geography.get("regions", []), "global regions")
    graph_areas = _index(geography.get("areas", []), "global areas")
    graph_anchors = _index(geography.get("anchors", []), "global anchors")
    if source.get("graphRegionId") not in graph_regions:
        raise GeographyError(f"missing global region {source.get('graphRegionId')!r}")

    required_feature_ids = source.get("requiredFeatureIds", {})
    allowed_kinds = set(required_feature_ids)
    if not KINDS <= allowed_kinds:
        raise GeographyError(f"requiredFeatureIds must include {sorted(KINDS)}")
    instances = _index(source.get("instances", []), "instances")
    anchors = _index(source.get("boundaryAnchors", []), "boundaryAnchors")
    distortions = _index(source.get("distortions", []), "distortions")
    all_ids = set(instances)
    feature_owner = {}
    for instance_id, instance in instances.items():
        if instance.get("graphRegionId") != source["graphRegionId"]:
            raise GeographyError(f"instance {instance_id}: graphRegionId must be {source['graphRegionId']!r}")
        area = graph_areas.get(instance.get("graphAreaId"))
        if not area or area.get("regionId") != source["graphRegionId"]:
            raise GeographyError(f"instance {instance_id}: incompatible global graph area")
        if not instance.get("seamRationale"):
            raise GeographyError(f"instance {instance_id}: seamRationale is required")
        for key in ("sourceOrigin", "scale", "offset"):
            _finite_pair(instance.get("transform", {}).get(key), f"instance {instance_id}.{key}")
        if any(v <= 0 for v in instance["transform"]["scale"]):
            raise GeographyError(f"instance {instance_id}: scale must preserve north/east orientation")
        bounds = instance.get("localBounds", {})
        if set(bounds) != {"minX", "minY", "maxX", "maxY"} or bounds["minX"] >= bounds["maxX"] or bounds["minY"] >= bounds["maxY"]:
            raise GeographyError(f"instance {instance_id}: invalid localBounds")
        features = _index(instance.get("features", []), f"instance {instance_id} features")
        point_count = 0
        for feature_id, feature in features.items():
            if feature_id in all_ids:
                raise GeographyError(f"stable ID {feature_id!r} is not globally unique")
            all_ids.add(feature_id)
            if feature.get("kind") not in allowed_kinds:
                raise GeographyError(f"feature {feature_id}: invalid kind")
            points = feature.get("points")
            if not isinstance(points, list) or len(points) < 2:
                raise GeographyError(f"feature {feature_id}: at least two control points are required")
            point_count += len(points)
            for number, point in enumerate(points):
                _finite_pair(point, f"feature {feature_id} point {number}")
                if not -180 <= point[0] <= 180 or not -90 <= point[1] <= 90:
                    raise GeographyError(f"feature {feature_id}: source coordinate is outside EPSG:4326")
                local = transform_point(instance, point, precision)
                if not _inside(local, bounds):
                    raise GeographyError(f"feature {feature_id}: transformed point {number} {local} is outside {instance_id}")
            feature_owner[feature_id] = (instance_id, feature["kind"])
        budget = instance.get("budget", {})
        instance_anchor_count = sum(a.get("instanceId") == instance_id for a in anchors.values())
        if len(features) > budget.get("maxFeatures", -1):
            raise GeographyError(f"instance {instance_id}: {len(features)} features exceed maxFeatures {budget.get('maxFeatures')}")
        if point_count > budget.get("maxControlPoints", -1):
            raise GeographyError(f"instance {instance_id}: {point_count} control points exceed maxControlPoints {budget.get('maxControlPoints')}")
        if instance_anchor_count > budget.get("maxBoundaryAnchors", -1):
            raise GeographyError(f"instance {instance_id}: {instance_anchor_count} anchors exceed maxBoundaryAnchors {budget.get('maxBoundaryAnchors')}")

    for kind in sorted(allowed_kinds):
        required = source.get("requiredFeatureIds", {}).get(kind)
        if not isinstance(required, list) or not required:
            raise GeographyError(f"requiredFeatureIds.{kind}: non-empty list required")
        if len(required) != len(set(required)):
            raise GeographyError(f"requiredFeatureIds.{kind}: duplicate feature assignment")
        for feature_id in required:
            owner = feature_owner.get(feature_id)
            if not owner or owner[1] != kind:
                raise GeographyError(f"required {kind} {feature_id!r} has no single authoritative source feature")
    declared = {feature_id for ids in source["requiredFeatureIds"].values() for feature_id in ids}
    if declared != set(feature_owner):
        raise GeographyError(f"feature inventory mismatch: unclassified={sorted(set(feature_owner)-declared)}, missing={sorted(declared-set(feature_owner))}")

    paired = set()
    for anchor_id, anchor in anchors.items():
        if anchor_id in all_ids:
            raise GeographyError(f"stable ID {anchor_id!r} is not globally unique")
        all_ids.add(anchor_id)
        instance = instances.get(anchor.get("instanceId"))
        if not instance:
            raise GeographyError(f"anchor {anchor_id}: missing instance")
        _finite_pair(anchor.get("source"), f"anchor {anchor_id}.source")
        _finite_pair(anchor.get("local"), f"anchor {anchor_id}.local")
        expected = transform_point(instance, anchor["source"], precision, anchor.get("distortion"))
        max_error = max(abs(expected[i] - anchor["local"][i]) for i in range(2))
        if max_error > rules["maxUndeclaredDisplacementCells"]:
            raise GeographyError(f"anchor {anchor_id}: local coordinate differs from declared transform by {max_error:.2f} cells")
        if not _inside(anchor["local"], instance["localBounds"], rules["seamLocalToleranceCells"]):
            raise GeographyError(f"anchor {anchor_id}: local coordinate is outside its instance")
        pair_id, global_id = anchor.get("pairId"), anchor.get("globalAnchorId")
        if bool(pair_id) == bool(global_id):
            raise GeographyError(f"anchor {anchor_id}: exactly one pairId or globalAnchorId is required")
        if global_id:
            graph_anchor = graph_anchors.get(global_id)
            if not graph_anchor or graph_anchor.get("regionId") != source["graphRegionId"]:
                raise GeographyError(f"anchor {anchor_id}: missing compatible global anchor {global_id!r}")
        else:
            pair = anchors.get(pair_id)
            if not pair or pair.get("pairId") != anchor_id or pair.get("instanceId") == anchor.get("instanceId"):
                raise GeographyError(f"anchor {anchor_id}: boundary pair is missing, non-reciprocal, or in the same instance")
            if anchor.get("movementClasses") != pair.get("movementClasses"):
                raise GeographyError(f"anchor {anchor_id}: movement classes differ from pair {pair_id}")
            distance = math.dist(anchor["source"], pair["source"])
            if distance > rules["seamSourceToleranceDegrees"]:
                raise GeographyError(f"anchor {anchor_id}: seam discontinuity {distance:.4f} degrees exceeds tolerance")
            paired.add(tuple(sorted((anchor_id, pair_id))))

    for distortion_id, distortion in distortions.items():
        if distortion_id in all_ids:
            raise GeographyError(f"stable ID {distortion_id!r} is not globally unique")
        all_ids.add(distortion_id)
        anchor = anchors.get(distortion.get("anchorId"))
        if not anchor or "distortion" not in anchor:
            raise GeographyError(f"distortion {distortion_id}: missing distorted anchor")
        actual = math.dist([0, 0], anchor["distortion"]["offset"])
        if abs(actual - distortion.get("displacementCells", -1)) > 0.01:
            raise GeographyError(f"distortion {distortion_id}: displacement does not match offset")
        if distortion.get("orientationDeltaDegrees", math.inf) > rules["orientationToleranceDegrees"]:
            raise GeographyError(f"distortion {distortion_id}: orientation exceeds configured tolerance")
        if distortion.get("adjacencyGapCells", math.inf) > rules["adjacencyToleranceCells"]:
            raise GeographyError(f"distortion {distortion_id}: adjacency exceeds configured tolerance")
        if not distortion.get("preservesOrientation") or not distortion.get("preservesAdjacency") or not distortion.get("reason"):
            raise GeographyError(f"distortion {distortion_id}: orientation, adjacency, and reason must be declared")

    connected = {next(iter(instances))}
    while True:
        expanded = connected | {anchors[b].get("instanceId") for pair in paired for b in pair if anchors[pair[0]]["instanceId"] in connected or anchors[pair[1]]["instanceId"] in connected}
        if expanded == connected:
            break
        connected = expanded
    if connected != set(instances):
        raise GeographyError(f"Europe instance graph is disconnected: {sorted(set(instances)-connected)}")
    global_bindings = {a.get("globalAnchorId") for a in anchors.values() if a.get("globalAnchorId")}
    referenced_by_global_graph = {e[side]["anchorId"] for group in ("boundaries", "routes") for e in geography.get(group, []) for side in ("from", "to") if e[side]["regionId"] == source["graphRegionId"]}
    if global_bindings != referenced_by_global_graph:
        raise GeographyError(f"global anchor coverage mismatch: expected {sorted(referenced_by_global_graph)}, got {sorted(global_bindings)}")
    return instances, anchors


def generate(source, world):
    instances, anchors = validate(source, world)
    precision = source["coordinateRules"]["precisionDecimals"]
    generated = {"sourceId": source["id"], "schemaVersion": source["schemaVersion"], "instances": []}
    for instance_id in sorted(instances):
        instance = instances[instance_id]
        generated["instances"].append({
            "id": instance_id,
            "localBounds": instance["localBounds"],
            "features": [{"id": feature["id"], "kind": feature["kind"], "sourcePoints": feature["points"], "localPoints": [transform_point(instance, p, precision) for p in feature["points"]]} for feature in sorted(instance["features"], key=lambda f: f["id"])],
            "anchors": [{"id": anchor["id"], "source": anchor["source"], "local": anchor["local"]} for anchor in sorted(anchors.values(), key=lambda a: a["id"]) if anchor["instanceId"] == instance_id]
        })
    return json.dumps(generated, indent=2, sort_keys=True, separators=(",", ": ")) + "\n"


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
        print(f"Europe geography valid: {len(source['instances'])} instances, {sum(len(i['features']) for i in source['instances'])} features, {len(source['boundaryAnchors'])} anchors")
    except (OSError, json.JSONDecodeError, GeographyError) as error:
        print(f"Europe geography validation failed: {error}", file=__import__("sys").stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

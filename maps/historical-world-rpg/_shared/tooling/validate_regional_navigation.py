from collections import deque
import math

MOVEMENT_CLASSES = {"land", "naval", "amphibious", "flying"}


def validate(data, fail, require_id, unique_index):
    geography = data.get("regionalGeography")
    if not isinstance(geography, dict):
        fail("regionalGeography: object is required")
    if set(geography) != {"regions", "areas", "anchors", "boundaries", "routes"}:
        fail("regionalGeography: regions, areas, anchors, boundaries, and routes are required")
    regions = unique_index(geography.get("regions", []), "regionalGeography.regions")
    areas = unique_index(geography.get("areas", []), "regionalGeography.areas")
    anchors = unique_index(geography.get("anchors", []), "regionalGeography.anchors")
    boundaries = unique_index(geography.get("boundaries", []), "regionalGeography.boundaries")
    routes = unique_index(geography.get("routes", []), "regionalGeography.routes")

    all_ids = {}
    for kind, records in (("region", regions), ("area", areas), ("anchor", anchors), ("boundary", boundaries), ("route", routes)):
        for stable_id in records:
            require_id(stable_id, f"regional {kind}")
            if stable_id in all_ids:
                fail(f"regional stable ID {stable_id!r} is shared by {all_ids[stable_id]} and {kind}")
            all_ids[stable_id] = kind
    if not regions:
        fail("regionalGeography.regions: at least one region is required")

    for region_id, region in regions.items():
        if not isinstance(region.get("name"), str) or not region["name"]:
            fail(f"region {region_id}: name is required")
        if region.get("orientation") not in {"north_up", "east_up", "south_up", "west_up"}:
            fail(f"region {region_id}: invalid orientation")
    for area_id, area in areas.items():
        if area.get("regionId") not in regions:
            fail(f"area {area_id}: missing region {area.get('regionId')!r}")
        bounds = area.get("bounds")
        if not isinstance(bounds, dict) or set(bounds) != {"minX", "minY", "maxX", "maxY"}:
            fail(f"area {area_id}: invalid bounds")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in bounds.values()):
            fail(f"area {area_id}: bounds must be finite numbers")
        if bounds["minX"] >= bounds["maxX"] or bounds["minY"] >= bounds["maxY"]:
            fail(f"area {area_id}: bounds must have positive extent")
    for anchor_id, anchor in anchors.items():
        region_id, area_id = anchor.get("regionId"), anchor.get("areaId")
        if region_id not in regions or area_id not in areas or areas[area_id].get("regionId") != region_id:
            fail(f"anchor {anchor_id}: region and area must exist and match")
        classes = anchor.get("movementClasses")
        if not isinstance(classes, list) or not classes or len(classes) != len(set(classes)) or not set(classes) <= MOVEMENT_CLASSES:
            fail(f"anchor {anchor_id}: invalid movement classes")
        position = anchor.get("position")
        if not isinstance(position, dict) or set(position) != {"x", "y"} or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in position.values()):
            fail(f"anchor {anchor_id}: position must contain finite x and y")
        bounds = areas[area_id]["bounds"]
        if not bounds["minX"] <= position["x"] <= bounds["maxX"] or not bounds["minY"] <= position["y"] <= bounds["maxY"]:
            fail(f"anchor {anchor_id}: position is outside its local area")

    def endpoint(record_id, value, label, classes):
        if not isinstance(value, dict) or set(value) != {"regionId", "anchorId"}:
            fail(f"{label} {record_id}: endpoint requires regionId and anchorId")
        anchor = anchors.get(value.get("anchorId"))
        if value.get("regionId") not in regions or not anchor or anchor.get("regionId") != value.get("regionId"):
            fail(f"{label} {record_id}: endpoint region and anchor must exist and match")
        if not set(classes) <= set(anchor.get("movementClasses", [])):
            fail(f"{label} {record_id}: endpoint anchor has incompatible movement classes")

    edges = []
    for label, records in (("boundary", boundaries), ("route", routes)):
        for record_id, record in records.items():
            classes = record.get("movementClasses")
            if not isinstance(classes, list) or not classes or len(classes) != len(set(classes)) or not set(classes) <= MOVEMENT_CLASSES:
                fail(f"{label} {record_id}: invalid movement classes")
            if not isinstance(record.get("directed"), bool):
                fail(f"{label} {record_id}: directed must be boolean")
            endpoint(record_id, record.get("from"), label, classes)
            endpoint(record_id, record.get("to"), label, classes)
            if record["from"]["regionId"] == record["to"]["regionId"]:
                fail(f"{label} {record_id}: endpoints must use different regions")
            if label == "route":
                duration = record.get("durationDays")
                if isinstance(duration, bool) or not isinstance(duration, int) or duration < 1:
                    fail(f"route {record_id}: durationDays must be positive")
                hooks = record.get("encounterHookIds")
                if not isinstance(hooks, list) or len(hooks) != len(set(hooks)):
                    fail(f"route {record_id}: encounterHookIds must be a unique array")
                for hook in hooks:
                    require_id(hook, f"route {record_id}.encounterHookIds")
            edges.append(record)


    graph = {region_id: set() for region_id in regions}
    for edge in edges:
        a, b = edge["from"]["regionId"], edge["to"]["regionId"]
        graph[a].add(b)
        if not edge["directed"]:
            graph[b].add(a)
    reached, pending = set(), deque([next(iter(regions))])
    while pending:
        current = pending.popleft()
        if current in reached:
            continue
        reached.add(current)
        pending.extend(graph[current] - reached)
    if reached != set(regions):
        fail(f"regional geography is not globally reachable: {sorted(set(regions) - reached)}")
    return regions, areas, anchors, boundaries, routes

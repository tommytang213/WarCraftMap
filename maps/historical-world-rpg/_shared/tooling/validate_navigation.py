from collections import deque
import math


MOVEMENT_CLASSES = {"land", "naval", "amphibious", "flying"}


def validate(data, fail, require_id, unique_index, strategic_units):
    zones = unique_index(data.get("navigationZones", []), "navigationZones")
    safe_points = unique_index(data.get("navigationSafePoints", []), "navigationSafePoints")
    states = unique_index(data.get("activeUnitNavigationStates", []), "activeUnitNavigationStates")

    for zone_id, zone in zones.items():
        domain = f"navigation zone {zone_id}"
        classes = zone.get("movementClasses")
        if not isinstance(classes, list) or not classes:
            fail(f"{domain}.movementClasses: at least one class is required")
        if len(set(classes)) != len(classes) or not set(classes) <= MOVEMENT_CLASSES:
            fail(f"{domain}.movementClasses: invalid or duplicate movement class")
        connections = zone.get("connections")
        if not isinstance(connections, dict) or set(connections) != set(classes):
            fail(f"{domain}.connections: must define exactly its movement classes")
        for movement_class, targets in connections.items():
            if not isinstance(targets, list) or len(targets) != len(set(targets)):
                fail(f"{domain}.connections.{movement_class}: must be a unique array")
            for target in targets:
                require_id(target, f"{domain}.connections.{movement_class}")
                if target == zone_id or target not in zones:
                    fail(f"{domain}: invalid connection to {target!r}")
                other = zones[target]
                if movement_class not in other.get("movementClasses", []):
                    fail(f"{domain}: {target!r} does not support {movement_class}")
                if zone_id not in other.get("connections", {}).get(movement_class, []):
                    fail(f"{domain}: connection to {target!r} is not reciprocal for {movement_class}")

    for point_id, point in safe_points.items():
        domain = f"navigation safe point {point_id}"
        zone_id = point.get("zoneId")
        if zone_id not in zones:
            fail(f"{domain}: missing zone {zone_id!r}")
        classes = point.get("movementClasses")
        if not isinstance(classes, list) or not classes or len(classes) != len(set(classes)):
            fail(f"{domain}.movementClasses: at least one unique class is required")
        if not set(classes) <= set(zones[zone_id].get("movementClasses", [])):
            fail(f"{domain}: movement class is not supported by zone {zone_id!r}")
        position = point.get("position")
        if not isinstance(position, dict) or set(position) != {"x", "y"}:
            fail(f"{domain}.position: x and y are required")
        if any(isinstance(position[k], bool) or not isinstance(position[k], (int, float)) or not math.isfinite(position[k]) for k in ("x", "y")):
            fail(f"{domain}.position: coordinates must be numbers")
        if point.get("kind") not in {"safe_point", "recovery_anchor"}:
            fail(f"{domain}: invalid kind")

    seen_units = set()
    for state_id, state in states.items():
        domain = f"active unit navigation state {state_id}"
        unit_id = state.get("unitId")
        if unit_id not in strategic_units:
            fail(f"{domain}: missing strategic unit {unit_id!r}")
        if unit_id in seen_units:
            fail(f"{domain}: duplicate state for unit {unit_id!r}")
        seen_units.add(unit_id)
        if strategic_units[unit_id].get("runtimeInstantiation", {}).get("state") != "active":
            fail(f"{domain}: navigation state requires an active unit")
        movement_class = state.get("movementClass")
        if movement_class not in MOVEMENT_CLASSES:
            fail(f"{domain}: invalid movementClass")
        expected = "naval" if strategic_units[unit_id].get("kind") == "ship" else "land"
        if movement_class != expected:
            fail(f"{domain}: {strategic_units[unit_id].get('kind')} requires {expected} movement")
        zone_id = state.get("currentZoneId")
        if zone_id not in zones or movement_class not in zones[zone_id].get("movementClasses", []):
            fail(f"{domain}: current zone does not support {movement_class}")
        last_safe = state.get("lastSafePosition")
        if not isinstance(last_safe, dict) or set(last_safe) != {"zoneId", "x", "y"}:
            fail(f"{domain}.lastSafePosition: zoneId, x, and y are required")
        last_zone_id = last_safe.get("zoneId")
        if last_zone_id not in zones or movement_class not in zones[last_zone_id].get("movementClasses", []):
            fail(f"{domain}: last-safe zone does not support {movement_class}")
        if any(isinstance(last_safe[k], bool) or not isinstance(last_safe[k], (int, float)) or not math.isfinite(last_safe[k]) for k in ("x", "y")):
            fail(f"{domain}.lastSafePosition: coordinates must be finite numbers")
        if not _reachable(zones, movement_class, zone_id, last_zone_id):
            fail(f"{domain}: last-safe point is disconnected from current zone")

    return zones, safe_points, states


def _reachable(zones, movement_class, start, destination):
    pending, visited = deque([start]), set()
    while pending:
        current = pending.popleft()
        if current == destination:
            return True
        if current in visited:
            continue
        visited.add(current)
        pending.extend(zones[current].get("connections", {}).get(movement_class, []))
    return False

"""Headless navigation graph and recovery policy.

This module selects a destination only. Warcraft runtime movement belongs in a
future adapter and must re-verify the returned destination before teleporting.
"""

MOVEMENT_CLASSES = frozenset({"land", "naval", "amphibious", "flying"})
INELIGIBLE_CATEGORIES = frozenset({"structure", "dummy"})
RECOVERY_PRIORITY = ("nearby_safe_point", "last_safe_point", "recovery_anchor")


def _adjacency(zones, movement_class):
    return {
        zone_id: set(zone.get("connections", {}).get(movement_class, ()))
        for zone_id, zone in zones.items()
        if movement_class in zone.get("movementClasses", ())
    }


def is_reachable(zones, movement_class, origin_zone_id, destination_zone_id):
    """Return whether two zones share a movement-class graph component."""
    if movement_class not in MOVEMENT_CLASSES:
        return False
    graph = _adjacency(zones, movement_class)
    if origin_zone_id not in graph or destination_zone_id not in graph:
        return False
    pending, visited = [origin_zone_id], set()
    while pending:
        current = pending.pop()
        if current == destination_zone_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        pending.extend(graph[current] - visited)
    return False


def choose_recovery_destination(
    *, unit_category, movement_class, current_zone_id, last_safe_point,
    nearby_safe_points, recovery_anchors, zones
):
    """Apply the recovery priority contract without moving a runtime object.

    Candidates must be explicitly verified safe, support the unit's movement
    class, and be connected to its current zone. Lists retain scenario/runtime
    ordering, allowing a future caller to provide nearest-first nearby points.
    """
    if unit_category in INELIGIBLE_CATEGORIES or unit_category != "mobile":
        return None

    def valid(candidate, stored=False):
        return bool(
            candidate
            and (stored or candidate.get("verifiedSafe") is True)
            and (stored or movement_class in candidate.get("movementClasses", ()))
            and is_reachable(
                zones, movement_class, current_zone_id, candidate.get("zoneId")
            )
        )

    for point in nearby_safe_points:
        if valid(point):
            return {"source": "nearby_safe_point", "destination": point}
    if valid(last_safe_point, stored=True):
        return {"source": "last_safe_point", "destination": last_safe_point}
    for anchor in recovery_anchors:
        if valid(anchor):
            return {"source": "recovery_anchor", "destination": anchor}
    return None

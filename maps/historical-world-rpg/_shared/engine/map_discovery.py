"""Discovery-authorized world/regional map models and informational focus APIs.

The service owns no Warcraft handles and never mutates navigation/entity state.
Scenario data supplies every label and coordinate; campaign state supplies only
stable IDs and the precision the player has earned.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Mapping


KNOWLEDGE_KINDS = ("regions", "settlements", "landmarks", "routes", "boundaries", "pointsOfInterest")
LOCATION_KINDS = ("settlement", "landmark", "pointOfInterest")
PRECISIONS = frozenset({"region", "approximate", "exact"})


class MapDiscoveryError(ValueError):
    pass


@dataclass(frozen=True)
class MapFocus:
    context: str
    region_id: str | None
    target_id: str | None
    precision: str
    areas: tuple[dict, ...] = ()


def empty_knowledge() -> dict:
    return {"version": 1, **{kind: [] for kind in KNOWLEDGE_KINDS}, "locations": {}, "searchAreas": {}}


class DiscoveryKnowledge:
    """Authoritative, serializable knowledge independent of runtime objects."""

    def __init__(self, catalog: Mapping, state: Mapping | None = None):
        self.catalog = copy.deepcopy(dict(catalog))
        self.state = copy.deepcopy(dict(state or empty_knowledge()))
        self._indexes = _catalog_indexes(self.catalog)
        self._validate()

    def _validate(self):
        if self.state.get("version") != 1:
            raise MapDiscoveryError("unsupported map knowledge version")
        for kind in KNOWLEDGE_KINDS:
            values = self.state.get(kind)
            if not isinstance(values, list) or len(values) != len(set(values)):
                raise MapDiscoveryError(f"knowledge {kind} must be a unique ID list")
            targets = self._indexes[kind]
            missing = [ident for ident in values if ident not in targets]
            if missing:
                raise MapDiscoveryError(f"knowledge {kind} contains invalid reference {missing[0]!r}")
        locations = self.state.get("locations")
        if not isinstance(locations, dict):
            raise MapDiscoveryError("knowledge locations must be an object")
        for ident, value in locations.items():
            record = self._location(ident)
            if not isinstance(value, dict) or value.get("precision") not in PRECISIONS:
                raise MapDiscoveryError(f"location {ident!r} has invalid precision")
            if value.get("regionId") != record["regionId"]:
                raise MapDiscoveryError(f"location {ident!r} has invalid region")
            if value["precision"] == "approximate" and not value.get("searchAreaIds"):
                raise MapDiscoveryError(f"location {ident!r} approximate knowledge needs a search area")
            for area_id in value.get("searchAreaIds", []):
                if area_id not in self.state.get("searchAreas", {}):
                    raise MapDiscoveryError(f"location {ident!r} references missing search area {area_id!r}")
        areas = self.state.get("searchAreas")
        if not isinstance(areas, dict):
            raise MapDiscoveryError("searchAreas must be an object")
        for area_id, area in areas.items():
            _validate_search_area(area_id, area, self._indexes["regions"])

    def reveal_region(self, region_id: str):
        self._reveal("regions", region_id)

    def reveal_transition(self, transition_id: str):
        kind = "routes" if transition_id in self._indexes["routes"] else "boundaries"
        self._reveal(kind, transition_id)

    def visit_settlement(self, settlement_id: str):
        self.reveal_exact(settlement_id)

    def reveal_exact(self, location_id: str):
        record = self._location(location_id)
        self.reveal_region(record["regionId"])
        self._reveal(_plural(record["kind"]), location_id)
        previous = self.state["locations"].get(location_id, {})
        for area_id in previous.get("searchAreaIds", []):
            self.state["searchAreas"].pop(area_id, None)
        self.state["locations"][location_id] = {"precision": "exact", "regionId": record["regionId"], "searchAreaIds": []}

    def reveal_region_only(self, location_id: str):
        record = self._location(location_id)
        self.reveal_region(record["regionId"])
        current = self.state["locations"].get(location_id)
        if not current or current["precision"] != "exact":
            self.state["locations"][location_id] = {"precision": "region", "regionId": record["regionId"], "searchAreaIds": []}

    def reveal_approximate(self, location_id: str, areas: list[dict]):
        record = self._location(location_id)
        self.reveal_region(record["regionId"])
        if self.state["locations"].get(location_id, {}).get("precision") == "exact":
            return
        if not areas:
            raise MapDiscoveryError("approximate knowledge needs at least one search area")
        new_ids = []
        for area in areas:
            area = copy.deepcopy(area)
            _validate_search_area(area.get("id"), area, self._indexes["regions"])
            if area["regionId"] != record["regionId"]:
                raise MapDiscoveryError("search area and location must share a region")
            self.state["searchAreas"][area["id"]] = area
            new_ids.append(area["id"])
        old_ids = self.state["locations"].get(location_id, {}).get("searchAreaIds", [])
        for obsolete in set(old_ids) - set(new_ids):
            self.state["searchAreas"].pop(obsolete, None)
        self.state["locations"][location_id] = {"precision": "approximate", "regionId": record["regionId"], "searchAreaIds": new_ids}

    def hide_location(self, location_id: str):
        self._location(location_id)
        old = self.state["locations"].pop(location_id, None)
        if old:
            for area_id in old.get("searchAreaIds", []):
                self.state["searchAreas"].pop(area_id, None)

    def _reveal(self, kind, ident):
        if ident not in self._indexes[kind]:
            raise MapDiscoveryError(f"unknown {kind} ID {ident!r}")
        if ident not in self.state[kind]:
            self.state[kind].append(ident)
            self.state[kind].sort()

    def _location(self, ident):
        for kind in LOCATION_KINDS:
            record = self._indexes[_plural(kind)].get(ident)
            if record:
                return record
        raise MapDiscoveryError(f"unknown location ID {ident!r}")

    def export_state(self):
        self._validate()
        return copy.deepcopy(self.state)


class CampaignMap:
    """Modal presentation state built solely from authorized campaign knowledge."""

    def __init__(self, catalog: Mapping, knowledge: DiscoveryKnowledge, physical_region_id: str, command_region_id: str):
        self.catalog = copy.deepcopy(dict(catalog))
        self.knowledge = knowledge
        self.indexes = _catalog_indexes(self.catalog)
        for label, ident in (("physical", physical_region_id), ("command", command_region_id)):
            if ident not in self.indexes["regions"]:
                raise MapDiscoveryError(f"invalid {label} region {ident!r}")
        self.physical_region_id = physical_region_id
        self.command_region_id = command_region_id
        self.focus = MapFocus("world", None, None, "none")
        self.is_open = False

    def open_world(self):
        self.is_open = True
        self.focus = MapFocus("world", None, None, "none")
        return self.render()

    def open_region(self, region_id: str):
        self._require_known_region(region_id)
        self.is_open = True
        self.focus = MapFocus("regional", region_id, None, "region")
        return self.render()

    def close(self):
        self.is_open = False

    def set_command_region(self, region_id: str):
        if region_id not in self.indexes["regions"]:
            raise MapDiscoveryError(f"invalid command region {region_id!r}")
        self.command_region_id = region_id

    def focus_location(self, location_id: str):
        known = self.knowledge.state["locations"].get(location_id)
        if known is None:
            raise MapDiscoveryError("cannot focus an unknown location")
        areas = tuple(copy.deepcopy(self.knowledge.state["searchAreas"][x]) for x in known.get("searchAreaIds", []))
        self.is_open = True
        self.focus = MapFocus("regional", known["regionId"], location_id, known["precision"], areas)
        return self.render()

    def focus_search_area(self, area_id: str):
        area = self.knowledge.state["searchAreas"].get(area_id)
        if area is None:
            raise MapDiscoveryError("cannot focus an unknown search area")
        self.is_open = True
        self.focus = MapFocus("regional", area["regionId"], None, "approximate", (copy.deepcopy(area),))
        return self.render()

    def render(self):
        if not self.is_open:
            raise MapDiscoveryError("map is closed")
        known = self.knowledge.state
        region_ids = set(known["regions"]) | {self.physical_region_id, self.command_region_id}
        result = {
            "modal": True,
            "context": self.focus.context,
            "focusedRegionId": self.focus.region_id,
            "physicalRegionId": self.physical_region_id,
            "commandRegionId": self.command_region_id,
            "regions": [_public(self.indexes["regions"][x]) for x in sorted(region_ids)],
            "settlements": [], "landmarks": [], "pointsOfInterest": [], "routes": [], "boundaries": [],
            "breadcrumbRegionIds": self._known_breadcrumb(self.focus.region_id),
            "focus": {"targetId": self.focus.target_id, "precision": self.focus.precision, "areas": copy.deepcopy(list(self.focus.areas))},
        }
        for kind in ("settlements", "landmarks", "pointsOfInterest"):
            for ident in sorted(known[kind]):
                record = self.indexes[kind][ident]
                if self.focus.context == "world" or record["regionId"] == self.focus.region_id:
                    result[kind].append(_public(record))
        for kind in ("routes", "boundaries"):
            for ident in sorted(known[kind]):
                record = self.indexes[kind][ident]
                if self.focus.context == "world" or self.focus.region_id in _transition_regions(record):
                    result[kind].append(_public(record))
        return result

    def _require_known_region(self, region_id):
        if region_id not in self.knowledge.state["regions"] and region_id not in {self.physical_region_id, self.command_region_id}:
            raise MapDiscoveryError("cannot open an unknown region")

    def _known_breadcrumb(self, destination):
        if destination is None:
            return []
        if destination == self.physical_region_id:
            return [destination]
        graph = {}
        for kind in ("routes", "boundaries"):
            for ident in self.knowledge.state[kind]:
                record = self.indexes[kind][ident]
                source, target = record["from"]["regionId"], record["to"]["regionId"]
                graph.setdefault(source, set()).add(target)
                if not record.get("directed", False):
                    graph.setdefault(target, set()).add(source)
        queue = [(self.physical_region_id, [self.physical_region_id])]
        visited = {self.physical_region_id}
        while queue:
            current, path = queue.pop(0)
            for neighbor in sorted(graph.get(current, ())):
                if neighbor == destination:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return []


def build_catalog(world: Mapping, presentation: Mapping) -> dict:
    """Combine validated world IDs with scenario-owned map geometry and labels."""
    geography = world.get("regionalGeography", {})
    regions = {x["id"]: copy.deepcopy(x) for x in geography.get("regions", [])}
    layouts = {x["regionId"]: x for x in presentation.get("regionLayouts", [])}
    if set(layouts) != set(regions):
        raise MapDiscoveryError("region layouts must cover every world region exactly once")
    for ident, region in regions.items():
        region["mapPosition"] = copy.deepcopy(layouts[ident]["mapPosition"])
    instance_regions = presentation.get("regionalInstanceRegions", {})
    settlements = []
    for source in world.get("settlements", []):
        if "localPosition" not in source:
            continue
        instance = source.get("regionalInstanceId")
        region_id = instance_regions.get(instance)
        if not region_id:
            raise MapDiscoveryError(f"settlement {source.get('id')!r} has no regional map assignment")
        settlements.append({"id": source["id"], "kind": "settlement", "name": source["name"], "regionId": region_id, "position": copy.deepcopy(source["localPosition"])})
    catalog = {
        "regions": list(regions.values()), "settlements": settlements,
        "landmarks": copy.deepcopy(presentation.get("landmarks", [])),
        "pointsOfInterest": copy.deepcopy(presentation.get("pointsOfInterest", [])),
        "routes": copy.deepcopy(geography.get("routes", [])),
        "boundaries": copy.deepcopy(geography.get("boundaries", [])),
    }
    _catalog_indexes(catalog)
    return catalog


def _catalog_indexes(catalog):
    indexes = {}
    all_ids = set()
    for kind in ("regions", "settlements", "landmarks", "pointsOfInterest", "routes", "boundaries"):
        records = catalog.get(kind, [])
        if not isinstance(records, list):
            raise MapDiscoveryError(f"catalog {kind} must be an array")
        index = {}
        for record in records:
            ident = record.get("id") if isinstance(record, dict) else None
            if not isinstance(ident, str) or not ident or ident in all_ids:
                raise MapDiscoveryError(f"catalog has invalid or duplicate ID {ident!r}")
            index[ident] = record
            all_ids.add(ident)
        indexes[kind] = index
    regions = indexes["regions"]
    for kind in ("settlements", "landmarks", "pointsOfInterest"):
        expected = kind[:-1] if kind != "pointsOfInterest" else "pointOfInterest"
        for record in indexes[kind].values():
            if record.get("kind") != expected or record.get("regionId") not in regions:
                raise MapDiscoveryError(f"invalid {kind} location {record.get('id')!r}")
            if not isinstance(record.get("name"), str) or not record["name"].strip():
                raise MapDiscoveryError(f"location {record.get('id')!r} needs an English label")
            _point(record.get("position"), f"location {record.get('id')!r}")
    return indexes


def _validate_search_area(area_id, area, regions):
    if not isinstance(area_id, str) or not area_id or not isinstance(area, dict):
        raise MapDiscoveryError("search area needs a stable ID")
    if area.get("regionId") not in regions:
        raise MapDiscoveryError(f"search area {area_id!r} has invalid region")
    shape = area.get("shape")
    if shape == "circle":
        _point(area.get("center"), f"search area {area_id!r}")
        radius = area.get("radius")
        if isinstance(radius, bool) or not isinstance(radius, (int, float)) or radius <= 0:
            raise MapDiscoveryError(f"search area {area_id!r} has invalid radius")
    elif shape == "polygon":
        points = area.get("points")
        if not isinstance(points, list) or len(points) < 3:
            raise MapDiscoveryError(f"search area {area_id!r} polygon needs three points")
        for point in points:
            _point(point, f"search area {area_id!r}")
    else:
        raise MapDiscoveryError(f"search area {area_id!r} has invalid shape")


def _point(value, context):
    if not isinstance(value, dict) or any(isinstance(value.get(axis), bool) or not isinstance(value.get(axis), (int, float)) for axis in ("x", "y")):
        raise MapDiscoveryError(f"{context} has invalid coordinates")


def _plural(kind):
    return {"settlement": "settlements", "landmark": "landmarks", "pointOfInterest": "pointsOfInterest"}[kind]


def _transition_regions(record):
    return {record.get("from", {}).get("regionId"), record.get("to", {}).get("regionId")}


def _public(record):
    return copy.deepcopy(record)

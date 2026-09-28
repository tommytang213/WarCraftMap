"""Scenario-neutral regional-instance topology and transactional travel runtime."""
from __future__ import annotations
import copy
from dataclasses import dataclass
from typing import Callable, Protocol

MOVEMENT_CLASSES = frozenset({"land", "naval", "amphibious", "flying"})

class RegionalNavigationError(ValueError): pass
class InvalidTransition(RegionalNavigationError): pass
class RuntimeReconstructionError(RegionalNavigationError): pass

class RuntimeAdapter(Protocol):
    """Only boundary allowed to create, retire, or relocate Warcraft objects."""
    def snapshot(self): ...
    def restore(self, snapshot) -> None: ...
    def retire_region(self, region_id: str) -> None: ...
    def reconstruct_region(self, region_id: str, entities: dict) -> None: ...
    def relocate_entity(self, entity_id: str, region_id: str, area_id: str, x: float, y: float) -> None: ...

class PersistenceAdapter(Protocol):
    def checkpoint(self, regional_state: dict) -> None: ...

@dataclass(frozen=True)
class TravelResult:
    entity_id: str
    region_id: str
    anchor_id: str
    campaign_time: int

class RegionalWorld:
    """Authoritative regional state; runtime handles are deliberately excluded."""
    def __init__(self, geography: dict, state: dict, runtime: RuntimeAdapter, persistence: PersistenceAdapter | None = None, encounter_hook: Callable[[str, dict], None] | None = None):
        self.geography = copy.deepcopy(geography)
        self.state = copy.deepcopy(state)
        self.runtime = runtime
        self.persistence = persistence
        self.encounter_hook = encounter_hook or (lambda _hook, _crossing: None)
        self.regions = _index(geography, "regions")
        self.areas = _index(geography, "areas")
        self.anchors = _index(geography, "anchors")
        self.boundaries = _index(geography, "boundaries")
        self.routes = _index(geography, "routes")
        self._validate_state()

    def _validate_state(self):
        if self.state.get("activeRegionId") not in self.regions:
            raise RegionalNavigationError("active region is missing")
        entities = self.state.get("entities")
        if not isinstance(entities, dict):
            raise RegionalNavigationError("entities must be an object")
        for entity_id, entity in entities.items():
            if entity.get("regionId") not in self.regions:
                raise RegionalNavigationError(f"entity {entity_id}: missing region")
            if entity.get("movementClass") not in MOVEMENT_CLASSES:
                raise RegionalNavigationError(f"entity {entity_id}: invalid movement class")
            if entity.get("transitionState", "idle") not in {"idle", "crossing"}:
                raise RegionalNavigationError(f"entity {entity_id}: invalid transition state")
        if not isinstance(self.state.get("pendingCrossings", {}), dict):
            raise RegionalNavigationError("pendingCrossings must be an object")

    def _edge(self, edge_id, entity, collection):
        edge = collection.get(edge_id)
        if edge is None:
            raise InvalidTransition(f"missing transition {edge_id!r}")
        if entity["movementClass"] not in edge["movementClasses"]:
            raise InvalidTransition("entity movement class is incompatible")
        source, destination = edge["from"], edge["to"]
        if entity["regionId"] == source["regionId"]:
            return edge, source, destination
        if not edge["directed"] and entity["regionId"] == destination["regionId"]:
            return edge, destination, source
        raise InvalidTransition("transition is disconnected from entity region")

    def _atomic(self, operation):
        previous_state, runtime_snapshot = copy.deepcopy(self.state), self.runtime.snapshot()
        try:
            result = operation()
            if self.persistence:
                self.persistence.checkpoint(copy.deepcopy(self.state))
            return result
        except Exception:
            self.state = previous_state
            self.runtime.restore(runtime_snapshot)
            raise

    def transition(self, entity_id: str, boundary_id: str) -> TravelResult:
        def perform():
            entity = self._eligible_entity(entity_id)
            _edge, _source, destination = self._edge(boundary_id, entity, self.boundaries)
            anchor = self._destination_anchor(destination, entity["movementClass"])
            old_region = self.state["activeRegionId"]
            entity.update({"regionId": destination["regionId"], "areaId": anchor["areaId"], "position": copy.deepcopy(anchor["position"]), "transitionState": "idle"})
            self._activate(old_region, destination["regionId"])
            self.runtime.relocate_entity(entity_id, destination["regionId"], anchor["areaId"], anchor["position"]["x"], anchor["position"]["y"])
            return TravelResult(entity_id, destination["regionId"], anchor["id"], self.state["campaignTime"])
        return self._atomic(perform)

    def begin_crossing(self, entity_id: str, route_id: str):
        def perform():
            entity = self._eligible_entity(entity_id)
            route, _source, destination = self._edge(route_id, entity, self.routes)
            crossing = {"id": f"crossing_{entity_id}", "entityId": entity_id, "routeId": route_id, "destinationRegionId": destination["regionId"], "elapsedDays": 0, "durationDays": route["durationDays"], "nextHookIndex": 0}
            self.state["pendingCrossings"][entity_id] = crossing
            entity["transitionState"] = "crossing"
            self.runtime.retire_region(entity["regionId"])
            return copy.deepcopy(crossing)
        return self._atomic(perform)

    def advance(self, days: int):
        if isinstance(days, bool) or not isinstance(days, int) or days < 0:
            raise RegionalNavigationError("days must be a non-negative integer")
        for _ in range(days):
            self._atomic(self._advance_one_day)

    def _advance_one_day(self):
        self.state["campaignTime"] += 1
        for entity_id in sorted(tuple(self.state["pendingCrossings"])):
            crossing = self.state["pendingCrossings"][entity_id]
            route = self.routes[crossing["routeId"]]
            crossing["elapsedDays"] += 1
            hooks = route["encounterHookIds"]
            while crossing["nextHookIndex"] < len(hooks):
                index = crossing["nextHookIndex"]
                trigger_day = ((index + 1) * route["durationDays"] + len(hooks)) // (len(hooks) + 1)
                if crossing["elapsedDays"] < trigger_day: break
                self.encounter_hook(hooks[index], copy.deepcopy(crossing))
                crossing["nextHookIndex"] += 1
            if crossing["elapsedDays"] >= crossing["durationDays"]:

                self._complete_crossing(entity_id, crossing, route)
    def simulate_inactive(self, days: int, step: Callable[[dict, str, int], None]):
        """Advance authoritative inactive-region state without runtime objects."""
        if isinstance(days, bool) or not isinstance(days, int) or days < 0:
            raise RegionalNavigationError("days must be a non-negative integer")
        def perform():
            for region_id in sorted(self.regions):
                if region_id != self.state["activeRegionId"]:
                    step(self.state, region_id, days)
        self._atomic(perform)

    def cancel_crossing(self, entity_id: str):
        def perform():
            crossing = self.state["pendingCrossings"].pop(entity_id, None)
            if crossing is None: raise InvalidTransition("entity has no pending crossing")
            entity = self.state["entities"][entity_id]
            entity["transitionState"] = "idle"
            self.runtime.reconstruct_region(entity["regionId"], self._entities_in(entity["regionId"]))
        self._atomic(perform)

    def _complete_crossing(self, entity_id, crossing, route):
        entity = self.state["entities"][entity_id]
        _, _, destination = self._edge(crossing["routeId"], entity, self.routes)
        anchor = self._destination_anchor(destination, entity["movementClass"])
        entity.update({"regionId": destination["regionId"], "areaId": anchor["areaId"], "position": copy.deepcopy(anchor["position"]), "transitionState": "idle"})
        del self.state["pendingCrossings"][entity_id]
        self._activate(self.state["activeRegionId"], destination["regionId"])
        self.runtime.relocate_entity(entity_id, destination["regionId"], anchor["areaId"], anchor["position"]["x"], anchor["position"]["y"])

    def _eligible_entity(self, entity_id):
        entity = self.state["entities"].get(entity_id)
        if entity is None: raise InvalidTransition("missing or stale entity")
        if not entity.get("physicallyActive", False): raise InvalidTransition("entity is not physically active")
        if entity.get("transitionState", "idle") != "idle": raise InvalidTransition("entity already has a transition")
        return entity

    def _destination_anchor(self, endpoint, movement_class):
        anchor = self.anchors.get(endpoint["anchorId"])
        if not anchor or anchor["regionId"] != endpoint["regionId"]:
            raise InvalidTransition("destination anchor is missing")
        if movement_class not in anchor["movementClasses"]:
            raise InvalidTransition("destination anchor is incompatible")
        return anchor

    def _entities_in(self, region_id):
        return {key: copy.deepcopy(value) for key, value in self.state["entities"].items() if value["regionId"] == region_id and value.get("transitionState", "idle") == "idle"}

    def _activate(self, old_region, new_region):
        if old_region != new_region:
            self.runtime.retire_region(old_region)
            self.runtime.reconstruct_region(new_region, self._entities_in(new_region))
            self.state["activeRegionId"] = new_region

    def export_state(self):
        return copy.deepcopy(self.state)


def _index(geography, key):
    return {record["id"]: record for record in geography.get(key, [])}

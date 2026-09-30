"""Scenario-neutral regional-instance topology and transactional travel runtime."""
from __future__ import annotations
import copy
import time
from dataclasses import dataclass
from collections.abc import Mapping
from typing import Callable, Protocol

MOVEMENT_CLASSES = frozenset({"land", "naval", "amphibious", "flying"})
REGIONAL_STATE_VERSION = 1
REGIONAL_WORLD_STATE_KEY = "regionalNavigationState"

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
    def representation_ids(self) -> set[str]: ...

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
    def __init__(self, geography: dict, state: dict, runtime: RuntimeAdapter, persistence: PersistenceAdapter | None = None, encounter_hook: Callable[[str, dict], None] | None = None, *, max_active_objects: int = 500, max_transition_milliseconds: float = 1000):
        self.geography = copy.deepcopy(geography)
        self.state = copy.deepcopy(state)
        self.runtime = runtime
        self.persistence = persistence
        self.encounter_hook = encounter_hook or (lambda _hook, _crossing: None)
        if isinstance(max_active_objects, bool) or not isinstance(max_active_objects, int) or max_active_objects < 1:
            raise RegionalNavigationError("max_active_objects must be positive")
        if isinstance(max_transition_milliseconds, bool) or not isinstance(max_transition_milliseconds, (int, float)) or max_transition_milliseconds <= 0:
            raise RegionalNavigationError("max_transition_milliseconds must be positive")
        self.max_active_objects = max_active_objects
        self.max_transition_milliseconds = max_transition_milliseconds
        self.regions = _index(geography, "regions")
        self.areas = _index(geography, "areas")
        self.anchors = _index(geography, "anchors")
        self.boundaries = _index(geography, "boundaries")
        self.routes = _index(geography, "routes")
        self._transition_in_progress = False
        self._normalize_state()
        self._validate_state()
        self.representation_indexes = self._build_representation_indexes()

    def _normalize_state(self):
        """Upgrade the pre-runtime prototype without changing authoritative entities."""
        self.state.setdefault("schemaVersion", REGIONAL_STATE_VERSION)
        active = self.state.get("activePhysicalRegionId", self.state.get("activeRegionId"))
        self.state["activePhysicalRegionId"] = active
        self.state["activeLocalRegionId"] = self.state.get("activeLocalRegionId", active)
        self.state.setdefault("runtimeRegionActive", True)
        # Keep the former spelling as a compatibility projection, never as authority.
        self.state["activeRegionId"] = active
        self.state.setdefault("pendingCrossings", {})
        self.state.setdefault("transitionSequence", 0)
        # Runtime indexes existed briefly in prototype saves. They contain no
        # authority and must not survive migration or serialization.
        self.state.pop("representationIndexes", None)

    def _validate_state(self):
        if self.state.get("schemaVersion") != REGIONAL_STATE_VERSION:
            raise RegionalNavigationError("regional state schemaVersion must be 1")
        if self.state.get("activePhysicalRegionId") not in self.regions:
            raise RegionalNavigationError("active region is missing")
        if self.state.get("activeLocalRegionId") not in self.regions:
            raise RegionalNavigationError("active local region is missing")
        if not isinstance(self.state.get("runtimeRegionActive"), bool):
            raise RegionalNavigationError("runtimeRegionActive must be boolean")
        entities = self.state.get("entities")
        if not isinstance(entities, dict):
            raise RegionalNavigationError("entities must be an object")
        for entity_id, entity in entities.items():
            if not isinstance(entity_id, str) or not entity_id or not isinstance(entity, dict):
                raise RegionalNavigationError("entity records require stable string IDs")
            if entity.get("regionId") not in self.regions:
                raise RegionalNavigationError(f"entity {entity_id}: missing region")
            if entity.get("movementClass") not in MOVEMENT_CLASSES:
                raise RegionalNavigationError(f"entity {entity_id}: invalid movement class")
            if entity.get("transitionState", "idle") not in {"idle", "crossing"}:
                raise RegionalNavigationError(f"entity {entity_id}: invalid transition state")
            if not isinstance(entity.get("physicallyActive", False), bool):
                raise RegionalNavigationError(f"entity {entity_id}: physicallyActive must be boolean")
        if not isinstance(self.state.get("pendingCrossings", {}), dict):
            raise RegionalNavigationError("pendingCrossings must be an object")
        for entity_id, crossing in self.state["pendingCrossings"].items():
            if entity_id not in entities or crossing.get("entityId") != entity_id or crossing.get("routeId") not in self.routes:
                raise RegionalNavigationError(f"pending crossing {entity_id}: stale reference")
            if entities[entity_id].get("transitionState") != "crossing":
                raise RegionalNavigationError(f"pending crossing {entity_id}: entity is not crossing")
            route = self.routes[crossing["routeId"]]
            try:
                _edge, _source, destination = self._edge(crossing["routeId"], entities[entity_id], self.routes)
            except InvalidTransition as error:
                raise RegionalNavigationError(f"pending crossing {entity_id}: {error}") from error
            elapsed, duration, hook_index = crossing.get("elapsedDays"), crossing.get("durationDays"), crossing.get("nextHookIndex")
            if (crossing.get("destinationRegionId") != destination["regionId"] or duration != route["durationDays"] or
                    isinstance(elapsed, bool) or not isinstance(elapsed, int) or elapsed < 0 or elapsed >= duration or
                    isinstance(hook_index, bool) or not isinstance(hook_index, int) or not 0 <= hook_index <= len(route["encounterHookIds"])):
                raise RegionalNavigationError(f"pending crossing {entity_id}: invalid progress")
        crossing_entities = {entity_id for entity_id, entity in entities.items() if entity.get("transitionState") == "crossing"}
        if crossing_entities != set(self.state["pendingCrossings"]):
            raise RegionalNavigationError("crossing entities and pending crossings disagree")
        if len(crossing_entities) > 1:
            raise RegionalNavigationError("only one physical regional crossing may be pending")
        if bool(crossing_entities) == self.state["runtimeRegionActive"]:
            raise RegionalNavigationError("pending crossing runtime activation is inconsistent")
        if self.state["activePhysicalRegionId"] != self.state["activeLocalRegionId"]:
            raise RegionalNavigationError("physical and local regions may diverge only in remote-management runtime")

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
        if self._transition_in_progress:
            raise InvalidTransition("another regional transition is in progress")
        previous_state = copy.deepcopy(self.state)
        previous_indexes = copy.deepcopy(self.representation_indexes)
        runtime_snapshot = self.runtime.snapshot()
        self._transition_in_progress = True
        started = time.perf_counter()
        try:
            result = operation()
            self.representation_indexes = self._build_representation_indexes()
            elapsed_ms = (time.perf_counter() - started) * 1000
            if elapsed_ms > self.max_transition_milliseconds:
                raise RuntimeReconstructionError(f"regional transition exceeded {self.max_transition_milliseconds:g} ms budget")
            if self.persistence:
                self.persistence.checkpoint(copy.deepcopy(self.state))
            return result
        except Exception:
            self.state = previous_state
            self.representation_indexes = previous_indexes
            self.runtime.restore(runtime_snapshot)
            raise
        finally:
            self._transition_in_progress = False

    def transition(self, entity_id: str, boundary_id: str) -> TravelResult:
        def perform():
            entity = self._eligible_entity(entity_id)
            _edge, _source, destination = self._edge(boundary_id, entity, self.boundaries)
            anchor = self._destination_anchor(destination, entity["movementClass"])
            old_region = self.state["activeLocalRegionId"]
            entity.update({"regionId": destination["regionId"], "areaId": anchor["areaId"], "position": copy.deepcopy(anchor["position"]), "transitionState": "idle"})
            self._activate(old_region, destination["regionId"])
            self.runtime.relocate_entity(entity_id, destination["regionId"], anchor["areaId"], anchor["position"]["x"], anchor["position"]["y"])
            self.state["transitionSequence"] += 1
            return TravelResult(entity_id, destination["regionId"], anchor["id"], self.state["campaignTime"])
        return self._atomic(perform)

    def begin_crossing(self, entity_id: str, route_id: str):
        def perform():
            entity = self._eligible_entity(entity_id)
            if self.state["pendingCrossings"]:
                raise InvalidTransition("another regional crossing is pending")
            route, _source, destination = self._edge(route_id, entity, self.routes)
            self.state["transitionSequence"] += 1
            crossing = {"id": f"crossing_{self.state['transitionSequence']}_{entity_id}", "entityId": entity_id, "routeId": route_id, "destinationRegionId": destination["regionId"], "elapsedDays": 0, "durationDays": route["durationDays"], "nextHookIndex": 0}
            self.state["pendingCrossings"][entity_id] = crossing
            entity["transitionState"] = "crossing"
            self.runtime.retire_region(entity["regionId"])
            self.state["activeLocalRegionId"] = entity["regionId"]
            self.state["runtimeRegionActive"] = False
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
                if region_id != self.state["activeLocalRegionId"]:
                    step(self.state, region_id, days)
        self._atomic(perform)

    def cancel_crossing(self, entity_id: str):
        def perform():
            crossing = self.state["pendingCrossings"].pop(entity_id, None)
            if crossing is None: raise InvalidTransition("entity has no pending crossing")
            entity = self.state["entities"][entity_id]
            entity["transitionState"] = "idle"
            self.runtime.reconstruct_region(entity["regionId"], self._entities_in(entity["regionId"]))
            self.state["activePhysicalRegionId"] = entity["regionId"]
            self.state["activeLocalRegionId"] = entity["regionId"]
            self.state["activeRegionId"] = entity["regionId"]
            self.state["runtimeRegionActive"] = True
        self._atomic(perform)

    def _complete_crossing(self, entity_id, crossing, route):
        entity = self.state["entities"][entity_id]
        _, _, destination = self._edge(crossing["routeId"], entity, self.routes)
        anchor = self._destination_anchor(destination, entity["movementClass"])
        entity.update({"regionId": destination["regionId"], "areaId": anchor["areaId"], "position": copy.deepcopy(anchor["position"]), "transitionState": "idle"})
        del self.state["pendingCrossings"][entity_id]
        self._activate(self.state["activeLocalRegionId"], destination["regionId"])
        self.runtime.relocate_entity(entity_id, destination["regionId"], anchor["areaId"], anchor["position"]["x"], anchor["position"]["y"])
        self.state["transitionSequence"] += 1

    def _eligible_entity(self, entity_id):
        entity = self.state["entities"].get(entity_id)
        if entity is None: raise InvalidTransition("missing or stale entity")
        if not entity.get("physicallyActive", False): raise InvalidTransition("entity is not physically active")
        if entity.get("transitionState", "idle") != "idle": raise InvalidTransition("entity already has a transition")
        if not self.state["runtimeRegionActive"] or entity["regionId"] != self.state["activePhysicalRegionId"] or entity["regionId"] != self.state["activeLocalRegionId"]:
            raise InvalidTransition("entity is not in the active physical region")
        return entity

    def _destination_anchor(self, endpoint, movement_class):
        anchor = self.anchors.get(endpoint["anchorId"])
        if not anchor or anchor["regionId"] != endpoint["regionId"]:
            raise InvalidTransition("destination anchor is missing")
        if movement_class not in anchor["movementClasses"]:
            raise InvalidTransition("destination anchor is incompatible")
        return anchor

    def _entities_in(self, region_id):
        result = {key: copy.deepcopy(value) for key, value in self.state["entities"].items() if value["regionId"] == region_id and value.get("physicallyActive", False) and value.get("transitionState", "idle") == "idle"}
        if len(result) > self.max_active_objects:
            raise RuntimeReconstructionError(f"region {region_id} exceeds {self.max_active_objects} active object budget")
        return result

    def _activate(self, old_region, new_region):
        if old_region != new_region:
            self.runtime.retire_region(old_region)
            self.runtime.reconstruct_region(new_region, self._entities_in(new_region))
            self.state["activePhysicalRegionId"] = new_region
            self.state["activeLocalRegionId"] = new_region
            self.state["activeRegionId"] = new_region
            self.state["runtimeRegionActive"] = True

    def activate(self, region_id: str):
        """Reconstruct a local region from authority; useful at bootstrap/load."""
        if region_id not in self.regions:
            raise InvalidTransition("missing activation region")
        def perform():
            old = self.state["activeLocalRegionId"]
            if old != region_id:
                self.runtime.retire_region(old)
            self.runtime.reconstruct_region(region_id, self._entities_in(region_id))
            self.state["activePhysicalRegionId"] = region_id
            self.state["activeLocalRegionId"] = region_id
            self.state["activeRegionId"] = region_id
            self.state["runtimeRegionActive"] = True
        return self._atomic(perform)

    def recover_representations(self):
        """Deterministically replace missing/stale handles from authoritative state."""
        def perform():
            region_id = self.state["activeLocalRegionId"]
            expected = set(self._entities_in(region_id)) if self.state["runtimeRegionActive"] else set()
            observed = set(self.runtime.representation_ids())
            if observed != expected:
                self.runtime.retire_region(region_id)
                if self.state["runtimeRegionActive"]:
                    self.runtime.reconstruct_region(region_id, self._entities_in(region_id))
            return sorted(expected - observed)
        return self._atomic(perform)

    def _build_representation_indexes(self):
        active = self.state.get("activeLocalRegionId") if self.state.get("runtimeRegionActive", True) else None
        by_entity = {}
        by_region = {region_id: [] for region_id in self.regions}
        for entity_id, entity in sorted(self.state.get("entities", {}).items()):
            if entity.get("regionId") == active and entity.get("physicallyActive", False) and entity.get("transitionState", "idle") == "idle":
                by_entity[entity_id] = {"regionId": active, "stableId": entity_id}
                by_region[active].append(entity_id)
        return {"byEntityId": by_entity, "byRegionId": by_region}

    def export_state(self):
        return copy.deepcopy(self.state)


class RegionalSaveAdapter:
    """Campaign-save integration; Warcraft handles are intentionally never saved."""
    def __init__(self, world: RegionalWorld): self.world = world
    def capture_world(self, candidate: Mapping) -> dict:
        result = copy.deepcopy(dict(candidate)); result[REGIONAL_WORLD_STATE_KEY] = self.world.export_state(); return result
    def validate_world(self, candidate: Mapping) -> None:
        if not isinstance(candidate, Mapping) or REGIONAL_WORLD_STATE_KEY not in candidate: raise RegionalNavigationError("regional navigation state is missing")
        RegionalWorld(self.world.geography, candidate[REGIONAL_WORLD_STATE_KEY], _ValidationRuntime())
    def reconstruct(self, candidate: Mapping) -> dict:
        self.validate_world(candidate); return copy.deepcopy(candidate[REGIONAL_WORLD_STATE_KEY])
    def activate(self, _candidate: Mapping, reconstructed: dict) -> None:
        replacement = RegionalWorld(self.world.geography, reconstructed, self.world.runtime, None, self.world.encounter_hook,
                                    max_active_objects=self.world.max_active_objects,
                                    max_transition_milliseconds=self.world.max_transition_milliseconds)
        if replacement.state["runtimeRegionActive"]:
            replacement.activate(replacement.state["activeLocalRegionId"])
        else:
            replacement._atomic(lambda: replacement.runtime.retire_region(replacement.state["activeLocalRegionId"]))
        self.world.state = replacement.state
        self.world.representation_indexes = replacement.representation_indexes
    def migrate_legacy_world(self, candidate: Mapping) -> dict:
        result = copy.deepcopy(dict(candidate)); result.setdefault(REGIONAL_WORLD_STATE_KEY, self.world.export_state()); self.validate_world(result); return result


class _ValidationRuntime:
    def snapshot(self): return None
    def restore(self, _snapshot): pass
    def retire_region(self, _region_id): pass
    def reconstruct_region(self, _region_id, _entities): pass
    def relocate_entity(self, *_args): pass
    def representation_ids(self): return set()


def _index(geography, key):
    return {record["id"]: record for record in geography.get(key, [])}

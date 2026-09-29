"""Deterministic strategic armies/fleets with transient runtime objects.

Scenario data owns templates and balance values.  Campaign state contains only
stable IDs and scalar values; Warcraft handles live exclusively in the adapter.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol


MILITARY_STATE_SCHEMA_VERSION = 1
MILITARY_WORLD_STATE_KEY = "militaryState"
_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_KINDS = {"formation": "land", "ship": "naval"}


class MilitaryError(ValueError):
    """Rejected definition, state, or atomic military operation."""


class MilitaryRuntimeAdapter(Protocol):
    """The only boundary allowed to create or retire Warcraft objects."""

    def create(self, unit_id: str, specification: Mapping[str, Any]) -> Any: ...
    def retire(self, representation: Any) -> None: ...
    def exists(self, representation: Any) -> bool: ...


class RecordingMilitaryAdapter:
    """Deterministic headless Warcraft compatibility adapter for validation."""

    def __init__(self) -> None:
        self.operations: list[tuple[Any, ...]] = []
        self._serial = 0
        self._live: set[str] = set()

    def create(self, unit_id: str, specification: Mapping[str, Any]) -> str:
        self._serial += 1
        handle = f"military_object_{self._serial}"
        self._live.add(handle)
        self.operations.append(("create", unit_id, copy.deepcopy(dict(specification)), handle))
        return handle

    def retire(self, representation: Any) -> None:
        self._live.discard(representation)
        self.operations.append(("retire", representation))

    def exists(self, representation: Any) -> bool:
        return representation in self._live

    def destroy_unexpectedly(self, representation: Any) -> None:
        self._live.discard(representation)


@dataclass(frozen=True)
class UnitView:
    id: str
    name: str
    kind: str
    legal_owner_polity_id: str
    controller_polity_id: str
    represented_strength: int
    strength_unit_id: str
    morale: int
    supply: int
    readiness: int
    location_id: str
    commander_officer_id: str | None
    officer_ids: tuple[str, ...]
    runtime_template_id: str
    locally_relevant: bool
    represented_object_count: int


def _stable_id(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise MilitaryError(f"{context}: invalid stable ID {value!r}")
    return value


def _index(world: Mapping[str, Any], key: str) -> dict[str, Mapping[str, Any]]:
    values = world.get(key)
    if not isinstance(values, list):
        raise MilitaryError(f"{key}: must be an array")
    result = {}
    for value in values:
        if not isinstance(value, Mapping):
            raise MilitaryError(f"{key}: every entry must be an object")
        ident = _stable_id(value.get("id"), f"{key}.id")
        if ident in result:
            raise MilitaryError(f"{key}: duplicate ID {ident!r}")
        result[ident] = value
    return result


def _score(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
        raise MilitaryError(f"{context}: must be an integer between 0 and 100")
    return value


class MilitaryRuntime:
    """Authoritative strategic state plus reconstructible local representations."""

    def __init__(
        self,
        world_definitions: Mapping[str, Any],
        adapter: MilitaryRuntimeAdapter,
        conflict_is_active: Callable[[str, str], bool],
        tradition_runtime: Any | None = None,
    ) -> None:
        if not isinstance(world_definitions, Mapping):
            raise MilitaryError("world definitions must be an object")
        self._world = copy.deepcopy(dict(world_definitions))
        self._adapter = adapter
        self._conflict_is_active = conflict_is_active
        self._traditions = tradition_runtime
        self._polities = _index(self._world, "polities")
        self._officers = _index(self._world, "officers")
        self._zones = _index(self._world, "navigationZones")
        self._templates = _index(self._world, "militaryRuntimeTemplates")
        self._unit_definitions = _index(self._world, "strategicUnits")
        self._army_definitions = _index(self._world, "armies")
        self._fleet_definitions = _index(self._world, "fleets")
        self._state = self._initial_state()
        self._representations: dict[str, list[Any]] = {}

    def _initial_state(self) -> dict[str, Any]:
        units = []
        for ident in sorted(self._unit_definitions):
            source = self._unit_definitions[ident]
            runtime = source.get("runtimeInstantiation")
            if not isinstance(runtime, Mapping):
                raise MilitaryError(f"strategic unit {ident}: missing runtimeInstantiation")
            units.append({
                "id": ident, "name": source.get("name"), "kind": source.get("kind"),
                "legalOwnerPolityId": source.get("legalOwnerPolityId"),
                "controllerPolityId": source.get("controllerPolityId"),
                "representedStrength": source.get("representedStrength"),
                "strengthUnitId": source.get("strengthUnitId"),
                "operationalState": copy.deepcopy(source.get("operationalState")),
                "currentLocationId": source.get("currentLocationId"),
                "runtimeTemplateId": runtime.get("runtimeTemplateId"),
                "locallyRelevant": runtime.get("state") == "active",
                "commanderOfficerId": source.get("commanderOfficerId"),
                "officerIds": copy.deepcopy(source.get("officerIds")),
            })
        groups = []
        for group_kind, definitions, field in (
            ("army", self._army_definitions, "formationUnitIds"),
            ("fleet", self._fleet_definitions, "shipUnitIds"),
        ):
            for ident in sorted(definitions):
                source = definitions[ident]
                groups.append({
                    "id": ident, "kind": group_kind, "name": source.get("name"),
                    "legalOwnerPolityId": source.get("legalOwnerPolityId"),
                    "controllerPolityId": source.get("controllerPolityId"),
                    "memberUnitIds": copy.deepcopy(source.get(field)),
                    "operationalState": copy.deepcopy(source.get("operationalState")),
                    "commanderOfficerId": source.get("commanderOfficerId"),
                    "officerIds": copy.deepcopy(source.get("officerIds")),
                })
        state = {"schemaVersion": 1, "units": units, "groups": groups}
        return self.validate_snapshot(state)

    def _validate_officers(self, record: Mapping[str, Any], context: str) -> tuple[str, ...]:
        values = record.get("officerIds")
        if not isinstance(values, list):
            raise MilitaryError(f"{context}.officerIds: must be an array")
        result = []
        for value in values:
            ident = _stable_id(value, f"{context}.officerIds")
            if ident in result:
                raise MilitaryError(f"{context}: duplicate officer {ident!r}")
            if ident not in self._officers:
                raise MilitaryError(f"{context}: missing officer {ident!r}")
            result.append(ident)
        commander = record.get("commanderOfficerId")
        if commander is not None:
            commander = _stable_id(commander, f"{context}.commanderOfficerId")
            if commander not in result:
                raise MilitaryError(f"{context}: commander must be assigned to the entity")
        return tuple(result)

    def _validate_operational(self, value: Any, context: str) -> dict[str, int]:
        if not isinstance(value, Mapping) or set(value) != {"morale", "supply", "readiness"}:
            raise MilitaryError(f"{context}.operationalState: invalid fields")
        return {key: _score(value.get(key), f"{context}.{key}") for key in ("morale", "supply", "readiness")}

    def _validate_owner(self, record: Mapping[str, Any], context: str) -> tuple[str, str]:
        owner = _stable_id(record.get("legalOwnerPolityId"), f"{context}.legalOwnerPolityId")
        controller = _stable_id(record.get("controllerPolityId"), f"{context}.controllerPolityId")
        if owner not in self._polities or controller not in self._polities:
            raise MilitaryError(f"{context}: missing polity reference")
        return owner, controller

    def validate_snapshot(self, candidate: Any) -> dict[str, Any]:
        if not isinstance(candidate, Mapping) or set(candidate) != {"schemaVersion", "units", "groups"} or candidate.get("schemaVersion") != 1:
            raise MilitaryError("military state schemaVersion must be 1 and contain only units and groups")
        raw_units, raw_groups = candidate.get("units"), candidate.get("groups")
        if not isinstance(raw_units, list) or not isinstance(raw_groups, list):
            raise MilitaryError("military units and groups must be arrays")
        units: dict[str, dict[str, Any]] = {}
        unit_fields = {"id", "name", "kind", "legalOwnerPolityId", "controllerPolityId", "representedStrength", "strengthUnitId", "operationalState", "currentLocationId", "runtimeTemplateId", "locallyRelevant", "commanderOfficerId", "officerIds"}
        for raw in raw_units:
            if not isinstance(raw, Mapping) or set(raw) != unit_fields:
                raise MilitaryError("military unit state contains unexpected or missing fields")
            ident = _stable_id(raw.get("id"), "military unit id")
            if ident in units or ident not in self._unit_definitions:
                raise MilitaryError(f"military unit state: duplicate or incompatible ID {ident!r}")
            name, kind = raw.get("name"), raw.get("kind")
            if not isinstance(name, str) or not name.strip() or kind not in _KINDS:
                raise MilitaryError(f"military unit {ident}: invalid name or kind")
            owner, controller = self._validate_owner(raw, f"military unit {ident}")
            strength = raw.get("representedStrength")
            if isinstance(strength, bool) or not isinstance(strength, int) or strength < 1:
                raise MilitaryError(f"military unit {ident}: representedStrength must be positive")
            strength_unit = _stable_id(raw.get("strengthUnitId"), f"military unit {ident}.strengthUnitId")
            location = _stable_id(raw.get("currentLocationId"), f"military unit {ident}.currentLocationId")
            if location not in self._zones or _KINDS[kind] not in self._zones[location].get("movementClasses", []):
                raise MilitaryError(f"military unit {ident}: incompatible location {location!r}")
            template = _stable_id(raw.get("runtimeTemplateId"), f"military unit {ident}.runtimeTemplateId")
            if template not in self._templates or self._templates[template].get("unitKind") != kind:
                raise MilitaryError(f"military unit {ident}: incompatible runtime template {template!r}")
            if not isinstance(raw.get("locallyRelevant"), bool):
                raise MilitaryError(f"military unit {ident}: locallyRelevant must be boolean")
            units[ident] = {**copy.deepcopy(dict(raw)), "legalOwnerPolityId": owner,
                "controllerPolityId": controller, "representedStrength": strength,
                "strengthUnitId": strength_unit, "operationalState": self._validate_operational(raw.get("operationalState"), f"military unit {ident}"),
                "currentLocationId": location, "runtimeTemplateId": template,
                "officerIds": list(self._validate_officers(raw, f"military unit {ident}"))}
        if set(units) != set(self._unit_definitions):
            raise MilitaryError("military unit state must cover scenario units exactly")

        groups: dict[str, dict[str, Any]] = {}
        membership: dict[str, str] = {}
        group_fields = {"id", "kind", "name", "legalOwnerPolityId", "controllerPolityId", "memberUnitIds", "operationalState", "commanderOfficerId", "officerIds"}
        expected_groups = {**self._army_definitions, **self._fleet_definitions}
        for raw in raw_groups:
            if not isinstance(raw, Mapping) or set(raw) != group_fields:
                raise MilitaryError("military group state contains unexpected or missing fields")
            ident = _stable_id(raw.get("id"), "military group id")
            kind = raw.get("kind")
            if ident in groups or ident not in expected_groups or kind not in {"army", "fleet"}:
                raise MilitaryError(f"military group state: duplicate or incompatible ID {ident!r}")
            if (ident in self._army_definitions) != (kind == "army"):
                raise MilitaryError(f"military group {ident}: incompatible kind")
            name = raw.get("name")
            if not isinstance(name, str) or not name.strip():
                raise MilitaryError(f"military group {ident}: invalid name")
            owner, controller = self._validate_owner(raw, f"military group {ident}")
            members = raw.get("memberUnitIds")
            if not isinstance(members, list) or not members:
                raise MilitaryError(f"military group {ident}: at least one member is required")
            checked = []
            expected_kind = "formation" if kind == "army" else "ship"
            for member in members:
                member = _stable_id(member, f"military group {ident}.memberUnitIds")
                if member in checked:
                    raise MilitaryError(f"military group {ident}: duplicate member {member!r}")
                if member not in units or units[member]["kind"] != expected_kind:
                    raise MilitaryError(f"military group {ident}: incompatible member {member!r}")
                if member in membership:
                    raise MilitaryError(f"military unit {member!r} belongs to multiple groups")
                if units[member]["controllerPolityId"] != controller:
                    raise MilitaryError(f"military group {ident}: member controller differs")
                membership[member] = ident
                checked.append(member)
            groups[ident] = {**copy.deepcopy(dict(raw)), "legalOwnerPolityId": owner,
                "controllerPolityId": controller, "memberUnitIds": checked,
                "operationalState": self._validate_operational(raw.get("operationalState"), f"military group {ident}"),
                "officerIds": list(self._validate_officers(raw, f"military group {ident}"))}
        if set(groups) != set(expected_groups):
            raise MilitaryError("military group state must cover scenario groups exactly")
        return {"schemaVersion": 1, "units": [units[x] for x in sorted(units)], "groups": [groups[x] for x in sorted(groups)]}

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    def _unit(self, unit_id: str) -> dict[str, Any]:
        return next((x for x in self._state["units"] if x["id"] == unit_id), None) or self._unknown("unit", unit_id)

    def _group(self, group_id: str) -> dict[str, Any]:
        return next((x for x in self._state["groups"] if x["id"] == group_id), None) or self._unknown("group", group_id)

    @staticmethod
    def _unknown(kind: str, ident: str):
        raise MilitaryError(f"unknown military {kind} {ident!r}")

    def unit(self, unit_id: str) -> UnitView:
        value = self._unit(unit_id)
        operational = value["operationalState"]
        return UnitView(value["id"], value["name"], value["kind"], value["legalOwnerPolityId"],
            value["controllerPolityId"], value["representedStrength"], value["strengthUnitId"],
            operational["morale"], operational["supply"], operational["readiness"],
            value["currentLocationId"], value["commanderOfficerId"], tuple(value["officerIds"]),
            value["runtimeTemplateId"], value["locallyRelevant"], len(self._representations.get(unit_id, ())))

    def _commit(self, candidate: dict[str, Any]) -> bool:
        validated = self.validate_snapshot(candidate)
        changed = validated != self._state
        self._state = validated
        return changed

    def set_members(self, group_id: str, member_unit_ids: list[str]) -> bool:
        candidate = self.snapshot()
        group = next((x for x in candidate["groups"] if x["id"] == group_id), None)
        if group is None:
            self._unknown("group", group_id)
        group["memberUnitIds"] = copy.deepcopy(member_unit_ids)
        return self._commit(candidate)

    def assign_command(self, entity_id: str, commander_officer_id: str | None) -> bool:
        candidate = self.snapshot()
        entity = next((x for key in ("units", "groups") for x in candidate[key] if x["id"] == entity_id), None)
        if entity is None:
            self._unknown("entity", entity_id)
        entity["commanderOfficerId"] = commander_officer_id
        return self._commit(candidate)

    def set_ownership(self, entity_id: str, legal_owner_polity_id: str, controller_polity_id: str) -> bool:
        candidate = self.snapshot()
        entity = next((x for key in ("units", "groups") for x in candidate[key] if x["id"] == entity_id), None)
        if entity is None:
            self._unknown("entity", entity_id)
        entity["legalOwnerPolityId"], entity["controllerPolityId"] = legal_owner_polity_id, controller_polity_id
        if entity in candidate["groups"]:
            for unit in candidate["units"]:
                if unit["id"] in entity["memberUnitIds"]:
                    unit["legalOwnerPolityId"], unit["controllerPolityId"] = legal_owner_polity_id, controller_polity_id
        changed = self._commit(candidate)
        if changed and self._traditions is not None:
            targets = entity["memberUnitIds"] if entity in candidate["groups"] else [entity_id]
            for unit_id in targets:
                self._traditions.change_unit(unit_id, controller_id=controller_polity_id)
        return changed

    def update_unit(self, unit_id: str, *, represented_strength: int | None = None, morale: int | None = None, supply: int | None = None, readiness: int | None = None) -> bool:
        candidate = self.snapshot()
        unit = next((x for x in candidate["units"] if x["id"] == unit_id), None)
        if unit is None:
            self._unknown("unit", unit_id)
        if represented_strength is not None:
            unit["representedStrength"] = represented_strength
        for key, value in (("morale", morale), ("supply", supply), ("readiness", readiness)):
            if value is not None:
                unit["operationalState"][key] = value
        return self._commit(candidate)

    def update_operational(self, entity_id: str, *, morale: int | None = None, supply: int | None = None, readiness: int | None = None) -> bool:
        """Atomically update army, fleet, or strategic-unit operational scores."""
        candidate = self.snapshot()
        entity = next((x for key in ("units", "groups") for x in candidate[key] if x["id"] == entity_id), None)
        if entity is None:
            self._unknown("entity", entity_id)
        if morale is None and supply is None and readiness is None:
            return False
        for key, value in (("morale", morale), ("supply", supply), ("readiness", readiness)):
            if value is not None:
                entity["operationalState"][key] = value
        return self._commit(candidate)

    def consume_supply(self, entity_id: str, amount: int) -> bool:
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise MilitaryError("supply consumption must be a non-negative integer")
        candidate = self.snapshot()
        entity = next((x for key in ("units", "groups") for x in candidate[key] if x["id"] == entity_id), None)
        if entity is None:
            self._unknown("entity", entity_id)
        if entity["operationalState"]["supply"] < amount:
            raise MilitaryError(f"military entity {entity_id!r} has insufficient supply")
        entity["operationalState"]["supply"] -= amount
        return self._commit(candidate)

    def _reachable(self, kind: str, origin: str, destination: str) -> bool:
        movement = _KINDS[kind]
        if destination not in self._zones or movement not in self._zones[destination].get("movementClasses", []):
            return False
        pending, visited = [origin], set()
        while pending:
            current = pending.pop()
            if current == destination:
                return True
            if current in visited or current not in self._zones:
                continue
            visited.add(current)
            pending.extend(sorted(set(self._zones[current].get("connections", {}).get(movement, [])) - visited, reverse=True))
        return False

    def move(self, entity_id: str, destination_location_id: str, *, hostile_to_polity_id: str | None = None, supply_cost: int = 0) -> bool:
        candidate = self.snapshot()
        group = next((x for x in candidate["groups"] if x["id"] == entity_id), None)
        units = candidate["units"]
        targets = [x for x in units if x["id"] in group["memberUnitIds"]] if group else [x for x in units if x["id"] == entity_id]
        if not targets:
            self._unknown("entity", entity_id)
        controller = group["controllerPolityId"] if group else targets[0]["controllerPolityId"]
        if hostile_to_polity_id is not None:
            _stable_id(hostile_to_polity_id, "hostile polity")
            if hostile_to_polity_id not in self._polities or not self._conflict_is_active(controller, hostile_to_polity_id):
                raise MilitaryError("hostile operation requires an active legal conflict")
        if isinstance(supply_cost, bool) or not isinstance(supply_cost, int) or supply_cost < 0:
            raise MilitaryError("movement supply cost must be a non-negative integer")
        for unit in targets:
            if not self._reachable(unit["kind"], unit["currentLocationId"], destination_location_id):
                raise MilitaryError(f"military unit {unit['id']!r} cannot reach {destination_location_id!r}")
            if unit["operationalState"]["supply"] < supply_cost:
                raise MilitaryError(f"military unit {unit['id']!r} has insufficient supply")
        for unit in targets:
            unit["currentLocationId"] = destination_location_id
            unit["operationalState"]["supply"] -= supply_cost
        if group:
            if group["operationalState"]["supply"] < supply_cost:
                raise MilitaryError(f"military group {entity_id!r} has insufficient supply")
            group["operationalState"]["supply"] -= supply_cost
        return self._commit(candidate)

    def set_locally_relevant(self, unit_id: str, relevant: bool) -> bool:
        if not isinstance(relevant, bool):
            raise MilitaryError("local relevance must be boolean")
        candidate = self.snapshot()
        unit = next((x for x in candidate["units"] if x["id"] == unit_id), None)
        if unit is None:
            self._unknown("unit", unit_id)
        changed = unit["locallyRelevant"] != relevant
        if not changed:
            self.recover_representations()
            return False
        unit["locallyRelevant"] = relevant
        validated = self.validate_snapshot(candidate)
        if relevant:
            created = self._create_for(validated, unit_id)
            self._state = validated
            self._representations[unit_id] = created
            if self._traditions is not None:
                self._traditions.set_runtime_active(unit_id, True)
        else:
            old = self._representations.pop(unit_id, [])
            self._state = validated
            for handle in old:
                self._adapter.retire(handle)
            if self._traditions is not None:
                self._traditions.set_runtime_active(unit_id, False)
        return True

    def _create_for(self, state: Mapping[str, Any], unit_id: str) -> list[Any]:
        unit = next(x for x in state["units"] if x["id"] == unit_id)
        template = self._templates[unit["runtimeTemplateId"]]
        count = template.get("activeObjectCount")
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise MilitaryError(f"runtime template {unit['runtimeTemplateId']}: activeObjectCount must be positive")
        specification = {"runtimeTemplate": copy.deepcopy(dict(template)), "strategicState": copy.deepcopy(unit)}
        created = []
        try:
            for _ in range(count):
                created.append(self._adapter.create(unit_id, specification))
        except Exception:
            for handle in created:
                self._adapter.retire(handle)
            raise
        return created

    def recover_representations(self) -> None:
        for unit in self._state["units"]:
            ident = unit["id"]
            live = [handle for handle in self._representations.get(ident, []) if self._adapter.exists(handle)]
            expected = self._templates[unit["runtimeTemplateId"]].get("activeObjectCount") if unit["locallyRelevant"] else 0
            if len(live) != expected:
                for handle in live:
                    self._adapter.retire(handle)
                self._representations.pop(ident, None)
                if unit["locallyRelevant"]:
                    self._representations[ident] = self._create_for(self._state, ident)

    def reconstruct_representations(self) -> None:
        staged = {}
        try:
            for unit in self._state["units"]:
                if unit["locallyRelevant"]:
                    staged[unit["id"]] = self._create_for(self._state, unit["id"])
        except Exception:
            for handles in staged.values():
                for handle in handles:
                    self._adapter.retire(handle)
            raise
        old, self._representations = self._representations, staged
        for handles in old.values():
            for handle in handles:
                self._adapter.retire(handle)
        if self._traditions is not None:
            self._traditions.reconstruct(sorted(staged))

    def restore(self, candidate: Any, *, reconstruct: bool = True) -> None:
        restored = self.validate_snapshot(candidate)
        old_state = self._state
        self._state = restored
        try:
            if reconstruct:
                self.reconstruct_representations()
        except Exception:
            self._state = old_state
            raise


class MilitarySaveAdapter:
    """CampaignSaveManager callbacks for authoritative military state."""

    def __init__(self, runtime: MilitaryRuntime, world_state: Mapping[str, Any]):
        self.runtime = runtime
        self.world_state = copy.deepcopy(dict(world_state))

    def capture_world(self) -> dict[str, Any]:
        result = copy.deepcopy(self.world_state)
        result[MILITARY_WORLD_STATE_KEY] = self.runtime.snapshot()
        return result

    def migrate_legacy_world(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(candidate, Mapping):
            raise MilitaryError("legacy world state must be an object")
        result = copy.deepcopy(dict(candidate))
        result.setdefault(MILITARY_WORLD_STATE_KEY, self.runtime.snapshot())
        self.validate_world(result)
        return result

    def validate_world(self, candidate: Mapping[str, Any]) -> None:
        if not isinstance(candidate, Mapping) or MILITARY_WORLD_STATE_KEY not in candidate:
            raise MilitaryError(f"world state is missing {MILITARY_WORLD_STATE_KEY}")
        self.runtime.validate_snapshot(candidate[MILITARY_WORLD_STATE_KEY])

    def reconstruct(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        self.validate_world(candidate)
        return self.runtime.validate_snapshot(candidate[MILITARY_WORLD_STATE_KEY])

    def activate(self, candidate: Mapping[str, Any], reconstructed: Mapping[str, Any]) -> None:
        expected = self.runtime.validate_snapshot(candidate[MILITARY_WORLD_STATE_KEY])
        if dict(reconstructed) != expected:
            raise MilitaryError("reconstructed military state does not match candidate state")
        self.runtime.restore(expected, reconstruct=True)
        self.world_state = copy.deepcopy(dict(candidate))

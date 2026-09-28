"""Authoritative settlement state and transient Warcraft representations.

Scenario data owns every settlement, service, and representation template.  The
runtime deliberately stores adapter handles separately from campaign state.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Protocol


SETTLEMENT_STATE_SCHEMA_VERSION = 1
SETTLEMENT_WORLD_STATE_KEY = "settlementState"
SETTLEMENT_KINDS = frozenset({
    "capital", "major_city", "city", "town", "village", "port", "fort",
    "trading_post", "mission", "mine", "plantation", "pirate_haven",
})
_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class SettlementError(ValueError):
    pass


class SettlementRepresentationAdapter(Protocol):
    """Compatibility boundary for Warcraft object creation and destruction."""

    def create(self, settlement_id: str, specification: Mapping[str, Any]) -> Any: ...
    def destroy(self, representation: Any) -> None: ...


class RecordingSettlementAdapter:
    """Headless deterministic adapter harness used by tests and simulations."""

    def __init__(self) -> None:
        self.operations: list[tuple[str, Any]] = []
        self._serial = 0

    def create(self, settlement_id: str, specification: Mapping[str, Any]) -> str:
        self._serial += 1
        handle = f"representation_{self._serial}"
        self.operations.append(("create", settlement_id, copy.deepcopy(dict(specification)), handle))
        return handle

    def destroy(self, representation: Any) -> None:
        self.operations.append(("destroy", representation))


@dataclass(frozen=True)
class SettlementDefinition:
    id: str
    name: str
    initial_legal_owner_polity_id: str
    initial_controller_polity_id: str
    initial_province_id: str
    initial_kind: str
    initial_capturable: bool
    navigation_zone_id: str | None
    city_core_id: str | None
    defense_layout_id: str | None
    service_ids: tuple[str, ...]


@dataclass(frozen=True)
class SettlementView:
    definition: SettlementDefinition
    legal_owner_polity_id: str
    controller_polity_id: str
    province_id: str
    kind: str
    capturable: bool
    navigation_zone_id: str | None
    city_core_id: str | None
    defense_layout_id: str | None
    operational: bool
    services: Mapping[str, bool]
    represented: bool

    @property
    def id(self) -> str:
        return self.definition.id


def _stable_id(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise SettlementError(f"{context}: invalid stable ID {value!r}")
    return value


def _optional_id(value: Any, context: str) -> str | None:
    return None if value is None else _stable_id(value, context)


def _index(world: Mapping[str, Any], key: str) -> dict[str, Mapping[str, Any]]:
    values = world.get(key)
    if not isinstance(values, list):
        raise SettlementError(f"{key}: must be an array")
    result: dict[str, Mapping[str, Any]] = {}
    for value in values:
        if not isinstance(value, Mapping):
            raise SettlementError(f"{key}: every entry must be an object")
        ident = _stable_id(value.get("id"), f"{key}.id")
        if ident in result:
            raise SettlementError(f"{key}: duplicate ID {ident!r}")
        result[ident] = value
    return result


class SettlementRuntime:
    """Stable definitions, mutable campaign state, and transient representations."""

    def __init__(self, world_definitions: Mapping[str, Any], adapter: SettlementRepresentationAdapter):
        if not isinstance(world_definitions, Mapping):
            raise SettlementError("world definitions must be an object")
        self._adapter = adapter
        self._world = copy.deepcopy(dict(world_definitions))
        self._definitions, self._representation_specs = self._load_definitions(self._world)
        self._by_id = MappingProxyType({item.id: item for item in self._definitions})
        self._state = {
            item.id: {
                "legalOwnerPolityId": item.initial_legal_owner_polity_id,
                "controllerPolityId": item.initial_controller_polity_id,
                "provinceId": item.initial_province_id,
                "kind": item.initial_kind,
                "capturable": item.initial_capturable,
                "navigationZoneId": item.navigation_zone_id,
                "cityCoreId": item.city_core_id,
                "defenseLayoutId": item.defense_layout_id,
                "operational": True,
                "services": {service_id: True for service_id in item.service_ids},
            }
            for item in self._definitions
        }
        self._representations: dict[str, Any] = {}

    @staticmethod
    def _load_definitions(world: Mapping[str, Any]):
        polities = _index(world, "polities")
        provinces = _index(world, "provinces")
        zones = _index(world, "navigationZones")
        services = _index(world, "settlementServiceDefinitions")
        templates = _index(world, "settlementObjectTemplates")
        cores = _index(world, "cityCores")
        layouts = _index(world, "defenseLayouts")
        settlements = _index(world, "settlements")

        for core_id, core in cores.items():
            template_id = _stable_id(core.get("objectTemplateId"), f"city core {core_id}.objectTemplateId")
            if template_id not in templates:
                raise SettlementError(f"city core {core_id}: missing object template {template_id!r}")
        for layout_id, layout in layouts.items():
            refs = layout.get("objectTemplateIds")
            if not isinstance(refs, list):
                raise SettlementError(f"defense layout {layout_id}.objectTemplateIds: must be an array")
            seen: set[str] = set()
            for raw_ref in refs:
                ref = _stable_id(raw_ref, f"defense layout {layout_id}.objectTemplateIds")
                if ref in seen:
                    raise SettlementError(f"defense layout {layout_id}: duplicate object template {ref!r}")
                if ref not in templates:
                    raise SettlementError(f"defense layout {layout_id}: missing object template {ref!r}")
                seen.add(ref)

        definitions: list[SettlementDefinition] = []
        specs: dict[str, dict[str, Any]] = {}
        for settlement_id, value in settlements.items():
            owner = _stable_id(value.get("legalOwnerPolityId"), f"settlement {settlement_id}.legalOwnerPolityId")
            controller = _stable_id(value.get("controllerPolityId"), f"settlement {settlement_id}.controllerPolityId")
            province_id = _stable_id(value.get("provinceId"), f"settlement {settlement_id}.provinceId")
            if owner not in polities:
                raise SettlementError(f"settlement {settlement_id}: missing legal owner polity {owner!r}")
            if controller not in polities:
                raise SettlementError(f"settlement {settlement_id}: missing controller polity {controller!r}")
            if province_id not in provinces:
                raise SettlementError(f"settlement {settlement_id}: missing province {province_id!r}")
            if settlement_id not in provinces[province_id].get("settlementIds", []):
                raise SettlementError(f"settlement {settlement_id}: province {province_id!r} does not include settlement")
            kind = value.get("kind")
            if kind not in SETTLEMENT_KINDS:
                raise SettlementError(f"settlement {settlement_id}: invalid kind {kind!r}")
            capturable = value.get("capturable")
            if not isinstance(capturable, bool):
                raise SettlementError(f"settlement {settlement_id}.capturable must be boolean")
            zone_id = _optional_id(value.get("navigationZoneId"), f"settlement {settlement_id}.navigationZoneId")
            core_id = _optional_id(value.get("cityCoreId"), f"settlement {settlement_id}.cityCoreId")
            layout_id = _optional_id(value.get("defenseLayoutId"), f"settlement {settlement_id}.defenseLayoutId")
            if zone_id is not None and zone_id not in zones:
                raise SettlementError(f"settlement {settlement_id}: missing navigation zone {zone_id!r}")
            if core_id is not None and core_id not in cores:
                raise SettlementError(f"settlement {settlement_id}: missing city core {core_id!r}")
            if layout_id is not None and layout_id not in layouts:
                raise SettlementError(f"settlement {settlement_id}: missing defense layout {layout_id!r}")
            if capturable and (core_id is None or layout_id is None):
                raise SettlementError(f"settlement {settlement_id}: capturable settlements require city core and defense layout")
            raw_service_ids = value.get("serviceIds")
            if not isinstance(raw_service_ids, list):
                raise SettlementError(f"settlement {settlement_id}.serviceIds: must be an array")
            service_ids: list[str] = []
            for raw_service_id in raw_service_ids:
                service_id = _stable_id(raw_service_id, f"settlement {settlement_id}.serviceIds")
                if service_id in service_ids:
                    raise SettlementError(f"settlement {settlement_id}: duplicate service {service_id!r}")
                if service_id not in services:
                    raise SettlementError(f"settlement {settlement_id}: missing service {service_id!r}")
                service_ids.append(service_id)
            name = value.get("name")
            if not isinstance(name, str) or not name.strip():
                raise SettlementError(f"settlement {settlement_id}.name must be non-empty text")
            definitions.append(SettlementDefinition(
                settlement_id, name, owner, controller, province_id, kind, capturable,
                zone_id, core_id, layout_id, tuple(service_ids),
            ))
            specs[settlement_id] = {
                "navigationZoneId": zone_id,
                "cityCore": copy.deepcopy(cores.get(core_id)) if core_id else None,
                "defenseLayout": copy.deepcopy(layouts.get(layout_id)) if layout_id else None,
                "objectTemplates": {
                    template_id: copy.deepcopy(templates[template_id])
                    for template_id in sorted(templates)
                    if (core_id and cores[core_id]["objectTemplateId"] == template_id)
                    or (layout_id and template_id in layouts[layout_id]["objectTemplateIds"])
                },
            }
        if not definitions:
            raise SettlementError("at least one settlement is required")
        return tuple(sorted(definitions, key=lambda item: item.id)), MappingProxyType(specs)

    @property
    def definitions(self) -> tuple[SettlementDefinition, ...]:
        return self._definitions

    def ids(self) -> tuple[str, ...]:
        return tuple(item.id for item in self._definitions)

    def lookup(self, settlement_id: str) -> SettlementView | None:
        definition = self._by_id.get(settlement_id)
        if definition is None:
            return None
        state = self._state[settlement_id]
        return SettlementView(
            definition, state["legalOwnerPolityId"], state["controllerPolityId"],
            state["provinceId"], state["kind"], state["capturable"],
            state["navigationZoneId"], state["cityCoreId"], state["defenseLayoutId"],
            state["operational"],
            MappingProxyType(dict(state["services"])), settlement_id in self._representations,
        )

    def require(self, settlement_id: str) -> SettlementView:
        result = self.lookup(settlement_id)
        if result is None:
            raise SettlementError(f"unknown settlement {settlement_id!r}")
        return result

    def enumerate(self) -> tuple[SettlementView, ...]:
        return tuple(self.require(ident) for ident in self.ids())

    def update(self, settlement_id: str, **changes: Any) -> bool:
        self.require(settlement_id)
        allowed = {"legalOwnerPolityId", "controllerPolityId", "provinceId", "kind", "capturable", "operational"}
        if not changes or set(changes) - allowed:
            raise SettlementError(f"unsupported settlement update fields: {sorted(set(changes) - allowed)!r}")
        candidate = copy.deepcopy(self._state)
        candidate[settlement_id].update(changes)
        validated = self._validate_records(self._records(candidate))
        changed = candidate != self._state
        self._state = validated
        return changed

    def set_service_available(self, settlement_id: str, service_id: str, available: bool) -> bool:
        self.require(settlement_id)
        if service_id not in self._state[settlement_id]["services"]:
            raise SettlementError(f"settlement {settlement_id!r} has no service {service_id!r}")
        if not isinstance(available, bool):
            raise SettlementError("service availability must be boolean")
        changed = self._state[settlement_id]["services"][service_id] != available
        self._state[settlement_id]["services"][service_id] = available
        return changed

    def representation_specification(self, settlement_id: str) -> dict[str, Any]:
        """Return validated scenario-owned reconstruction data without runtime handles."""
        self.require(settlement_id)
        return copy.deepcopy(dict(self._representation_specs[settlement_id]))

    def create_representation(self, settlement_id: str) -> Any:
        view = self.require(settlement_id)
        if not view.operational:
            raise SettlementError(f"settlement {settlement_id!r} is not operational")
        if settlement_id in self._representations:
            return self._representations[settlement_id]
        handle = self._adapter.create(settlement_id, self._representation_specs[settlement_id])
        self._representations[settlement_id] = handle
        return handle

    def destroy_representation(self, settlement_id: str) -> bool:
        self.require(settlement_id)
        handle = self._representations.pop(settlement_id, None)
        if handle is None:
            return False
        self._adapter.destroy(handle)
        return True

    def reconstruct_representations(self) -> None:
        staged = self._stage_representations(self._state)
        old = self._representations
        self._representations = staged
        for settlement_id in sorted(old):
            self._adapter.destroy(old[settlement_id])

    def _stage_representations(self, state: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
        staged: dict[str, Any] = {}
        try:
            for settlement_id in self.ids():
                if state[settlement_id]["operational"]:
                    staged[settlement_id] = self._adapter.create(settlement_id, self._representation_specs[settlement_id])
        except Exception:
            for created_id in sorted(staged):
                self._adapter.destroy(staged[created_id])
            raise
        return staged

    def _records(self, state: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
        return [{"id": ident, **copy.deepcopy(dict(state[ident]))} for ident in self.ids()]

    def snapshot(self) -> dict[str, Any]:
        return {"schemaVersion": SETTLEMENT_STATE_SCHEMA_VERSION, "settlements": self._records(self._state)}

    def _validate_records(self, records: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(records, list):
            raise SettlementError("settlement state settlements must be an array")
        restored: dict[str, dict[str, Any]] = {}
        expected_fields = {
            "id", "legalOwnerPolityId", "controllerPolityId", "provinceId", "kind",
            "capturable", "navigationZoneId", "cityCoreId", "defenseLayoutId",
            "operational", "services",
        }
        polities = set(_index(self._world, "polities"))
        provinces = _index(self._world, "provinces")
        for record in records:
            if not isinstance(record, Mapping) or set(record) != expected_fields:
                raise SettlementError("settlement state entries contain unexpected or missing fields")
            ident = _stable_id(record.get("id"), "settlement state id")
            if ident in restored:
                raise SettlementError(f"settlement state: duplicate ID {ident!r}")
            definition = self._by_id.get(ident)
            if definition is None:
                raise SettlementError(f"settlement state: incompatible settlement {ident!r}")
            owner = _stable_id(record.get("legalOwnerPolityId"), f"settlement state {ident}.legalOwnerPolityId")
            controller = _stable_id(record.get("controllerPolityId"), f"settlement state {ident}.controllerPolityId")
            province_id = _stable_id(record.get("provinceId"), f"settlement state {ident}.provinceId")
            if owner not in polities or controller not in polities:
                raise SettlementError(f"settlement state {ident}: missing polity reference")
            if province_id not in provinces or ident not in provinces[province_id].get("settlementIds", []):
                raise SettlementError(f"settlement state {ident}: inconsistent province {province_id!r}")
            kind = record.get("kind")
            if kind not in SETTLEMENT_KINDS:
                raise SettlementError(f"settlement state {ident}: invalid kind {kind!r}")
            if not isinstance(record.get("capturable"), bool) or not isinstance(record.get("operational"), bool):
                raise SettlementError(f"settlement state {ident}: capturable and operational must be boolean")
            reference_values = (
                record.get("navigationZoneId"), record.get("cityCoreId"),
                record.get("defenseLayoutId"),
            )
            expected_references = (
                definition.navigation_zone_id, definition.city_core_id,
                definition.defense_layout_id,
            )
            if reference_values != expected_references:
                raise SettlementError(f"settlement state {ident}: representation references are incompatible")
            service_state = record.get("services")
            if not isinstance(service_state, Mapping) or set(service_state) != set(definition.service_ids):
                raise SettlementError(f"settlement state {ident}: service set is incompatible")
            if not all(isinstance(value, bool) for value in service_state.values()):
                raise SettlementError(f"settlement state {ident}: service availability must be boolean")
            restored[ident] = {
                "legalOwnerPolityId": owner, "controllerPolityId": controller,
                "provinceId": province_id, "kind": kind, "capturable": record["capturable"],
                "navigationZoneId": record["navigationZoneId"],
                "cityCoreId": record["cityCoreId"],
                "defenseLayoutId": record["defenseLayoutId"],
                "operational": record["operational"], "services": dict(service_state),
            }
        missing = set(self._by_id) - set(restored)
        if missing:
            raise SettlementError(f"settlement state: missing settlement {sorted(missing)[0]!r}")
        return {ident: restored[ident] for ident in self.ids()}

    def validate_snapshot(self, candidate: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(candidate, Mapping) or candidate.get("schemaVersion") != SETTLEMENT_STATE_SCHEMA_VERSION:
            raise SettlementError("settlement state schemaVersion must be 1")
        if set(candidate) != {"schemaVersion", "settlements"}:
            raise SettlementError("settlement state contains unexpected fields")
        return self._validate_records(candidate.get("settlements"))

    def restore(self, candidate: Any, *, reconstruct: bool = True) -> None:
        restored = self.validate_snapshot(candidate)
        staged = self._stage_representations(restored) if reconstruct else None
        old = self._representations
        self._state = restored
        if staged is not None:
            self._representations = staged
            for settlement_id in sorted(old):
                self._adapter.destroy(old[settlement_id])


class SettlementSaveAdapter:
    """CampaignSaveManager callbacks with validation-before-activation semantics."""

    def __init__(self, runtime: SettlementRuntime, world_state: Mapping[str, Any]):
        self.runtime = runtime
        self.world_state = copy.deepcopy(dict(world_state))

    def capture_world(self) -> dict[str, Any]:
        result = copy.deepcopy(self.world_state)
        result[SETTLEMENT_WORLD_STATE_KEY] = self.runtime.snapshot()
        return result

    def migrate_legacy_world(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(candidate, Mapping):
            raise SettlementError("legacy world state must be an object")
        migrated = copy.deepcopy(dict(candidate))
        if SETTLEMENT_WORLD_STATE_KEY not in migrated:
            migrated[SETTLEMENT_WORLD_STATE_KEY] = self.runtime.snapshot()
        self.validate_world(migrated)
        return migrated

    def validate_world(self, candidate: Mapping[str, Any]) -> None:
        if not isinstance(candidate, Mapping) or SETTLEMENT_WORLD_STATE_KEY not in candidate:
            raise SettlementError(f"world state is missing {SETTLEMENT_WORLD_STATE_KEY}")
        self.runtime.validate_snapshot(candidate[SETTLEMENT_WORLD_STATE_KEY])

    def reconstruct(self, candidate: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        self.validate_world(candidate)
        return self.runtime.validate_snapshot(candidate[SETTLEMENT_WORLD_STATE_KEY])

    def activate(self, candidate: Mapping[str, Any], reconstructed: Mapping[str, Mapping[str, Any]]) -> None:
        expected = self.runtime.validate_snapshot(candidate[SETTLEMENT_WORLD_STATE_KEY])
        if dict(reconstructed) != expected:
            raise SettlementError("reconstructed settlement state does not match candidate state")
        self.runtime.restore(candidate[SETTLEMENT_WORLD_STATE_KEY], reconstruct=True)
        self.world_state = copy.deepcopy(dict(candidate))

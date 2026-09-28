"""Authoritative, scenario-neutral province ownership and governance state."""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Mapping

PROVINCE_STATE_SCHEMA_VERSION = 1
PROVINCE_WORLD_STATE_KEY = "provinceState"
_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class ProvinceError(ValueError):
    pass


@dataclass(frozen=True)
class ProvinceDefinition:
    id: str
    name: str
    administrative_type: str
    settlement_ids: tuple[str, ...]


@dataclass(frozen=True)
class ProvinceView:
    definition: ProvinceDefinition
    legal_owner_polity_id: str
    controller_polity_id: str
    governing_polity_id: str
    sovereign_polity_id: str
    autonomy_percent: float
    occupied: bool

    @property
    def id(self) -> str:
        return self.definition.id


@dataclass(frozen=True)
class ProvinceTransitionEvent:
    sequence: int
    province_id: str
    reason: str
    changes: tuple[tuple[str, str, str], ...]

    def to_dict(self) -> dict:
        return {
            "sequence": self.sequence,
            "provinceId": self.province_id,
            "reason": self.reason,
            "changes": [
                {"field": field, "fromPolityId": old, "toPolityId": new}
                for field, old, new in self.changes
            ],
        }


def _stable_id(value, context):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ProvinceError(f"{context}: invalid stable ID {value!r}")
    return value


def _text(value, context):
    if not isinstance(value, str) or not value.strip():
        raise ProvinceError(f"{context}: must be non-empty text")
    return value


def _number(value, context):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
        raise ProvinceError(f"{context}: must be a number from 0 through 100")
    return value


def _index(values, domain):
    if not isinstance(values, list):
        raise ProvinceError(f"{domain}: must be an array")
    result = {}
    for record in values:
        if not isinstance(record, Mapping):
            raise ProvinceError(f"{domain}: every entry must be an object")
        ident = _stable_id(record.get("id"), f"{domain}.id")
        if ident in result:
            raise ProvinceError(f"{domain}: duplicate ID {ident!r}")
        result[ident] = record
    return result


class ProvinceRuntime:
    """Mutable authority with derived indexes and deterministic transition history."""

    def __init__(self, world_definitions, polity_runtime):
        if not isinstance(world_definitions, Mapping):
            raise ProvinceError("world definitions must be an object")
        self.polities = polity_runtime
        world = copy.deepcopy(dict(world_definitions))
        provinces = _index(world.get("provinces"), "provinces")
        settlements = _index(world.get("settlements"), "settlements")
        holdings = _index(world.get("territorialHoldings"), "territorialHoldings")
        province_holdings = {}
        for holding in holdings.values():
            territory = holding.get("territory")
            if isinstance(territory, Mapping) and territory.get("kind") == "province":
                province_id = territory.get("id")
                if province_id in province_holdings:
                    raise ProvinceError(f"province {province_id!r}: duplicate territorial holding")
                province_holdings[province_id] = holding
        definitions, states = [], {}
        for province_id in sorted(provinces):
            record = provinces[province_id]
            settlement_ids = record.get("settlementIds")
            if not isinstance(settlement_ids, list):
                raise ProvinceError(f"province {province_id}.settlementIds: must be an array")
            checked = []
            for settlement_id in settlement_ids:
                settlement_id = _stable_id(settlement_id, f"province {province_id}.settlementIds")
                if settlement_id in checked:
                    raise ProvinceError(f"province {province_id}: duplicate settlement {settlement_id!r}")
                if settlement_id not in settlements or settlements[settlement_id].get("provinceId") != province_id:
                    raise ProvinceError(f"province {province_id}: invalid settlement {settlement_id!r}")
                checked.append(settlement_id)
            definition = ProvinceDefinition(
                province_id,
                _text(record.get("name"), f"province {province_id}.name"),
                _text(record.get("administrativeType"), f"province {province_id}.administrativeType"),
                tuple(checked),
            )
            holding = province_holdings.get(province_id)
            if holding is None:
                raise ProvinceError(f"province {province_id}: missing territorial holding")
            legal_owner = holding.get("legalOwner")
            if not isinstance(legal_owner, Mapping) or legal_owner.get("kind") != "polity":
                raise ProvinceError(f"province {province_id}: legal owner must be a polity")
            owner = legal_owner.get("id")
            controller = holding.get("controllerPolityId")
            if owner != record.get("legalOwnerPolityId") or controller != record.get("controllerPolityId"):
                raise ProvinceError(f"province {province_id}: world and holding ownership/control disagree")
            state = ProvinceView(
                definition, owner, controller, holding.get("governingPolityId"),
                holding.get("sovereignPolityId"),
                _number(holding.get("autonomyPercent"), f"province {province_id}.autonomyPercent"),
                controller != owner,
            )
            for field in (state.legal_owner_polity_id, state.controller_polity_id,
                          state.governing_polity_id, state.sovereign_polity_id):
                if self.polities.lookup(field) is None:
                    raise ProvinceError(f"province {province_id}: missing polity {field!r}")
            definitions.append(definition); states[province_id] = state
        if not definitions:
            raise ProvinceError("at least one province is required")
        self._definitions = tuple(definitions)
        self._states = states
        self._initial_states = dict(states)
        self._events = []
        self._next_sequence = 1
        self._rebuild_indexes()

    def _rebuild_indexes(self):
        self._by_id = MappingProxyType(dict(self._states))
        fields = {
            "legal_owner": "legal_owner_polity_id", "controller": "controller_polity_id",
            "governing": "governing_polity_id", "sovereign": "sovereign_polity_id",
        }
        self._polity_indexes = MappingProxyType({
            kind: MappingProxyType({polity_id: tuple(sorted(
                province.id for province in self._states.values()
                if getattr(province, attribute) == polity_id
            )) for polity_id in self.polities.ids()})
            for kind, attribute in fields.items()
        })

    @property
    def definitions(self): return self._definitions
    @property
    def events(self): return tuple(self._events)
    def ids(self): return tuple(item.id for item in self._definitions)
    def lookup(self, province_id): return self._by_id.get(province_id)
    def require(self, province_id):
        result = self.lookup(province_id)
        if result is None: raise ProvinceError(f"unknown province {province_id!r}")
        return result
    def enumerate(self): return tuple(self.require(ident) for ident in self.ids())
    def provinces_for(self, polity_id, relationship="legal_owner"):
        self.polities.require(polity_id)
        if relationship not in self._polity_indexes:
            raise ProvinceError(f"unknown province relationship {relationship!r}")
        return self._polity_indexes[relationship][polity_id]
    def indexes_snapshot(self):
        return {kind: {key: list(value) for key, value in index.items()}
                for kind, index in self._polity_indexes.items()}

    def transition(self, province_id, *, controller_polity_id=None,
                   legal_owner_polity_id=None, reason="unspecified"):
        """Validate the whole change, then commit state, indexes, and one event."""
        current = self.require(province_id)
        reason = _stable_id(reason, "transition reason")
        for polity_id in (current.legal_owner_polity_id, current.controller_polity_id):
            if not self.polities.require(polity_id).active:
                raise ProvinceError(f"province {province_id}: inactive current participant {polity_id!r}")
        requested = {
            "legalOwnerPolityId": legal_owner_polity_id,
            "controllerPolityId": controller_polity_id,
        }
        for field, polity_id in requested.items():
            if polity_id is None: continue
            view = self.polities.lookup(polity_id)
            if view is None: raise ProvinceError(f"{field}: unknown polity {polity_id!r}")
            if not view.active: raise ProvinceError(f"{field}: inactive polity {polity_id!r}")
        owner = legal_owner_polity_id or current.legal_owner_polity_id
        controller = controller_polity_id or current.controller_polity_id
        changes = []
        if owner != current.legal_owner_polity_id:
            changes.append(("legalOwnerPolityId", current.legal_owner_polity_id, owner))
        if controller != current.controller_polity_id:
            changes.append(("controllerPolityId", current.controller_polity_id, controller))
        if not changes: raise ProvinceError("province transition must change ownership or control")
        updated = replace(current, legal_owner_polity_id=owner,
                          controller_polity_id=controller, occupied=controller != owner)
        event = ProvinceTransitionEvent(self._next_sequence, province_id, reason, tuple(changes))
        self._states[province_id] = updated
        self._events.append(event); self._next_sequence += 1
        self._rebuild_indexes()
        return event

    def snapshot(self):
        return {
            "schemaVersion": PROVINCE_STATE_SCHEMA_VERSION,
            "nextTransitionSequence": self._next_sequence,
            "provinces": [{
                "id": state.id,
                "legalOwnerPolityId": state.legal_owner_polity_id,
                "controllerPolityId": state.controller_polity_id,
                "governingPolityId": state.governing_polity_id,
                "sovereignPolityId": state.sovereign_polity_id,
                "autonomyPercent": state.autonomy_percent,
                "occupied": state.occupied,
            } for state in self.enumerate()],
            "transitionEvents": [event.to_dict() for event in self._events],
        }

    def _parse_snapshot(self, candidate):
        if not isinstance(candidate, Mapping) or candidate.get("schemaVersion") != PROVINCE_STATE_SCHEMA_VERSION:
            raise ProvinceError("province state schemaVersion must be 1")
        records = candidate.get("provinces")
        events = candidate.get("transitionEvents")
        next_sequence = candidate.get("nextTransitionSequence")
        if not isinstance(records, list) or not isinstance(events, list):
            raise ProvinceError("province state provinces and transitionEvents must be arrays")
        if isinstance(next_sequence, bool) or not isinstance(next_sequence, int) or next_sequence < 1:
            raise ProvinceError("nextTransitionSequence must be a positive integer")
        restored = {}
        expected_fields = {"id","legalOwnerPolityId","controllerPolityId","governingPolityId","sovereignPolityId","autonomyPercent","occupied"}
        for record in records:
            if not isinstance(record, Mapping) or set(record) != expected_fields:
                raise ProvinceError("province state entries have invalid fields")
            ident = _stable_id(record.get("id"), "province state id")
            if ident in restored: raise ProvinceError(f"province state: duplicate ID {ident!r}")
            definition = next((item for item in self._definitions if item.id == ident), None)
            if definition is None: raise ProvinceError(f"province state: incompatible province {ident!r}")
            polity_fields = [record.get(key) for key in ("legalOwnerPolityId","controllerPolityId","governingPolityId","sovereignPolityId")]
            if any(self.polities.lookup(value) is None for value in polity_fields):
                raise ProvinceError(f"province state {ident}: missing polity reference")
            if not isinstance(record.get("occupied"), bool) or record["occupied"] != (polity_fields[1] != polity_fields[0]):
                raise ProvinceError(f"province state {ident}: occupation does not match ownership/control")
            restored[ident] = ProvinceView(definition, *polity_fields,
                _number(record.get("autonomyPercent"), f"province state {ident}.autonomyPercent"), record["occupied"])
        missing = set(self.ids()) - set(restored)
        if missing: raise ProvinceError(f"province state: missing province {sorted(missing)[0]!r}")
        parsed_events = []
        replay = {ident: [state.legal_owner_polity_id, state.controller_polity_id]
                  for ident, state in self._initial_states.items()}
        for expected_sequence, raw in enumerate(events, 1):
            if not isinstance(raw, Mapping) or raw.get("sequence") != expected_sequence:
                raise ProvinceError("province transition events must have contiguous deterministic sequence numbers")
            province_id = raw.get("provinceId")
            if province_id not in restored: raise ProvinceError(f"province event: unknown province {province_id!r}")
            reason = _stable_id(raw.get("reason"), "province event reason")
            raw_changes = raw.get("changes")
            if not isinstance(raw_changes, list) or not raw_changes:
                raise ProvinceError("province event changes must be a non-empty array")
            changes = []
            for change in raw_changes:
                if not isinstance(change, Mapping) or change.get("field") not in ("legalOwnerPolityId","controllerPolityId"):
                    raise ProvinceError("province event contains an invalid change")
                old, new = change.get("fromPolityId"), change.get("toPolityId")
                if self.polities.lookup(old) is None or self.polities.lookup(new) is None or old == new:
                    raise ProvinceError("province event contains invalid polity references")
                position = 0 if change["field"] == "legalOwnerPolityId" else 1
                if replay[province_id][position] != old:
                    raise ProvinceError("province event history does not match prior state")
                replay[province_id][position] = new
                changes.append((change["field"], old, new))
            if [item[0] for item in changes] != sorted((item[0] for item in changes), key=lambda field: 0 if field == "legalOwnerPolityId" else 1) or len({item[0] for item in changes}) != len(changes):
                raise ProvinceError("province event changes must use deterministic field order")
            parsed_events.append(ProvinceTransitionEvent(expected_sequence, province_id, reason, tuple(changes)))
        if next_sequence != len(parsed_events) + 1:
            raise ProvinceError("nextTransitionSequence does not follow transition history")
        for ident, state in restored.items():
            if replay[ident] != [state.legal_owner_polity_id, state.controller_polity_id]:
                raise ProvinceError(f"province state {ident}: transition history does not match current state")
        return restored, parsed_events, next_sequence

    def validate_snapshot(self, candidate): self._parse_snapshot(candidate)
    def restore(self, candidate):
        restored, events, next_sequence = self._parse_snapshot(candidate)
        self._states, self._events, self._next_sequence = restored, events, next_sequence
        self._rebuild_indexes()


class ProvinceSaveAdapter:
    """Campaign-save callbacks for stable authoritative province state."""
    def __init__(self, runtime, world_state):
        self.runtime = runtime; self.world_state = copy.deepcopy(dict(world_state))
    def capture_world(self):
        result = copy.deepcopy(self.world_state)
        result[PROVINCE_WORLD_STATE_KEY] = self.runtime.snapshot()
        return result
    def migrate_legacy_world(self, candidate):
        if not isinstance(candidate, Mapping): raise ProvinceError("legacy world state must be an object")
        migrated = copy.deepcopy(dict(candidate))
        if PROVINCE_WORLD_STATE_KEY not in migrated:
            migrated[PROVINCE_WORLD_STATE_KEY] = self.runtime.snapshot()
        self.validate_world(migrated); return migrated
    def validate_world(self, candidate):
        if not isinstance(candidate, Mapping) or PROVINCE_WORLD_STATE_KEY not in candidate:
            raise ProvinceError(f"world state is missing {PROVINCE_WORLD_STATE_KEY}")
        self.runtime.validate_snapshot(candidate[PROVINCE_WORLD_STATE_KEY])
    def reconstruct(self, candidate):
        self.validate_world(candidate)
        snapshot = copy.deepcopy(candidate[PROVINCE_WORLD_STATE_KEY])
        self.runtime._parse_snapshot(snapshot)
        return snapshot
    def activate(self, candidate, reconstructed):
        if reconstructed != candidate[PROVINCE_WORLD_STATE_KEY]:
            raise ProvinceError("reconstructed province state does not match candidate state")
        self.runtime.restore(reconstructed); self.world_state = copy.deepcopy(dict(candidate))

"""Controller-scoped, deterministic military-tradition progression.

All balance and category names are supplied by scenario data.  Experience and
continuous modifiers use integers and rational coefficients so replays, remote
commands, checkpoints, and inactive-region simulation cannot diverge because
of floating-point or Warcraft-object state.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Mapping, Protocol, Sequence

STATE_VERSION = 2
WORLD_STATE_KEY = "militaryTraditionState"
_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class TraditionError(ValueError):
    """A definition, state, or atomic progression operation was rejected."""


class TraditionRuntimeAdapter(Protocol):
    def replace_tradition_layer(self, unit_id: str, modifiers: Mapping[str, Fraction], effects: Sequence[str]) -> None: ...
    def remove_tradition_layer(self, unit_id: str) -> None: ...


class RecordingTraditionAdapter:
    """Headless adapter.  Its named layer deliberately leaves other effects alone."""

    def __init__(self) -> None:
        self.layers: dict[str, dict[str, Any]] = {}
        self.unrelated_effects: dict[str, Any] = {}
        self.operations: list[tuple[Any, ...]] = []

    def replace_tradition_layer(self, unit_id: str, modifiers: Mapping[str, Fraction], effects: Sequence[str]) -> None:
        layer = {"modifiers": dict(modifiers), "effects": list(effects)}
        self.layers[unit_id] = copy.deepcopy(layer)
        self.operations.append(("replace", unit_id, copy.deepcopy(layer)))

    def remove_tradition_layer(self, unit_id: str) -> None:
        self.layers.pop(unit_id, None)
        self.operations.append(("remove", unit_id))


@dataclass(frozen=True)
class TraditionView:
    controller_id: str
    category_id: str
    experience: int
    modifiers: Mapping[str, Fraction]
    effects: tuple[str, ...]


def _ident(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise TraditionError(f"{context}: invalid stable ID {value!r}")
    return value


def _integer(value: Any, context: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise TraditionError(f"{context}: must be an integer >= {minimum}")
    return value


def _index(values: Any, context: str) -> dict[str, Mapping[str, Any]]:
    if not isinstance(values, list):
        raise TraditionError(f"{context}: must be an array")
    result = {}
    for value in values:
        if not isinstance(value, Mapping):
            raise TraditionError(f"{context}: entries must be objects")
        ident = _ident(value.get("id"), f"{context}.id")
        if ident in result:
            raise TraditionError(f"{context}: duplicate ID {ident!r}")
        result[ident] = copy.deepcopy(dict(value))
    return result


class MilitaryTraditionRuntime:
    """Authoritative controller/category state and reconstructible modifier layers."""

    def __init__(self, definitions: Mapping[str, Any], adapter: TraditionRuntimeAdapter) -> None:
        if not isinstance(definitions, Mapping):
            raise TraditionError("tradition definitions must be an object")
        self._adapter = adapter
        raw_controllers = definitions.get("eligibleControllerIds", [])
        if not isinstance(raw_controllers, list):
            raise TraditionError("eligibleControllerIds must be an array")
        self._controllers = set(_ident(x, "eligibleControllerIds") for x in raw_controllers)
        if len(self._controllers) != len(raw_controllers):
            raise TraditionError("eligibleControllerIds contains a duplicate")
        if not self._controllers:
            raise TraditionError("eligibleControllerIds must not be empty")
        self._categories = _index(definitions.get("categories"), "categories")
        self._sources = _index(definitions.get("experienceSources"), "experienceSources")
        self._traditions = _index(definitions.get("traditions"), "traditions")
        self._units = _index(definitions.get("unitAssignments"), "unitAssignments")
        self._validate_definitions()
        self._state = {"schemaVersion": STATE_VERSION, "tracks": [
            {"controllerId": controller, "categoryId": category, "experience": self._starting(category)}
            for controller in sorted(self._controllers) for category in sorted(self._categories)
        ]}
        self._active: set[str] = set()

    def _validate_definitions(self) -> None:
        for category_id, category in self._categories.items():
            if set(category) != {"id", "name"} or not isinstance(category.get("name"), str) or not category["name"].strip():
                raise TraditionError(f"category {category_id}: invalid fields or name")
        for source_id, source in self._sources.items():
            if set(source) != {"id", "weightNumerator", "weightDenominator"}:
                raise TraditionError(f"experience source {source_id}: invalid fields")
            _integer(source.get("weightNumerator"), f"experience source {source_id}.weightNumerator", 1)
            _integer(source.get("weightDenominator"), f"experience source {source_id}.weightDenominator", 1)
        seen_categories = set()
        for tradition_id, tradition in self._traditions.items():
            required = {"id", "categoryId", "startingExperience", "coefficients", "milestones"}
            if set(tradition) != required:
                raise TraditionError(f"tradition {tradition_id}: invalid fields")
            category = _ident(tradition.get("categoryId"), f"tradition {tradition_id}.categoryId")
            if category not in self._categories or category in seen_categories:
                raise TraditionError(f"tradition {tradition_id}: unknown or duplicate category")
            seen_categories.add(category)
            _integer(tradition.get("startingExperience"), f"tradition {tradition_id}.startingExperience")
            coefficients = tradition.get("coefficients")
            if not isinstance(coefficients, list) or not coefficients:
                raise TraditionError(f"tradition {tradition_id}: coefficients must not be empty")
            attrs = set()
            for coefficient in coefficients:
                if not isinstance(coefficient, Mapping) or set(coefficient) != {"attributeId", "numerator", "denominator"}:
                    raise TraditionError(f"tradition {tradition_id}: malformed coefficient")
                attribute = _ident(coefficient.get("attributeId"), "attributeId")
                if attribute in attrs:
                    raise TraditionError(f"tradition {tradition_id}: duplicate attribute {attribute!r}")
                attrs.add(attribute)
                if isinstance(coefficient.get("numerator"), bool) or not isinstance(coefficient.get("numerator"), int):
                    raise TraditionError("coefficient numerator must be an integer")
                _integer(coefficient.get("denominator"), "coefficient denominator", 1)
            thresholds, milestone_ids, effect_ids = set(), set(), set()
            milestones = tradition.get("milestones")
            if not isinstance(milestones, list):
                raise TraditionError(f"tradition {tradition_id}: milestones must be an array")
            for milestone in milestones:
                if not isinstance(milestone, Mapping) or set(milestone) != {"id", "threshold", "effect"}:
                    raise TraditionError(f"tradition {tradition_id}: malformed milestone")
                milestone_id = _ident(milestone.get("id"), "milestone.id")
                threshold = _integer(milestone.get("threshold"), "milestone.threshold", 1)
                effect = milestone.get("effect")
                if threshold in thresholds or milestone_id in milestone_ids or not isinstance(effect, Mapping) or set(effect) != {"effectId", "mode", "replacesEffectId"}:
                    raise TraditionError(f"tradition {tradition_id}: duplicate threshold or malformed effect")
                thresholds.add(threshold)
                milestone_ids.add(milestone_id)
                effect_id = _ident(effect.get("effectId"), "effect.effectId")
                mode, replaced = effect.get("mode"), effect.get("replacesEffectId")
                if effect_id in effect_ids or mode not in {"additive", "upgrade", "replacement"}:
                    raise TraditionError(f"tradition {tradition_id}: invalid or duplicate milestone effect")
                if mode == "additive" and replaced is not None:
                    raise TraditionError("additive milestone cannot replace an effect")
                if mode != "additive":
                    replaced = _ident(replaced, "effect.replacesEffectId")
                    if replaced not in effect_ids:
                        raise TraditionError(f"tradition {tradition_id}: replacement must name an earlier effect")
                effect_ids.add(effect_id)
        if seen_categories != set(self._categories):
            raise TraditionError("every category must have exactly one tradition")
        for unit_id, unit in self._units.items():
            if set(unit) != {"id", "controllerId", "categoryId"}:
                raise TraditionError(f"unit assignment {unit_id}: invalid fields")
            if unit.get("controllerId") not in self._controllers or unit.get("categoryId") not in self._categories:
                raise TraditionError(f"unit assignment {unit_id}: incompatible controller or category")

    def _tradition(self, category_id: str) -> Mapping[str, Any]:
        return next(x for x in self._traditions.values() if x["categoryId"] == category_id)

    def _starting(self, category_id: str) -> int:
        return self._tradition(category_id)["startingExperience"]

    def validate_snapshot(self, candidate: Any) -> dict[str, Any]:
        if not isinstance(candidate, Mapping) or set(candidate) != {"schemaVersion", "tracks"} or type(candidate.get("schemaVersion")) is not int or candidate["schemaVersion"] not in (1, STATE_VERSION):
            raise TraditionError("tradition state must use schemaVersion 1 or 2 and contain tracks")
        tracks, result, seen = candidate.get("tracks"), [], set()
        if not isinstance(tracks, list):
            raise TraditionError("tradition tracks must be an array")
        for track in tracks:
            if not isinstance(track, Mapping) or set(track) != {"controllerId", "categoryId", "experience"}:
                raise TraditionError("malformed tradition track")
            controller = _ident(track.get("controllerId"), "track.controllerId")
            category = _ident(track.get("categoryId"), "track.categoryId")
            key = (controller, category)
            if controller not in self._controllers or category not in self._categories or key in seen:
                raise TraditionError("unknown or duplicate tradition track")
            seen.add(key)
            result.append({"controllerId": controller, "categoryId": category,
                           "experience": _integer(track.get("experience"), "track.experience")})
        expected = {(c, k) for c in self._controllers for k in self._categories}
        # v1 scenarios omitted the independent player controller. Preserve all
        # polity experience; only the newly supported player tracks are seeded.
        if candidate["schemaVersion"] == 1:
            for controller, category in sorted(expected - seen):
                if controller == "player":
                    result.append({"controllerId": controller, "categoryId": category,
                                   "experience": self._starting(category)})
                    seen.add((controller, category))
        if seen != expected:
            raise TraditionError("tradition state must cover every eligible controller/category")
        return {"schemaVersion": STATE_VERSION, "tracks": sorted(result, key=lambda x: (x["controllerId"], x["categoryId"]))}

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    def view(self, controller_id: str, category_id: str) -> TraditionView:
        track = self._track(controller_id, category_id)
        modifiers, effects = self._resolve(category_id, track["experience"])
        return TraditionView(controller_id, category_id, track["experience"], modifiers, effects)

    def _track(self, controller_id: str, category_id: str, state: Mapping[str, Any] | None = None) -> dict[str, Any]:
        state = state or self._state
        found = next((x for x in state["tracks"] if x["controllerId"] == controller_id and x["categoryId"] == category_id), None)
        if found is None:
            raise TraditionError(f"unknown controller/category track {controller_id!r}/{category_id!r}")
        return found

    def _resolve(self, category_id: str, experience: int) -> tuple[dict[str, Fraction], tuple[str, ...]]:
        tradition = self._tradition(category_id)
        modifiers = {x["attributeId"]: Fraction(experience * x["numerator"], x["denominator"])
                     for x in tradition["coefficients"]}
        effects: list[str] = []
        for milestone in sorted(tradition["milestones"], key=lambda x: (x["threshold"], x["id"])):
            if milestone["threshold"] > experience:
                continue
            effect = milestone["effect"]
            if effect["mode"] != "additive":
                if effect["replacesEffectId"] in effects:
                    effects.remove(effect["replacesEffectId"])
            effects.append(effect["effectId"])
        return modifiers, tuple(effects)

    def award(self, contributions: Sequence[Mapping[str, Any]]) -> int:
        """Atomically validate and award a batch; aggregation makes ordering irrelevant."""
        if not isinstance(contributions, Sequence) or isinstance(contributions, (str, bytes)) or not contributions:
            raise TraditionError("contributions must be a non-empty sequence")
        totals: dict[tuple[str, str], int] = {}
        for item in contributions:
            if not isinstance(item, Mapping) or set(item) != {"sourceId", "unitId", "enemyControllerId", "amount"}:
                raise TraditionError("malformed combat contribution")
            source_id = _ident(item.get("sourceId"), "contribution.sourceId")
            unit_id = _ident(item.get("unitId"), "contribution.unitId")
            enemy = _ident(item.get("enemyControllerId"), "contribution.enemyControllerId")
            if source_id not in self._sources or unit_id not in self._units or enemy not in self._controllers:
                raise TraditionError("unknown contribution source, unit, or enemy controller")
            unit, source = self._units[unit_id], self._sources[source_id]
            if enemy == unit["controllerId"]:
                raise TraditionError("combat contribution requires an enemy controller")
            amount = _integer(item.get("amount"), "contribution.amount", 1)
            weighted = amount * source["weightNumerator"] // source["weightDenominator"]
            if weighted < 1:
                raise TraditionError("combat contribution rounds to zero experience")
            key = unit["controllerId"], unit["categoryId"]
            totals[key] = totals.get(key, 0) + weighted
        candidate = self.snapshot()
        for key, amount in totals.items():
            self._track(*key, state=candidate)["experience"] += amount
        candidate = self.validate_snapshot(candidate)
        self._state = candidate
        for controller, category in sorted(totals):
            for unit_id, unit in self._units.items():
                if unit["controllerId"] == controller and unit["categoryId"] == category and unit_id in self._active:
                    self._apply(unit_id)
        return sum(totals.values())

    def change_unit(self, unit_id: str, *, controller_id: str | None = None, category_id: str | None = None) -> bool:
        if unit_id not in self._units:
            raise TraditionError(f"unknown unit {unit_id!r}")
        unit = self._units[unit_id]
        controller, category = controller_id or unit["controllerId"], category_id or unit["categoryId"]
        if controller not in self._controllers or category not in self._categories:
            raise TraditionError("unknown unit controller or category")
        changed = (controller, category) != (unit["controllerId"], unit["categoryId"])
        if changed:
            previous = unit["controllerId"], unit["categoryId"]
            unit["controllerId"], unit["categoryId"] = controller, category
            try:
                if unit_id in self._active:
                    self._apply(unit_id)
            except Exception:
                unit["controllerId"], unit["categoryId"] = previous
                raise
        return changed

    def _apply(self, unit_id: str) -> None:
        unit = self._units[unit_id]
        view = self.view(unit["controllerId"], unit["categoryId"])
        self._adapter.replace_tradition_layer(unit_id, view.modifiers, view.effects)

    def set_runtime_active(self, unit_id: str, active: bool) -> bool:
        if unit_id not in self._units or not isinstance(active, bool):
            raise TraditionError("unknown unit or invalid runtime-active flag")
        changed = (unit_id in self._active) != active
        if active:
            self._active.add(unit_id); self._apply(unit_id)
        else:
            self._active.discard(unit_id); self._adapter.remove_tradition_layer(unit_id)
        return changed

    def reconstruct(self, active_unit_ids: Sequence[str]) -> None:
        requested = set(active_unit_ids)
        if any(x not in self._units for x in requested):
            raise TraditionError("cannot reconstruct unknown unit")
        for unit_id in sorted(self._active - requested):
            self._adapter.remove_tradition_layer(unit_id)
        self._active = requested
        for unit_id in sorted(requested):
            self._apply(unit_id)

    def restore(self, candidate: Any, active_unit_ids: Sequence[str] | None = None) -> None:
        validated = self.validate_snapshot(candidate)
        old = self._state
        self._state = validated
        try:
            self.reconstruct(sorted(self._active) if active_unit_ids is None else active_unit_ids)
        except Exception:
            self._state = old
            raise


class MilitaryTraditionSaveAdapter:
    def __init__(self, runtime: MilitaryTraditionRuntime, world_state: Mapping[str, Any]):
        self.runtime, self.world_state = runtime, copy.deepcopy(dict(world_state))

    def capture_world(self) -> dict[str, Any]:
        result = copy.deepcopy(self.world_state); result[WORLD_STATE_KEY] = self.runtime.snapshot(); return result

    def migrate_legacy_world(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        result = copy.deepcopy(dict(candidate)); result.setdefault(WORLD_STATE_KEY, self.runtime.snapshot()); self.validate_world(result); return result

    def validate_world(self, candidate: Mapping[str, Any]) -> None:
        if not isinstance(candidate, Mapping) or WORLD_STATE_KEY not in candidate:
            raise TraditionError(f"world state is missing {WORLD_STATE_KEY}")
        self.runtime.validate_snapshot(candidate[WORLD_STATE_KEY])

    def reconstruct(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        self.validate_world(candidate); return self.runtime.validate_snapshot(candidate[WORLD_STATE_KEY])

    def activate(self, candidate: Mapping[str, Any], reconstructed: Mapping[str, Any]) -> None:
        expected = self.runtime.validate_snapshot(candidate[WORLD_STATE_KEY])
        if dict(reconstructed) != expected:
            raise TraditionError("reconstructed tradition state does not match candidate")
        self.runtime.restore(expected); self.world_state = copy.deepcopy(dict(candidate))

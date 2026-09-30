"""Declarative availability and authoritative-location projection for characters."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import date
from typing import Mapping


class CharacterAvailabilityError(ValueError):
    pass


@dataclass(frozen=True)
class AvailabilityResult:
    character_id: str
    available: bool
    location_id: str | None
    reason: str


class CharacterAvailabilityRuntime:
    """Keeps identity/location outside Warcraft objects and projects local presence."""

    def __init__(self, definitions):
        self._definitions = {x["id"]: copy.deepcopy(x) for x in definitions}
        if len(self._definitions) != len(definitions):
            raise CharacterAvailabilityError("duplicate character identity")
        self._state = {
            ident: {"id": ident, "authoritativeLocationId": value["locationRules"][0]["locationId"],
                    "available": False, "suppressionReason": "not_evaluated"}
            for ident, value in self._definitions.items()
        }

    @staticmethod
    def _condition(value, context):
        kind, expected = value["kind"], value.get("id")
        if kind == "settlement_controlled_by":
            return context.get("settlementControllers", {}).get(value["settlementId"]) == value["polityId"]
        if kind == "settlement_exists":
            return value["settlementId"] not in set(context.get("destroyedSettlementIds", ()))
        if kind == "settlement_rebuilt":
            return value["settlementId"] in set(context.get("rebuiltSettlementIds", ()))
        if kind == "region_active": return expected in set(context.get("activeRegionIds", ()))
        if kind == "polity_active": return expected in set(context.get("activePolityIds", ()))
        collections = {"discovery": "discoveryIds", "event": "eventIds", "quest": "questIds",
                       "technology": "technologyIds"}
        if kind in collections: return expected in set(context.get(collections[kind], ()))
        raise CharacterAvailabilityError(f"unknown condition kind {kind!r}")

    @classmethod
    def _conditions(cls, values, context):
        return all(cls._condition(x, context) != x.get("negated", False) for x in values)

    def evaluate(self, character_id, context):
        value = self._definitions[character_id]
        current = date.fromisoformat(context["date"])
        window = value["availabilityWindow"]
        if not date.fromisoformat(window["startDate"]) <= current <= date.fromisoformat(window["endDate"]):
            return AvailabilityResult(character_id, False, None, "outside_date_window")
        if not self._conditions(value.get("availabilityConditions", ()), context):
            return AvailabilityResult(character_id, False, None, "conditions_not_met")
        for rule in sorted(value["locationRules"], key=lambda x: (-x["priority"], x["locationId"])):
            if self._conditions(rule.get("conditions", ()), context):
                return AvailabilityResult(character_id, True, rule["locationId"], "available")
        return AvailabilityResult(character_id, False, None, "no_valid_location")

    def refresh(self, context, character_state=None):
        """Refresh non-recruited projections; recruited/oathbound identity remains authoritative."""
        character_state = character_state or {}
        results = []
        for ident in sorted(self._definitions):
            mutable = character_state.get(ident, {})
            if mutable.get("recruited") or mutable.get("permanentState") == "oathbound":
                state = self._state[ident]
                results.append(AvailabilityResult(ident, True, state["authoritativeLocationId"], "retained_companion"))
                continue
            result = self.evaluate(ident, context)
            state = self._state[ident]
            state["available"], state["suppressionReason"] = result.available, result.reason
            if result.location_id is not None: state["authoritativeLocationId"] = result.location_id
            results.append(result)
        return tuple(results)

    def project_region(self, region_id, settlement_regions):
        return tuple(sorted(x["id"] for x in self._state.values()
                            if x["available"] and settlement_regions.get(x["authoritativeLocationId"]) == region_id))

    def snapshot(self):
        return {"schemaVersion": 1, "characters": copy.deepcopy([self._state[x] for x in sorted(self._state)])}

    def restore(self, snapshot):
        if snapshot.get("schemaVersion") != 1: raise CharacterAvailabilityError("invalid availability state version")
        records = snapshot.get("characters")
        if not isinstance(records, list) or {x.get("id") for x in records} != set(self._definitions):
            raise CharacterAvailabilityError("availability state identities are incompatible")
        candidate = {}
        for value in records:
            if set(value) != {"id", "authoritativeLocationId", "available", "suppressionReason"}:
                raise CharacterAvailabilityError("invalid availability state fields")
            candidate[value["id"]] = copy.deepcopy(value)
        self._state = candidate

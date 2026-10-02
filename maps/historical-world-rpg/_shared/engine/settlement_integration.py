"""Release-scale settlement integration and bounded local projection runtime.

The manifest consumed here is deliberately scenario-owned.  This engine only
enforces the generic invariant that every settlement is authoritative while
Warcraft objects are disposable, locally bounded projections.
"""
from __future__ import annotations

import copy
import hashlib
from typing import Mapping

INTEGRATION_STATE_VERSION = 1
INTEGRATION_WORLD_STATE_KEY = "settlementIntegrationState"


class SettlementIntegrationError(ValueError):
    pass


REQUIRED_ROLES = frozenset({
    "administration", "defense", "economy", "services", "visuals", "discovery",
    "routes", "physicalMap", "persistence", "quests", "events", "characters",
    "technology", "institutions", "ai", "diplomacy", "war", "capture",
    "historicalLocations",
})


def validate_manifest(source):
    if not isinstance(source, Mapping) or source.get("schemaVersion") != 1:
        raise SettlementIntegrationError("integration manifest schemaVersion must be 1")
    rows = source.get("settlements")
    if not isinstance(rows, list) or not rows:
        raise SettlementIntegrationError("integration manifest requires settlements")
    indexed = {}
    for row in rows:
        sid = row.get("settlementId")
        if not isinstance(sid, str) or not sid or sid in indexed:
            raise SettlementIntegrationError(f"duplicate or invalid settlement {sid!r}")
        roles = row.get("gameplayRoles", {})
        missing = REQUIRED_ROLES - set(roles)
        if missing:
            raise SettlementIntegrationError(f"{sid}: missing gameplay roles: {', '.join(sorted(missing))}")
        unresolved = [key for key, value in roles.items() if not isinstance(value, Mapping) or not value.get("modelId")]
        if unresolved:
            raise SettlementIntegrationError(f"{sid}: unresolved gameplay roles: {', '.join(sorted(unresolved))}")
        if row.get("runtimePolicy") != "authoritative_abstract_reconstruct_on_demand":
            raise SettlementIntegrationError(f"{sid}: invalid runtime policy")
        economy = row.get("economy", {})
        if not economy.get("availableGoodIds") or economy.get("storageCapacityUnits", 0) <= 0:
            raise SettlementIntegrationError(f"{sid}: impossible market")
        if not row.get("official", {}).get("characterId") or not row.get("defense", {}).get("profileId"):
            raise SettlementIntegrationError(f"{sid}: missing official or defense profile")
        indexed[sid] = copy.deepcopy(row)
    return indexed


class SettlementIntegrationRuntime:
    """Persistent abstract state plus a strict, region-local representation cache."""

    def __init__(self, manifest, *, maximum_active_objects=None):
        self.definitions = validate_manifest(manifest)
        budget = manifest.get("performanceBudgets", {}).get("maximumActiveSettlementObjects", 512)
        self.maximum_active_objects = int(maximum_active_objects or budget)
        if self.maximum_active_objects < 1:
            raise SettlementIntegrationError("maximum active objects must be positive")
        self.state = {}
        for sid, row in self.definitions.items():
            self.state[sid] = {
                "settlementId": sid, "legalOwnerPolityId": row["legalOwnerPolityId"],
                "controllerPolityId": row["controllerPolityId"], "officialCharacterId": row["official"]["characterId"],
                "defenseProfileId": row["defense"]["profileId"], "market": copy.deepcopy(row["economy"]),
                "growthPermille": 1000, "blockaded": False, "isolated": False,
                "captureCount": 0, "revision": 0,
            }
        self.active_region_id = None
        self._objects = {}

    def activate(self, region_id, factory):
        self.retire()
        candidates = sorted(sid for sid, row in self.definitions.items() if row["regionId"] == region_id)
        specs = []
        for sid in candidates:
            row = self.definitions[sid]
            specs.extend((sid, kind) for kind in row["physicalRepresentationKinds"])
        if len(specs) > self.maximum_active_objects:
            raise SettlementIntegrationError("active settlement object budget exceeded")
        made = {}
        try:
            for sid, kind in specs:
                key = f"{sid}:{kind}"
                made[key] = factory(sid, kind, copy.deepcopy(self.state[sid]))
        except Exception:
            for handle in made.values():
                close = getattr(handle, "destroy", None)
                if close: close()
            raise
        self.active_region_id, self._objects = region_id, made
        return copy.copy(made)

    def retire(self, destroy=None):
        for handle in self._objects.values():
            if destroy: destroy(handle)
            elif hasattr(handle, "destroy"): handle.destroy()
        self._objects = {}; self.active_region_id = None

    @property
    def active_object_count(self):
        return len(self._objects)

    def capture(self, settlement_id, controller_polity_id):
        row, state = self.definitions[settlement_id], self.state[settlement_id]
        if row["captureModel"] == "non_capturable":
            raise SettlementIntegrationError("settlement uses a validated non-capturable model")
        state["controllerPolityId"] = controller_polity_id
        state["captureCount"] += 1; state["revision"] += 1
        # Generated replacements are stable for a capture sequence and persist in saves.
        digest = hashlib.sha256(f"{settlement_id}|{controller_polity_id}|{state['captureCount']}".encode()).hexdigest()[:12]
        state["officialCharacterId"] = f"official_{settlement_id}_{digest}"
        return copy.deepcopy(state)

    def simulate(self, settlement_id, condition, days):
        if condition not in {"peaceful", "wartime", "captured", "blockaded", "isolated", "growing", "inactive"}:
            raise SettlementIntegrationError("unknown simulation condition")
        state = self.state[settlement_id]; days = max(0, int(days))
        state["blockaded"] = condition == "blockaded"; state["isolated"] = condition == "isolated"
        delta = {"peaceful": 1, "wartime": -2, "captured": -3, "blockaded": -4,
                 "isolated": -2, "growing": 4, "inactive": 0}[condition] * days
        state["growthPermille"] = max(250, min(2000, state["growthPermille"] + delta))
        state["revision"] += 1
        return copy.deepcopy(state)

    def snapshot(self):
        return {"schemaVersion": INTEGRATION_STATE_VERSION, "settlements": copy.deepcopy(self.state)}

    def restore(self, snapshot):
        if snapshot.get("schemaVersion") != INTEGRATION_STATE_VERSION:
            raise SettlementIntegrationError("unsupported integration state version")
        incoming = snapshot.get("settlements", {})
        unknown = set(incoming) - set(self.state)
        if unknown: raise SettlementIntegrationError("save references unknown settlements")
        # Missing records recover from catalogue defaults, supporting old saves transactionally.
        candidate = copy.deepcopy(self.state)
        for sid, state in incoming.items():
            if state.get("settlementId") != sid: raise SettlementIntegrationError("corrupt settlement state")
            candidate[sid] = copy.deepcopy(state)
        self.state = candidate


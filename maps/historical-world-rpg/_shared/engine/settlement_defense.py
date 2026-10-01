"""Authoritative settlement garrisons and transient local-defense forces.

The campaign record is the source of truth.  Warcraft units are protected projections:
creating or destroying them never creates strength, manpower, or supply.  This module is
scenario-neutral; unit choice and all timing/cost limits come from definitions.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

DEFENSE_STATE_SCHEMA_VERSION = 1
DEFENSE_WORLD_STATE_KEY = "settlementDefenseState"
_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
PROHIBITED_ACTIONS = frozenset({"command", "transfer", "embark", "loot", "disband", "sell", "inventory", "cargo"})


class SettlementDefenseError(ValueError): pass


def _id(value, context):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise SettlementDefenseError(f"{context}: invalid stable ID {value!r}")
    return value


def _amount(value, context, low=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < low:
        raise SettlementDefenseError(f"{context}: must be an integer >= {low}")
    return value


class DefenseAdapter(Protocol):
    def spawn(self, settlement_id: str, specification: Mapping[str, Any]) -> Any: ...
    def destroy(self, handle: Any) -> None: ...


class RecordingDefenseAdapter:
    def __init__(self): self.operations, self._serial = [], 0
    def spawn(self, settlement_id, specification):
        self._serial += 1; handle = f"defender_{self._serial}"
        self.operations.append(("spawn", settlement_id, copy.deepcopy(dict(specification)), handle)); return handle
    def destroy(self, handle): self.operations.append(("destroy", handle))


@dataclass(frozen=True)
class DefenseUnit:
    id: str
    settlement_id: str
    archetype_id: str
    strength: int
    manpower: int
    supply: int
    owner_polity_id: str
    commander_character_id: str | None
    runtime_handle: Any


class DefenseResolver:
    """Select qualitative composition from ordered, data-owned eligibility rules."""
    def __init__(self, definitions, roster_catalog=None):
        self.definitions = validate_definitions(definitions); self.roster = roster_catalog

    @staticmethod
    def _matches(rule, context):
        for key, value in rule.get("when", {}).items():
            actual = context.get(key)
            if key == "yearAtLeast" and context.get("year", 0) < value: return False
            elif key == "yearAtMost" and context.get("year", 0) > value: return False
            elif key.endswith("IdsAny"):
                source = set(context.get(key[:-3], ()))
                if not source.intersection(value): return False
            elif key.endswith("IdsAll"):
                source = set(context.get(key[:-3], ()))
                if not set(value) <= source: return False
            elif key not in {"yearAtLeast", "yearAtMost"} and not key.endswith(("IdsAny", "IdsAll")) and actual != value:
                return False
        return True

    def resolve(self, context):
        profile_id = context.get("profileId", self.definitions["defaultProfileId"])
        profile = self.definitions["profiles"][profile_id]
        candidates = list(profile["composition"])
        qualitative = set(profile.get("behaviorIds", ()))
        for rule in self.definitions["resolverRules"]:
            if self._matches(rule, context):
                candidates.extend(rule.get("addComposition", ()))
                candidates = [x for x in candidates if x["archetypeId"] not in set(rule.get("removeArchetypeIds", ()))]
                qualitative.update(rule.get("behaviorIds", ()))
        if self.roster is not None:
            available = set(self.roster.resolve_roster(
                {x["archetypeId"] for x in candidates}, context["year"], set(context.get("technologyIds", ())),
                country_id=context.get("polityId"), established_institution_ids=set(context.get("institutionIds", ())),
                equipment_ids=set(context.get("equipmentIds", ())), reform_ids=set(context.get("reformIds", ())),
                resource_ids=set(context.get("resourceIds", ())), has_port=bool(context.get("hasPort", False))))
            candidates = [x for x in candidates if x["archetypeId"] in available]
        if not candidates: raise SettlementDefenseError("resolver produced no eligible defenders")
        # Duplicate additions merge deterministically, allowing a rule to change emphasis.
        weights = {}
        for item in candidates: weights[item["archetypeId"]] = weights.get(item["archetypeId"], 0) + item["weight"]
        quality = max(0, min(100, profile["baseQuality"] + int(context.get("qualityModifier", 0))
            + int(context.get("administratorCommand", 0)) // 10 - int(context.get("unrest", 0)) // 5
            - int(context.get("recentConquestPenalty", 0))))
        return {"profileId": profile_id, "composition": [{"archetypeId": x, "weight": weights[x]} for x in sorted(weights)],
                "quality": quality, "behaviorIds": sorted(qualitative)}


def validate_definitions(source):
    if not isinstance(source, Mapping) or source.get("schemaVersion") != 1: raise SettlementDefenseError("defense definitions schemaVersion must be 1")
    result = copy.deepcopy(dict(source)); rules = result.get("rules", {})
    for key in ("reinforcementIntervalSeconds", "quietPeriodSeconds", "strengthPerUnit", "manpowerPerStrength", "supplyPerStrength", "replenishmentIntervalDays", "replenishmentStrength"):
        _amount(rules.get(key), f"rules.{key}", 1)
    profiles = {}
    for row in result.get("profiles", ()):
        ident = _id(row.get("id"), "profile.id")
        if ident in profiles: raise SettlementDefenseError("duplicate defense profile")
        _amount(row.get("baseQuality"), f"profile {ident}.baseQuality")
        if row["baseQuality"] > 100 or not row.get("composition"): raise SettlementDefenseError(f"profile {ident}: invalid quality or composition")
        for item in row["composition"]: _id(item.get("archetypeId"), "composition.archetypeId"); _amount(item.get("weight"), "composition.weight", 1)
        profiles[ident] = row
    default = _id(result.get("defaultProfileId"), "defaultProfileId")
    if default not in profiles: raise SettlementDefenseError("missing default defense profile")
    result["profiles"] = profiles
    if not isinstance(result.get("resolverRules", []), list): raise SettlementDefenseError("resolverRules must be an array")
    for rule in result["resolverRules"]: _id(rule.get("id"), "resolverRule.id")
    return result


class SettlementDefenseRuntime:
    """Garrison lifecycle with resource accounting and protected AI projections."""
    def __init__(self, definitions, settlements, adapter: DefenseAdapter, *, roster_catalog=None, administration=None):
        self.definitions = validate_definitions(definitions); self.rules = self.definitions["rules"]
        self.settlements, self.adapter, self.administration = settlements, adapter, administration
        self.resolver = DefenseResolver(definitions, roster_catalog)
        initial = {x["settlementId"]: x for x in self.definitions.get("initialGarrisons", ())}
        self._state, self._units, self._handles = {}, {}, {}
        for sid in settlements.ids():
            row = initial.get(sid, {})
            available = _amount(row.get("availableStrength", 0), f"{sid}.availableStrength")
            self._state[sid] = {"settlementId": sid, "availableStrength": available,
                "manpower": _amount(row.get("manpower", available), f"{sid}.manpower"),
                "reserves": _amount(row.get("reserves", 0), f"{sid}.reserves"),
                "supply": _amount(row.get("supply", available), f"{sid}.supply"),
                "casualties": _amount(row.get("casualties", 0), f"{sid}.casualties"),
                "readiness": _amount(row.get("readiness", 50), f"{sid}.readiness"),
                "profileId": row.get("profileId", self.definitions["defaultProfileId"]),
                "composition": copy.deepcopy(row.get("composition", [])), "quality": row.get("quality", 50),
                "behaviorIds": copy.deepcopy(row.get("behaviorIds", [])), "administratorCharacterId": row.get("administratorCharacterId"),
                "commanderCharacterId": None, "commanderKind": "local", "attack": None,
                "lastCombatSecond": None, "nextReinforcementSecond": None, "lastReplenishmentDay": row.get("lastReplenishmentDay", 0),
                "deployedUnits": []}

    def _s(self, sid):
        if sid not in self._state: raise SettlementDefenseError(f"unknown settlement {sid!r}")
        return self._state[sid]

    def resolve(self, sid, context):
        state = self._s(sid); resolved = self.resolver.resolve(context)
        state.update(copy.deepcopy(resolved)); return copy.deepcopy(resolved)

    def _resident_administrator(self, sid):
        if self.administration is None: return None
        for office in self.administration.offices.values():
            typ = self.administration.office_types.get(office.get("officeTypeId"), {})
            if typ.get("role") == "settlement_administrator" and sid in office.get("jurisdictionIds", ()) and office.get("status") == "active":
                holder = office.get("holderCharacterId")
                if holder and office.get("residenceSettlementId") == sid: return holder
        return None

    def start_attack(self, sid, *, attacker_polity_id, conflict_id, now_seconds, conflict_validated, context=None):
        """Materialize only after the diplomacy/capture layer validates the attack."""
        if not conflict_validated: raise SettlementDefenseError("attack requires a validated active conflict")
        state = self._s(sid); owner = self.settlements.require(sid).controller_polity_id
        if attacker_polity_id == owner: raise SettlementDefenseError("controller cannot attack its own settlement")
        if state["attack"] is not None:
            if state["attack"]["conflictId"] == conflict_id and state["attack"]["attackerPolityId"] == attacker_polity_id: return tuple(self.units(sid))
            raise SettlementDefenseError("settlement already has an active attack")
        if context is not None: self.resolve(sid, context)
        state["attack"] = {"attackerPolityId": attacker_polity_id, "conflictId": _id(conflict_id, "conflictId"), "startedSecond": float(now_seconds)}
        state["lastCombatSecond"] = float(now_seconds); state["nextReinforcementSecond"] = float(now_seconds) + self.rules["reinforcementIntervalSeconds"]
        resident = self._resident_administrator(sid)
        state["commanderCharacterId"] = resident
        state["commanderKind"] = "administrator" if resident else "acting_deputy"
        self._spawn_available(sid, state["availableStrength"])
        return tuple(self.units(sid))

    def _spawn_available(self, sid, requested):
        state = self._s(sid); unit_strength = self.rules["strengthPerUnit"]
        affordable = min(requested, state["availableStrength"], state["manpower"] // self.rules["manpowerPerStrength"], state["supply"] // self.rules["supplyPerStrength"])
        count_strength = affordable - affordable % unit_strength
        if affordable and not count_strength: count_strength = affordable
        if count_strength <= 0: return 0
        composition = state["composition"] or self.definitions["profiles"][state["profileId"]]["composition"]
        weights = [x for x in composition for _ in range(x["weight"])]
        remaining, serial = count_strength, len(self._units.get(sid, {}))
        while remaining:
            strength = min(unit_strength, remaining); archetype = weights[serial % len(weights)]["archetypeId"]
            uid = f"defense_{sid}_{serial + 1}"
            while uid in self._units.get(sid, {}): serial += 1; uid = f"defense_{sid}_{serial + 1}"
            manpower = strength * self.rules["manpowerPerStrength"]; supply = strength * self.rules["supplyPerStrength"]
            spec = {"unitId": uid, "archetypeId": archetype, "strength": strength, "quality": state["quality"],
                    "ownerPolityId": self.settlements.require(sid).controller_polity_id, "aiControlled": True,
                    "protectedActions": sorted(PROHIBITED_ACTIONS), "commanderCharacterId": state["commanderCharacterId"],
                    "commanderKind": state["commanderKind"], "behaviorIds": state["behaviorIds"]}
            handle = self.adapter.spawn(sid, spec)
            unit = DefenseUnit(uid, sid, archetype, strength, manpower, supply, spec["ownerPolityId"], state["commanderCharacterId"], handle)
            self._units.setdefault(sid, {})[uid] = unit; self._handles[uid] = handle
            state["deployedUnits"].append({"id": uid, "archetypeId": archetype, "strength": strength,
                "manpower": manpower, "supply": supply, "ownerPolityId": spec["ownerPolityId"],
                "commanderCharacterId": state["commanderCharacterId"]})
            remaining -= strength; serial += 1
        state["availableStrength"] -= count_strength; state["manpower"] -= count_strength * self.rules["manpowerPerStrength"]
        state["supply"] -= count_strength * self.rules["supplyPerStrength"]
        return count_strength

    def units(self, sid): return tuple(self._units.get(sid, {}).values())
    def authorize_action(self, unit_id, action):
        if unit_id in self._handles and action in PROHIBITED_ACTIONS: return False
        return unit_id not in self._handles

    def report_casualty(self, unit_id, lost_strength, *, now_seconds):
        lost_strength = _amount(lost_strength, "lostStrength", 1)
        unit = next((u for units in self._units.values() for u in units.values() if u.id == unit_id), None)
        if unit is None: raise SettlementDefenseError("unknown defense unit")
        lost = min(lost_strength, unit.strength); state = self._s(unit.settlement_id)
        state["casualties"] += lost; state["lastCombatSecond"] = float(now_seconds)
        survivor = unit.strength - lost
        if survivor:
            self._units[unit.settlement_id][unit.id] = DefenseUnit(unit.id, unit.settlement_id, unit.archetype_id, survivor,
                max(0, unit.manpower-lost*self.rules["manpowerPerStrength"]), max(0, unit.supply-lost*self.rules["supplyPerStrength"]),
                unit.owner_polity_id, unit.commander_character_id, unit.runtime_handle)
            next(x for x in state["deployedUnits"] if x["id"] == unit.id).update(
                strength=survivor, manpower=max(0, unit.manpower-lost*self.rules["manpowerPerStrength"]),
                supply=max(0, unit.supply-lost*self.rules["supplyPerStrength"]))
        else:
            self.adapter.destroy(unit.runtime_handle); del self._units[unit.settlement_id][unit.id]; self._handles.pop(unit.id, None)
            state["deployedUnits"] = [x for x in state["deployedUnits"] if x["id"] != unit.id]
        return lost

    def mark_combat(self, sid, now_seconds): self._s(sid)["lastCombatSecond"] = float(now_seconds)

    def advance(self, now_seconds):
        now = float(now_seconds)
        for sid in sorted(self._state):
            state = self._state[sid]
            if state["attack"] is not None:
                due = state["nextReinforcementSecond"]
                while due is not None and now >= due:
                    amount = min(self.rules["strengthPerUnit"], state["reserves"])
                    # Transfer bounded reserves into available state; spawn immediately.
                    state["reserves"] -= amount; state["availableStrength"] += amount
                    self._spawn_available(sid, amount); due += self.rules["reinforcementIntervalSeconds"]
                    if amount == 0: due = None
                state["nextReinforcementSecond"] = due
            elif self._units.get(sid) and now - (state["lastCombatSecond"] or 0) >= self.rules["quietPeriodSeconds"]:
                self._abstract_survivors(sid)

    def end_attack(self, sid, now_seconds):
        state = self._s(sid)
        if state["attack"] is None: return False
        state["attack"] = None; state["lastCombatSecond"] = float(now_seconds); state["nextReinforcementSecond"] = None; return True

    def _abstract_survivors(self, sid):
        state = self._s(sid)
        for unit in list(self._units.get(sid, {}).values()):
            state["availableStrength"] += unit.strength
            state["manpower"] += unit.manpower
            state["supply"] += unit.supply
            self.adapter.destroy(unit.runtime_handle); self._handles.pop(unit.id, None)
        self._units.pop(sid, None); state["commanderCharacterId"] = None; state["commanderKind"] = "local"
        state["deployedUnits"] = []

    def retire_region(self, settlement_ids):
        for sid in sorted(set(settlement_ids)): self._abstract_survivors(sid)

    def activate_region(self, settlement_ids):
        """Re-project active local battles after a physical-map transition."""
        for sid in sorted(set(settlement_ids)):
            state = self._s(sid)
            if state["attack"] is not None and not self._units.get(sid): self._spawn_available(sid, state["availableStrength"])

    def replenish(self, sid, *, day, manpower, supply):
        state = self._s(sid)
        if state["attack"] is not None: return 0
        intervals = (int(day) - state["lastReplenishmentDay"]) // self.rules["replenishmentIntervalDays"]
        if intervals <= 0: return 0
        gain = min(intervals*self.rules["replenishmentStrength"], _amount(manpower,"manpower")//self.rules["manpowerPerStrength"], _amount(supply,"supply")//self.rules["supplyPerStrength"], state["casualties"])
        state["availableStrength"] += gain; state["manpower"] += gain*self.rules["manpowerPerStrength"]
        state["supply"] += gain*self.rules["supplyPerStrength"]; state["casualties"] -= gain
        state["lastReplenishmentDay"] += intervals*self.rules["replenishmentIntervalDays"]
        return gain

    def on_capture(self, sid, new_controller_polity_id, now_seconds):
        # Defeated projections never change owners into a free field army.
        state = self._s(sid)
        for unit in list(self._units.get(sid, {}).values()): self.adapter.destroy(unit.runtime_handle); self._handles.pop(unit.id, None)
        self._units.pop(sid, None); state["attack"] = None; state["availableStrength"] = 0; state["reserves"] = 0
        state["manpower"] = 0; state["supply"] = 0; state["readiness"] = 0; state["lastCombatSecond"] = float(now_seconds)
        state["nextReinforcementSecond"] = None; state["commanderCharacterId"] = None; state["commanderKind"] = "local"
        state["deployedUnits"] = []

    def management_status(self, sid):
        state = copy.deepcopy(self._s(sid)); state["activeDefenseStrength"] = sum(x.strength for x in self.units(sid))
        state["aiControlled"] = True; state["directControlAllowed"] = False
        return state

    def snapshot(self): return {"schemaVersion": 1, "garrisons": [copy.deepcopy(self._state[x]) for x in sorted(self._state)]}

    def validate_snapshot(self, candidate):
        if not isinstance(candidate, Mapping) or set(candidate) != {"schemaVersion","garrisons"} or candidate.get("schemaVersion") != 1: raise SettlementDefenseError("defense state must contain schemaVersion 1 and garrisons")
        rows = candidate["garrisons"]
        if not isinstance(rows, list): raise SettlementDefenseError("garrisons must be an array")
        indexed = {}
        for row in rows:
            sid = row.get("settlementId") if isinstance(row, Mapping) else None
            if sid in indexed or sid not in self._state or set(row) != set(self._state[sid]): raise SettlementDefenseError("invalid garrison record")
            for key in ("availableStrength","manpower","reserves","supply","casualties","readiness","quality","lastReplenishmentDay"): _amount(row[key], f"{sid}.{key}")
            if row["readiness"] > 100 or row["quality"] > 100: raise SettlementDefenseError("readiness and quality cannot exceed 100")
            if not isinstance(row["deployedUnits"], list): raise SettlementDefenseError("deployedUnits must be an array")
            seen = set()
            for unit in row["deployedUnits"]:
                if not isinstance(unit, Mapping) or set(unit) != {"id","archetypeId","strength","manpower","supply","ownerPolityId","commanderCharacterId"}: raise SettlementDefenseError("invalid deployed defense unit")
                uid = _id(unit["id"], "deployed unit.id")
                if uid in seen: raise SettlementDefenseError("duplicate deployed defense unit")
                seen.add(uid); _id(unit["archetypeId"], "deployed unit.archetypeId"); _id(unit["ownerPolityId"], "deployed unit.ownerPolityId")
                for key in ("strength","manpower","supply"): _amount(unit[key], f"deployed unit.{key}", 1)
            if row["attack"] is None and row["deployedUnits"]: raise SettlementDefenseError("deployed units require an active attack")
            indexed[sid] = copy.deepcopy(dict(row))
        if set(indexed) != set(self._state): raise SettlementDefenseError("garrison set does not match settlements")
        return indexed

    def restore(self, candidate):
        restored = self.validate_snapshot(candidate)
        for units in self._units.values():
            for unit in units.values(): self.adapter.destroy(unit.runtime_handle)
        self._state, self._units, self._handles = restored, {}, {}
        # Mid-siege saves reconstruct exactly the already committed deployed strength,
        # which is derived from resources absent from abstract availableStrength.
        for sid, state in self._state.items():
            deployed = copy.deepcopy(state["deployedUnits"]); state["deployedUnits"] = []
            for row in deployed:
                spec = {"unitId": row["id"], "archetypeId": row["archetypeId"], "strength": row["strength"],
                    "quality": state["quality"], "ownerPolityId": row["ownerPolityId"], "aiControlled": True,
                    "protectedActions": sorted(PROHIBITED_ACTIONS), "commanderCharacterId": row["commanderCharacterId"],
                    "commanderKind": state["commanderKind"], "behaviorIds": state["behaviorIds"]}
                handle = self.adapter.spawn(sid, spec)
                unit = DefenseUnit(row["id"], sid, row["archetypeId"], row["strength"], row["manpower"], row["supply"],
                    row["ownerPolityId"], row["commanderCharacterId"], handle)
                self._units.setdefault(sid, {})[unit.id] = unit; self._handles[unit.id] = handle
                state["deployedUnits"].append(row)


class SettlementDefenseSaveAdapter:
    def __init__(self, runtime, world_state): self.runtime, self.world_state = runtime, copy.deepcopy(dict(world_state))
    def capture_world(self):
        result=copy.deepcopy(self.world_state); result[DEFENSE_WORLD_STATE_KEY]=self.runtime.snapshot(); return result
    def migrate_legacy_world(self, candidate):
        result=copy.deepcopy(dict(candidate)); result.setdefault(DEFENSE_WORLD_STATE_KEY,self.runtime.snapshot()); self.validate_world(result); return result
    def validate_world(self,candidate):
        if not isinstance(candidate,Mapping) or DEFENSE_WORLD_STATE_KEY not in candidate: raise SettlementDefenseError("world state is missing settlementDefenseState")
        self.runtime.validate_snapshot(candidate[DEFENSE_WORLD_STATE_KEY])
    def reconstruct(self,candidate): self.validate_world(candidate); return copy.deepcopy(candidate[DEFENSE_WORLD_STATE_KEY])
    def activate(self,candidate,reconstructed):
        if reconstructed != candidate[DEFENSE_WORLD_STATE_KEY]: raise SettlementDefenseError("reconstructed defense state mismatch")
        self.runtime.restore(reconstructed); self.world_state=copy.deepcopy(dict(candidate))

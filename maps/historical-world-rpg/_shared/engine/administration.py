"""Authoritative, scenario-neutral political office and administration runtime.

Office state deliberately contains no ownership/controller fields.  It may therefore
be composed with settlement, government and military runtimes without an appointment
silently changing any of them.  Generated officials are durable data records; Warcraft
objects are optional projections of their single ``locationId``.
"""
from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass
from typing import Any, Mapping

ADMINISTRATION_STATE_SCHEMA_VERSION = 1
ADMINISTRATION_WORLD_STATE_KEY = "administrationState"
OFFICE_ROLES = frozenset(("settlement_administrator", "province_governor",
                          "sovereign", "army_commander", "fleet_commander"))
_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class AdministrationError(ValueError): pass


def _id(value, context):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise AdministrationError(f"{context}: invalid stable ID {value!r}")
    return value


def _number(value, context, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise AdministrationError(f"{context}: must be between {low} and {high}")
    return float(value)


def _index(values, context):
    if not isinstance(values, list): raise AdministrationError(f"{context}: must be an array")
    result = {}
    for value in values:
        if not isinstance(value, Mapping): raise AdministrationError(f"{context}: entries must be objects")
        ident = _id(value.get("id"), f"{context}.id")
        if ident in result: raise AdministrationError(f"{context}: duplicate ID {ident!r}")
        result[ident] = copy.deepcopy(dict(value))
    return result


def _pick(seed, label, values):
    digest = hashlib.sha256(f"{seed}|{label}".encode()).digest()
    return values[int.from_bytes(digest[:8], "big") % len(values)]


@dataclass(frozen=True)
class RemovalWarning:
    risky: bool
    risk: float
    outcomes: tuple[str, ...]
    message: str


class AdministrationRuntime:
    """Office lifecycle, capacity/effects, succession and deterministic officials."""

    def __init__(self, definitions, *, character_runtime=None, campaign_seed="campaign"):
        world = copy.deepcopy(dict(definitions)); self.characters = character_runtime
        self.seed = str(campaign_seed)
        self.settlements = _index(world.get("settlements", []), "settlements")
        self.provinces = _index(world.get("provinces", []), "provinces")
        self.polities = _index(world.get("polities", []), "polities")
        self.cultures = _index(world.get("officeNameCultures", []), "officeNameCultures")
        self.office_types = _index(world.get("officeTypes", []), "officeTypes")
        for ident, value in self.office_types.items():
            if value.get("role") not in OFFICE_ROLES: raise AdministrationError(f"office type {ident}: invalid role")
            _number(value.get("baseCapacity", 1), f"office type {ident}.baseCapacity", 1, 1000)
        self.officials = _index(world.get("generatedOfficials", []), "generatedOfficials")
        self.offices = _index(world.get("politicalOffices", []), "politicalOffices")
        self.history = []; self._sequence = 1
        for ident, office in self.offices.items(): self._validate_office(ident, office)
        self.ensure_settlement_administrators(reason="initialization")

    def _known_character(self, ident):
        if ident in self.officials: return True
        if self.characters is None: return False
        try: self.characters.require(ident); return True
        except Exception: return False

    def _character_data(self, ident):
        if ident in self.officials: return self.officials[ident]
        view = self.characters.require(ident)
        return {"id": ident, "displayName": view.definition.display_name,
                "allegiancePolityId": view.allegiance_polity_id, "loyalty": view.loyalty,
                "permanentState": view.permanent_state, "skills": dict(view.skills),
                "traitIds": list(view.trait_ids), "professionIds": list(view.profession_ids),
                "locationId": getattr(view, "location_id", None),
                "titleGrantIds": list(view.definition.title_grant_ids)}

    def _validate_office(self, ident, office):
        type_id = office.get("officeTypeId")
        if type_id not in self.office_types: raise AdministrationError(f"office {ident}: missing office type")
        jurisdictions = office.get("jurisdictionIds")
        if not isinstance(jurisdictions, list) or not jurisdictions: raise AdministrationError(f"office {ident}: jurisdiction required")
        if len(jurisdictions) != len(set(jurisdictions)): raise AdministrationError(f"office {ident}: duplicate jurisdiction")
        role = self.office_types[type_id]["role"]
        catalog = self.settlements if role == "settlement_administrator" else self.provinces if role == "province_governor" else None
        if catalog is not None and any(x not in catalog for x in jurisdictions): raise AdministrationError(f"office {ident}: invalid jurisdiction")
        holder = office.get("holderCharacterId")
        if holder is not None and not self._known_character(holder): raise AdministrationError(f"office {ident}: missing holder {holder!r}")
        office.setdefault("holderCharacterId", None); office.setdefault("acting", False)
        office.setdefault("residenceSettlementId", None); office.setdefault("status", "active")
        office.setdefault("successionState", "settled"); office.setdefault("modifiers", {})
        office.setdefault("localSupport", 0.0); office.setdefault("militaryEntrenchment", 0.0)

    def _culture_for(self, settlement):
        culture = settlement.get("cultureId") or self.polities.get(settlement.get("controllerPolityId"), {}).get("cultureId")
        if culture in self.cultures: return culture
        if "default" in self.cultures: return "default"
        if not self.cultures: raise AdministrationError("officeNameCultures must provide a culture or default pool")
        return sorted(self.cultures)[0]

    def generate_official(self, settlement_id, allegiance_polity_id=None):
        settlement = self.settlements[settlement_id]; culture_id = self._culture_for(settlement)
        pool = self.cultures[culture_id]; seed = f"{self.seed}|{settlement_id}|administrator"
        given = _pick(seed, "given", pool.get("givenNames", ()))
        family = _pick(seed, "family", pool.get("familyNames", ()))
        if not given or not family: raise AdministrationError(f"culture {culture_id}: name pools must be non-empty")
        ident = f"official_{settlement_id}"; suffix = 2
        while ident in self.officials and self.officials[ident].get("originSettlementId") != settlement_id:
            ident = f"official_{settlement_id}_{suffix}"; suffix += 1
        if ident in self.officials: return ident
        raw = hashlib.sha256(seed.encode()).digest()
        rating = lambda offset, base, span: base + raw[offset] % span
        self.officials[ident] = {"id": ident, "displayName": f"{given} {family}",
            "originSettlementId": settlement_id, "cultureId": culture_id,
            "birthYear": 1390 + raw[0] % 36, "lifespanYears": 48 + raw[1] % 34,
            "skills": {"administration": rating(2, 38, 43), "command": rating(3, 15, 36),
                       "engineering": rating(4, 12, 35), "tradecraft": rating(5, 20, 41),
                       "diplomacy": rating(6, 20, 41), "scholarship": rating(7, 18, 43)},
            "traitIds": [_pick(seed, "trait", pool.get("traitIds", ("pragmatic",)))],
            "professionIds": [pool.get("professionId", "administrator")], "titleGrantIds": [],
            "allegiancePolityId": allegiance_polity_id or settlement.get("controllerPolityId"),
            "loyalty": float(35 + raw[8] % 31), "permanentState": "none",
            "locationId": settlement_id, "generated": True, "active": True}
        return ident

    def ensure_settlement_administrators(self, settlement_ids=None, *, reason="vacancy"):
        targets = sorted(settlement_ids or self.settlements)
        made = []
        for sid in targets:
            active = [o for o in self.offices.values() if o["status"] == "active" and
                      self.office_types[o["officeTypeId"]]["role"] == "settlement_administrator" and sid in o["jurisdictionIds"]]
            if any(o.get("holderCharacterId") and self._known_character(o["holderCharacterId"]) for o in active): continue
            holder = self.generate_official(sid)
            office_id = f"administrator_{sid}"
            if office_id not in self.offices:
                candidates = [x for x, v in self.office_types.items() if v["role"] == "settlement_administrator"]
                if not candidates: raise AdministrationError("a settlement_administrator office type is required")
                self.offices[office_id] = {"id": office_id, "officeTypeId": sorted(candidates)[0],
                    "jurisdictionIds": [sid], "holderCharacterId": None, "acting": True,
                    "residenceSettlementId": sid, "status": "active", "successionState": "acting",
                    "modifiers": {}, "localSupport": 20.0, "militaryEntrenchment": 0.0}
            self._appoint(office_id, holder, acting=True, reason=reason); made.append(office_id)
        return tuple(made)

    def on_settlement_acquired(self, settlement_id, controller_polity_id):
        self.settlements[settlement_id]["controllerPolityId"] = controller_polity_id
        return self.ensure_settlement_administrators((settlement_id,), reason="capture")

    def _eligible(self, office, character_id):
        data = self._character_data(character_id)
        if not data.get("active", True): return False
        role = self.office_types[office["officeTypeId"]]["role"]
        return not (role in ("army_commander", "fleet_commander") and data.get("skills", {}).get("command", 0) <= 0)

    def _change_loyalty(self, character_id, delta):
        if not delta: return
        if character_id in self.officials:
            record = self.officials[character_id]
            if record.get("permanentState") == "oathbound" and delta < 0: return
            record["loyalty"] = max(-100.0, min(100.0, record["loyalty"] + delta)); return
        if self.characters.require(character_id).permanent_state == "oathbound" and delta < 0: return
        self.characters.change_loyalty(character_id, delta)

    def _prestige(self, office):
        definition = self.office_types[office["officeTypeId"]]
        return float(definition.get("prestige", 10)) * max(1, len(office["jurisdictionIds"]))

    def appoint(self, office_id, character_id, *, acting=False, reason="appointment"):
        if office_id not in self.offices or not self._known_character(character_id): raise AdministrationError("unknown office or character")
        if not self._eligible(self.offices[office_id], character_id): raise AdministrationError("character is not eligible for office")
        return self._appoint(office_id, character_id, acting=acting, reason=reason)

    def _appoint(self, office_id, character_id, *, acting, reason):
        office = self.offices[office_id]; previous = office.get("holderCharacterId")
        old_prestige = max((self._prestige(o) for o in self.offices.values() if o.get("holderCharacterId") == character_id), default=0)
        office.update(holderCharacterId=character_id, acting=bool(acting), status="active", successionState="acting" if acting else "settled")
        gain = max(0, min(12, round((self._prestige(office) - old_prestige) / 5)))
        # A holder only earns this exact office's prestige once, preventing cycling.
        prior = any(x["officeId"] == office_id and x.get("newHolderCharacterId") == character_id for x in self.history)
        if prior: gain = 0
        self._change_loyalty(character_id, gain)
        self._record("appointment", office_id, previous, character_id, reason, gain)
        return self.view(office_id)

    def removal_warning(self, office_id):
        office = self.offices[office_id]; holder = office.get("holderCharacterId")
        if holder is None: return RemovalWarning(False, 0, (), "This office is vacant.")
        data = self._character_data(holder); loyalty = data.get("loyalty", 0)
        power = max(data.get("skills", {}).get("command", 0), self._prestige(office))
        risk = max(0.0, min(100.0, (30-loyalty)*0.8 + power*0.25 + office["localSupport"]*0.3 + office["militaryEntrenchment"]*0.4))
        outcomes = ("refusal",) if risk < 40 else ("refusal", "defection", "mutiny") if risk < 70 else ("refusal", "defection", "mutiny", "rebellion", "separatism")
        risky = risk >= 25
        message = (f"Warning: removal risk is {risk:.0f}%; possible outcomes: {', '.join(outcomes)}."
                   if risky else f"Removal risk is low ({risk:.0f}%).")
        return RemovalWarning(risky, risk, outcomes if risky else (), message)

    def dismiss(self, office_id, *, confirm_risk=False, reason="dismissal"):
        warning = self.removal_warning(office_id)
        if warning.risky and not confirm_risk: raise AdministrationError(warning.message)
        office = self.offices[office_id]; previous = office.get("holderCharacterId")
        if previous is None: return warning
        penalty = -max(2, min(15, round(self._prestige(office)/8)))
        self._change_loyalty(previous, penalty)
        office.update(holderCharacterId=None, acting=False, successionState="vacant")
        self._record("dismissal", office_id, previous, None, reason, penalty)
        return warning

    def _record(self, kind, office_id, old, new, reason, loyalty_delta):
        self.history.append({"sequence": self._sequence, "kind": kind, "officeId": office_id,
            "previousHolderCharacterId": old, "newHolderCharacterId": new,
            "reason": reason, "loyaltyDelta": loyalty_delta}); self._sequence += 1

    def capacity(self, office_id):
        office = self.offices[office_id]
        data = self._character_data(office["holderCharacterId"]) if office.get("holderCharacterId") else {"skills": {}, "titleGrantIds": []}
        skills = data.get("skills", {}); base = self.office_types[office["officeTypeId"]].get("baseCapacity", 1)
        score = base + skills.get("administration", 0)/20 + skills.get("diplomacy", 0)/50 + skills.get("scholarship", 0)/60
        score += len(data.get("titleGrantIds", ())) * .5
        return round(score, 2)

    def efficiency(self, office_id, *, local_conditions=None, government_modifier=0):
        office = self.offices[office_id]
        data = self._character_data(office["holderCharacterId"]) if office.get("holderCharacterId") else {"skills": {"administration": 50}}
        s = data.get("skills", {})
        value = (s.get("administration", 0)*.55 + s.get("command", 0)*.08 + s.get("engineering", 0)*.08 +
                 s.get("tradecraft", 0)*.1 + s.get("diplomacy", 0)*.1 + s.get("scholarship", 0)*.09)
        value += float(government_modifier) + sum(float(x) for x in (local_conditions or {}).values())
        overload = max(0, len(office["jurisdictionIds"]) - self.capacity(office_id))
        return round(max(0, min(100, value - overload*12)), 2)

    def view(self, office_id):
        office = self.offices[office_id]; holder = office.get("holderCharacterId")
        data = self._character_data(holder) if holder else {"displayName": office.get("collectiveBodyName", "Collective governance"), "skills": {}, "traitIds": []}
        return {**copy.deepcopy(office), "role": self.office_types[office["officeTypeId"]]["role"],
            "title": self.office_types[office["officeTypeId"]].get("title", "Administrator"),
            "holderName": data["displayName"], "collective": holder is None and bool(office.get("collectiveBodyId")), "loyalty": data.get("loyalty"), "skills": copy.deepcopy(data.get("skills", {})),
            "traitIds": list(data.get("traitIds", ())), "physicalLocationId": data.get("locationId"),
            "capacity": self.capacity(office_id), "efficiency": self.efficiency(office_id),
            "activeEffects": copy.deepcopy(office.get("modifiers", {}))}

    def snapshot(self):
        return {"schemaVersion": 1, "officials": [copy.deepcopy(self.officials[x]) for x in sorted(self.officials)],
            "offices": [copy.deepcopy(self.offices[x]) for x in sorted(self.offices)],
            "appointmentHistory": copy.deepcopy(self.history), "nextSequence": self._sequence}

    def restore(self, candidate):
        if not isinstance(candidate, Mapping) or candidate.get("schemaVersion") != 1: raise AdministrationError("administration schemaVersion must be 1")
        officials = _index(candidate.get("officials"), "officials"); offices = _index(candidate.get("offices"), "offices")
        old_officials, old_offices = self.officials, self.offices
        self.officials, self.offices = officials, offices
        try:
            for ident, office in offices.items(): self._validate_office(ident, office)
            history = candidate.get("appointmentHistory"); next_sequence = candidate.get("nextSequence")
            if not isinstance(history, list) or next_sequence != len(history)+1: raise AdministrationError("invalid appointment history")
            if [x.get("sequence") for x in history] != list(range(1, next_sequence)): raise AdministrationError("invalid appointment history order")
        except Exception:
            self.officials, self.offices = old_officials, old_offices; raise
        self.history, self._sequence = copy.deepcopy(history), next_sequence

    def reconstruct(self, local_settlement_ids, factory):
        """Instantiate each locally resident holder once; absent governors stay abstract."""
        local = set(local_settlement_ids); result = {}
        for ident, data in sorted(self.officials.items()):
            if data.get("locationId") in local and data.get("active", True): result[ident] = factory(copy.deepcopy(data))
        return result


class AdministrationSaveAdapter:
    def __init__(self, runtime, world_state): self.runtime, self.world_state = runtime, copy.deepcopy(dict(world_state))
    def capture_world(self):
        result = copy.deepcopy(self.world_state); result[ADMINISTRATION_WORLD_STATE_KEY] = self.runtime.snapshot(); return result
    def migrate_legacy_world(self, candidate):
        result = copy.deepcopy(dict(candidate)); result.setdefault(ADMINISTRATION_WORLD_STATE_KEY, self.runtime.snapshot()); return result
    def validate_world(self, candidate):
        clone = copy.deepcopy(self.runtime.snapshot()); self.runtime.restore(candidate[ADMINISTRATION_WORLD_STATE_KEY]); self.runtime.restore(clone)
    def reconstruct(self, candidate): self.validate_world(candidate); return copy.deepcopy(candidate[ADMINISTRATION_WORLD_STATE_KEY])
    def activate(self, candidate, reconstructed): self.runtime.restore(reconstructed); self.world_state = copy.deepcopy(dict(candidate))

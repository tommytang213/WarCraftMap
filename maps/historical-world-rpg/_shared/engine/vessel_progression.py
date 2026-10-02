"""Persistent, scenario-neutral individual-vessel progression.

Hull/archetype and content balance live in scenario data.  This module owns only
validation, deterministic transactions, bounded progression, and reconstruction
from stable authoritative IDs.  Warcraft handles are deliberately excluded.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Mapping, Protocol


VESSEL_STATE_SCHEMA_VERSION = 1
VESSEL_WORLD_STATE_KEY = "vesselProgressionState"
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
CATEGORIES = {"armament", "hull", "rigging_sails", "navigation", "cargo_logistics",
              "crew_marines", "protection_safety", "flagship_command"}
ROLES = {"combat", "exploration", "trade", "escort", "transport", "command"}
HISTORY_COUNTERS = {"battles", "victories", "defeatedShips", "voyages", "stormsSurvived",
                    "distanceSailed", "escortOperations", "tradeOperations"}
HISTORY_SETS = {"portsVisited", "discoveries", "commandersServedUnder"}
STAT_IDS = {"accuracy", "reload", "boarding", "maneuver", "speed", "stormHandling",
            "range", "supplyEfficiency", "cargoCapacity", "repair", "command"}


class VesselProgressionError(ValueError):
    """An invalid definition, state, or atomic vessel operation."""


class VesselRuntimeAdapter(Protocol):
    def create(self, vessel_id: str, specification: Mapping[str, Any]) -> Any: ...
    def retire(self, representation: Any) -> None: ...
    def exists(self, representation: Any) -> bool: ...


class RecordingVesselAdapter:
    def __init__(self) -> None:
        self.operations: list[tuple[Any, ...]] = []
        self.live: set[str] = set()
        self.serial = 0

    def create(self, vessel_id: str, specification: Mapping[str, Any]) -> str:
        self.serial += 1
        handle = f"vessel_object_{self.serial}"
        self.live.add(handle)
        self.operations.append(("create", vessel_id, copy.deepcopy(dict(specification)), handle))
        return handle

    def retire(self, representation: Any) -> None:
        self.live.discard(representation)
        self.operations.append(("retire", representation))

    def exists(self, representation: Any) -> bool:
        return representation in self.live

    def destroy_unexpectedly(self, representation: Any) -> None:
        self.live.discard(representation)


@dataclass(frozen=True)
class RefitContext:
    year: int
    polity_id: str
    region_id: str
    dockyard_id: str
    dockyard_capability: int
    technology_ids: frozenset[str] = frozenset()
    institution_ids: frozenset[str] = frozenset()
    requirement_ids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class VesselView:
    id: str
    name: str
    archetype_id: str
    fleet_id: str | None
    owner_polity_id: str
    controller_polity_id: str
    role_id: str
    experience: int
    milestone_id: str | None
    crew_quality: int
    hull_condition: int
    maintenance: int
    installed_refit_ids: tuple[str, ...]
    locally_relevant: bool
    represented: bool


def _fail(message: str) -> None:
    raise VesselProgressionError(message)


def _id(value: Any, context: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        _fail(f"{context}: invalid stable ID {value!r}")
    return value


def _integer(value: Any, context: str, low: int = 0, high: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < low or (high is not None and value > high):
        _fail(f"{context}: must be an integer in [{low}, {high if high is not None else 'unbounded'}]")
    return value


def _index(values: Any, context: str) -> dict[str, Mapping[str, Any]]:
    if not isinstance(values, list):
        _fail(f"{context}: must be an array")
    result = {}
    for value in values:
        if not isinstance(value, Mapping):
            _fail(f"{context}: every entry must be an object")
        ident = _id(value.get("id"), f"{context}.id")
        if ident in result:
            _fail(f"{context}: duplicate ID {ident!r}")
        result[ident] = value
    return result


def _ids(values: Any, context: str, targets: Mapping[str, Any] | set[str] | None = None) -> tuple[str, ...]:
    if not isinstance(values, list):
        _fail(f"{context}: must be an array")
    result = []
    for value in values:
        ident = _id(value, context)
        if ident in result:
            _fail(f"{context}: duplicate reference {ident!r}")
        if targets is not None and ident not in targets:
            _fail(f"{context}: missing reference {ident!r}")
        result.append(ident)
    return tuple(result)


def _effects(value: Any, context: str) -> dict[str, int]:
    if not isinstance(value, Mapping):
        _fail(f"{context}: must be an object")
    result = {}
    for stat, amount in value.items():
        if stat not in STAT_IDS:
            _fail(f"{context}: unknown effect {stat!r}")
        result[stat] = _integer(amount, f"{context}.{stat}", -5000, 5000)
    return result


def validate_catalog(catalog: Mapping[str, Any], references: Mapping[str, set[str]] | None = None) -> None:
    """Validate content and optional cross-domain stable-ID references."""
    if not isinstance(catalog, Mapping) or catalog.get("schemaVersion") != 1:
        _fail("vessel catalog schemaVersion must be 1")
    slots = _index(catalog.get("slotDefinitions"), "slotDefinitions")
    archetypes = _index(catalog.get("archetypes"), "archetypes")
    refits = _index(catalog.get("refits"), "refits")
    awards = _index(catalog.get("experienceAwards"), "experienceAwards")
    milestones = _index(catalog.get("milestones"), "milestones")
    traits = _index(catalog.get("traits"), "traits")
    specializations = _index(catalog.get("specializations"), "specializations")
    evidence = _index(catalog.get("historicalEvidence"), "historicalEvidence")
    tuning = catalog.get("tuning")
    if not all((slots, archetypes, refits, awards, milestones)) or not isinstance(tuning, Mapping):
        _fail("vessel catalog requires slots, archetypes, refits, awards, milestones, and tuning")
    for ident, slot in slots.items():
        if slot.get("category") not in CATEGORIES:
            _fail(f"slot {ident}: invalid category")
        _integer(slot.get("capacity"), f"slot {ident}.capacity", 1, 8)
    for ident, archetype in archetypes.items():
        _ids(archetype.get("slotIds"), f"archetype {ident}.slotIds", slots)
        roles = _ids(archetype.get("roleIds"), f"archetype {ident}.roleIds", ROLES)
        if not roles:
            _fail(f"archetype {ident}: requires a role")
        _integer(archetype.get("powerRating"), f"archetype {ident}.powerRating", 1)
        template = _id(archetype.get("runtimeTemplateId"), f"archetype {ident}.runtimeTemplateId")
        if references and template not in references.get("runtimeTemplates", set()):
            _fail(f"archetype {ident}: missing runtime-template reference {template!r}")
    for ident, refit in refits.items():
        slot = refit.get("slotId")
        if slot not in slots or refit.get("category") != slots[slot].get("category"):
            _fail(f"refit {ident}: incompatible slot/category")
        _ids(refit.get("compatibleArchetypeIds"), f"refit {ident}.compatibleArchetypeIds", archetypes)
        _integer(refit.get("slotCost"), f"refit {ident}.slotCost", 1, 8)
        for key in ("minimumYear", "maximumYear", "dockyardCapability", "moneyCost", "removalMoneyCost", "repairMoneyPerPoint"):
            _integer(refit.get(key), f"refit {ident}.{key}", 0)
        if refit["minimumYear"] > refit["maximumYear"]:
            _fail(f"refit {ident}: invalid year range")
        for field, domain in (("technologyIds", "technologies"), ("institutionIds", "institutions"),
                              ("polityIds", "polities"), ("regionIds", "regions"),
                              ("requirementIds", "requirements")):
            values = _ids(refit.get(field), f"refit {ident}.{field}")
            if references:
                for value in values:
                    if value not in references.get(domain, set()):
                        _fail(f"refit {ident}: missing {domain[:-1]} reference {value!r}")
        resources = refit.get("resourceCosts")
        if not isinstance(resources, Mapping):
            _fail(f"refit {ident}.resourceCosts: must be an object")
        for resource, amount in resources.items():
            _id(resource, f"refit {ident}.resourceCosts")
            if references and resource not in references.get("resources", set()):
                _fail(f"refit {ident}: missing resource reference {resource!r}")
            _integer(amount, f"refit {ident}.resourceCosts.{resource}", 1)
        _effects(refit.get("effects"), f"refit {ident}.effects")
        ev = refit.get("evidenceId")
        if ev not in evidence:
            _fail(f"refit {ident}: missing historical-evidence reference {ev!r}")
    previous = -1
    for ident, milestone in sorted(milestones.items(), key=lambda item: item[1].get("experience", -1)):
        threshold = _integer(milestone.get("experience"), f"milestone {ident}.experience", 0)
        if threshold <= previous:
            _fail("milestone thresholds must be unique and increasing")
        previous = threshold
        _ids(milestone.get("traitIds"), f"milestone {ident}.traitIds", traits)
        _ids(milestone.get("specializationIds"), f"milestone {ident}.specializationIds", specializations)
    for domain, values in (("trait", traits), ("specialization", specializations)):
        for ident, value in values.items():
            roles = _ids(value.get("roleIds"), f"{domain} {ident}.roleIds", ROLES)
            if not roles:
                _fail(f"{domain} {ident}: requires a role")
            _effects(value.get("effects"), f"{domain} {ident}.effects")
    for ident, award in awards.items():
        _integer(award.get("experience"), f"experience award {ident}.experience", 1)
        if not isinstance(award.get("oneShot"), bool):
            _fail(f"experience award {ident}.oneShot: must be boolean")
        _ids(award.get("roleIds"), f"experience award {ident}.roleIds", ROLES)
    _integer(tuning.get("curveScale"), "tuning.curveScale", 1)
    _integer(tuning.get("maximumContinuousBasisPoints"), "tuning.maximumContinuousBasisPoints", 1, 4000)
    _integer(tuning.get("maximumCombinedBasisPoints"), "tuning.maximumCombinedBasisPoints", 2500, 4000)
    _integer(tuning.get("maintenanceMoneyPerPoint"), "tuning.maintenanceMoneyPerPoint", 1)
    for role in ROLES:
        weights = tuning.get("roleWeights", {}).get(role)
        if not isinstance(weights, Mapping) or not weights:
            _fail(f"tuning.roleWeights: missing role {role!r}")
        parsed = _effects(weights, f"tuning.roleWeights.{role}")
        if any(x < 0 for x in parsed.values()) or sum(parsed.values()) != 10000:
            _fail(f"tuning.roleWeights.{role}: weights must total 10000")


def initial_state(catalog: Mapping[str, Any], vessels: list[Mapping[str, Any]]) -> dict[str, Any]:
    validate_catalog(catalog)
    records = []
    for source in vessels:
        records.append({
            "id": source.get("id"), "name": source.get("name"), "archetypeId": source.get("archetypeId"),
            "fleetId": source.get("fleetId"), "ownerPolityId": source.get("ownerPolityId"),
            "controllerPolityId": source.get("controllerPolityId"), "roleId": source.get("roleId"),
            "crewQuality": source.get("crewQuality", 50), "experience": source.get("experience", 0),
            "specializationIds": list(source.get("specializationIds", [])), "installedRefits": [],
            "hullCondition": source.get("hullCondition", 100), "maintenance": source.get("maintenance", 100),
            "captainCharacterId": source.get("captainCharacterId"), "admiralCharacterId": source.get("admiralCharacterId"),
            "locallyRelevant": source.get("locallyRelevant", False), "retired": False,
            "history": {**{x: 0 for x in HISTORY_COUNTERS}, **{x: [] for x in HISTORY_SETS},
                        "events": [], "completedAccomplishmentIds": [], "refitEvents": [], "milestoneEvents": []},
        })
    return validate_state(catalog, {"schemaVersion": 1, "vessels": records, "processedTransactionIds": []})


def _milestone(catalog: Mapping[str, Any], experience: int) -> Mapping[str, Any] | None:
    eligible = [x for x in catalog["milestones"] if x["experience"] <= experience]
    return max(eligible, key=lambda x: x["experience"]) if eligible else None


def validate_state(catalog: Mapping[str, Any], state: Mapping[str, Any], references: Mapping[str, set[str]] | None = None) -> dict[str, Any]:
    validate_catalog(catalog)
    if not isinstance(state, Mapping) or set(state) != {"schemaVersion", "vessels", "processedTransactionIds"} or state.get("schemaVersion") != 1:
        _fail("vessel state must be schema 1 with vessels and processedTransactionIds")
    archetypes, refits = _index(catalog["archetypes"], "archetypes"), _index(catalog["refits"], "refits")
    result, seen = copy.deepcopy(dict(state)), set()
    for vessel in result["vessels"] if isinstance(result.get("vessels"), list) else _fail("vessels must be an array"):
        required = {"id", "name", "archetypeId", "fleetId", "ownerPolityId", "controllerPolityId", "roleId",
                    "crewQuality", "experience", "specializationIds", "installedRefits", "hullCondition", "maintenance",
                    "captainCharacterId", "admiralCharacterId", "locallyRelevant", "retired", "history"}
        if not isinstance(vessel, Mapping) or set(vessel) != required:
            _fail("vessel state contains unexpected or missing fields")
        ident = _id(vessel.get("id"), "vessel.id")
        if ident in seen:
            _fail(f"vessels: duplicate ID {ident!r}")
        seen.add(ident)
        archetype = archetypes.get(vessel.get("archetypeId"))
        if archetype is None or vessel.get("roleId") not in archetype["roleIds"]:
            _fail(f"vessel {ident}: incompatible archetype or role")
        for key in ("ownerPolityId", "controllerPolityId"):
            value = _id(vessel.get(key), f"vessel {ident}.{key}")
            if references and value not in references.get("polities", set()):
                _fail(f"vessel {ident}: missing polity reference {value!r}")
        if vessel.get("fleetId") is not None:
            _id(vessel["fleetId"], f"vessel {ident}.fleetId")
            if references and vessel["fleetId"] not in references.get("fleets", set()):
                _fail(f"vessel {ident}: missing fleet reference {vessel['fleetId']!r}")
        _integer(vessel.get("crewQuality"), f"vessel {ident}.crewQuality", 0, 100)
        _integer(vessel.get("experience"), f"vessel {ident}.experience", 0)
        _integer(vessel.get("hullCondition"), f"vessel {ident}.hullCondition", 0, 100)
        _integer(vessel.get("maintenance"), f"vessel {ident}.maintenance", 0, 100)
        if not isinstance(vessel.get("locallyRelevant"), bool) or not isinstance(vessel.get("retired"), bool):
            _fail(f"vessel {ident}: relevance and retired must be boolean")
        for key in ("captainCharacterId", "admiralCharacterId"):
            if vessel.get(key) is not None:
                value = _id(vessel[key], f"vessel {ident}.{key}")
                if references and value not in references.get("characters", set()):
                    _fail(f"vessel {ident}: missing character reference {value!r}")
        specialization_defs = _index(catalog["specializations"], "specializations")
        specs = _ids(vessel.get("specializationIds"), f"vessel {ident}.specializationIds", specialization_defs)
        reached = _milestone(catalog, vessel["experience"])
        allowed = set(reached.get("specializationIds", [])) if reached else set()
        if set(specs) - allowed:
            _fail(f"vessel {ident}: specialization not unlocked")
        if any(vessel["roleId"] not in specialization_defs[x]["roleIds"] for x in specs):
            _fail(f"vessel {ident}: specialization is incompatible with role")
        installed, occupancy = vessel.get("installedRefits"), {}
        if not isinstance(installed, list):
            _fail(f"vessel {ident}.installedRefits: must be an array")
        for item in installed:
            if not isinstance(item, Mapping) or set(item) != {"refitId", "condition", "installedYear"}:
                _fail(f"vessel {ident}: invalid installed refit")
            refit = refits.get(item.get("refitId"))
            if refit is None or vessel["archetypeId"] not in refit["compatibleArchetypeIds"]:
                _fail(f"vessel {ident}: incompatible installed refit {item.get('refitId')!r}")
            if item["refitId"] in [x["refitId"] for x in installed if x is not item]:
                _fail(f"vessel {ident}: duplicate installed refit {item['refitId']!r}")
            occupancy[refit["slotId"]] = occupancy.get(refit["slotId"], 0) + refit["slotCost"]
            _integer(item.get("condition"), f"vessel {ident}.refit.condition", 0, 100)
            _integer(item.get("installedYear"), f"vessel {ident}.refit.installedYear", 0)
        slot_defs = _index(catalog["slotDefinitions"], "slotDefinitions")
        for slot, used in occupancy.items():
            if slot not in archetype["slotIds"] or used > slot_defs[slot]["capacity"]:
                _fail(f"vessel {ident}: refit slot capacity exceeded for {slot!r}")
        history = vessel.get("history")
        hfields = HISTORY_COUNTERS | HISTORY_SETS | {"events", "completedAccomplishmentIds", "refitEvents", "milestoneEvents"}
        if not isinstance(history, Mapping) or set(history) != hfields:
            _fail(f"vessel {ident}: invalid service history")
        for key in HISTORY_COUNTERS:
            _integer(history[key], f"vessel {ident}.history.{key}", 0)
        for key in HISTORY_SETS | {"completedAccomplishmentIds"}:
            _ids(history[key], f"vessel {ident}.history.{key}")
        for key in ("events", "refitEvents", "milestoneEvents"):
            if not isinstance(history[key], list) or len(history[key]) > catalog["tuning"]["historyEventLimit"]:
                _fail(f"vessel {ident}.history.{key}: invalid or over configured bound")
    transactions = _ids(result.get("processedTransactionIds"), "processedTransactionIds")
    result["processedTransactionIds"] = list(transactions[-catalog["tuning"]["transactionIdLimit"]:])
    return result


class VesselProgressionRuntime:
    def __init__(self, catalog: Mapping[str, Any], state: Mapping[str, Any], adapter: VesselRuntimeAdapter,
                 references: Mapping[str, set[str]] | None = None) -> None:
        validate_catalog(catalog, references)
        self.catalog = copy.deepcopy(dict(catalog))
        self.references = references
        self.state = validate_state(self.catalog, state, references)
        self.adapter = adapter
        self.representations: dict[str, Any] = {}

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self.state)

    def _record(self, vessel_id: str, candidate: dict[str, Any] | None = None) -> dict[str, Any]:
        state = candidate or self.state
        found = next((x for x in state["vessels"] if x["id"] == vessel_id), None)
        if found is None:
            _fail(f"unknown vessel {vessel_id!r}")
        return found

    def _commit(self, candidate: dict[str, Any]) -> bool:
        checked = validate_state(self.catalog, candidate, self.references)
        changed = checked != self.state
        self.state = checked
        return changed

    def view(self, vessel_id: str) -> VesselView:
        x = self._record(vessel_id)
        milestone = _milestone(self.catalog, x["experience"])
        return VesselView(x["id"], x["name"], x["archetypeId"], x["fleetId"], x["ownerPolityId"],
                          x["controllerPolityId"], x["roleId"], x["experience"], milestone["id"] if milestone else None,
                          x["crewQuality"], x["hullCondition"], x["maintenance"],
                          tuple(i["refitId"] for i in x["installedRefits"]), x["locallyRelevant"], vessel_id in self.representations)

    def _transaction(self, transaction_id: str) -> tuple[dict[str, Any], str]:
        ident = _id(transaction_id, "transactionId")
        if ident in self.state["processedTransactionIds"]:
            _fail(f"transaction {ident!r}: already processed")
        return self.snapshot(), ident

    def install_refit(self, vessel_id: str, refit_id: str, context: RefitContext,
                      account: Mapping[str, Any], transaction_id: str, replace_refit_id: str | None = None) -> dict[str, Any]:
        candidate, tx = self._transaction(transaction_id)
        vessel = self._record(vessel_id, candidate)
        refit = _index(self.catalog["refits"], "refits").get(refit_id)
        if refit is None:
            _fail(f"missing refit {refit_id!r}")
        if vessel["retired"] or refit_id in {x["refitId"] for x in vessel["installedRefits"]}:
            _fail("refit cannot be installed on this vessel")
        if vessel["archetypeId"] not in refit["compatibleArchetypeIds"]:
            _fail("refit is incompatible with hull archetype")
        if not refit["minimumYear"] <= context.year <= refit["maximumYear"]:
            _fail("refit is unavailable in campaign year")
        checks = ((refit["technologyIds"], context.technology_ids, "technology"),
                  (refit["institutionIds"], context.institution_ids, "institution"),
                  (refit["requirementIds"], context.requirement_ids, "scenario requirement"))
        for needed, present, label in checks:
            if not set(needed) <= set(present):
                _fail(f"refit lacks required {label}")
        if refit["polityIds"] and context.polity_id not in refit["polityIds"]:
            _fail("refit unavailable to polity")
        if refit["regionIds"] and context.region_id not in refit["regionIds"]:
            _fail("refit unavailable in region")
        if context.dockyard_capability < refit["dockyardCapability"]:
            _fail("dockyard capability is inadequate")
        _id(context.dockyard_id, "dockyardId")
        installed = vessel["installedRefits"]
        replaced = next((x for x in installed if x["refitId"] == replace_refit_id), None) if replace_refit_id else None
        if replace_refit_id and replaced is None:
            _fail("replacement target is not installed")
        if replaced:
            old = _index(self.catalog["refits"], "refits")[replaced["refitId"]]
            if old["slotId"] != refit["slotId"]:
                _fail("replacement must use the same slot")
            installed.remove(replaced)
        installed.append({"refitId": refit_id, "condition": 100, "installedYear": context.year})
        money = account.get("money")
        resources = copy.deepcopy(account.get("resources"))
        if isinstance(money, bool) or not isinstance(money, int) or not isinstance(resources, Mapping):
            _fail("refit account is invalid")
        total_money = refit["moneyCost"] + (refit["removalMoneyCost"] if replaced else 0)
        if money < total_money or any(resources.get(k, 0) < v for k, v in refit["resourceCosts"].items()):
            _fail("insufficient money or resources")
        checked_account = {"money": money - total_money, "resources": dict(resources)}
        for key, amount in refit["resourceCosts"].items():
            checked_account["resources"][key] -= amount
        vessel["history"]["refitEvents"].append({"transactionId": tx, "refitId": refit_id,
            "action": "replace" if replaced else "install", "year": context.year, "dockyardId": context.dockyard_id})
        vessel["history"]["refitEvents"] = vessel["history"]["refitEvents"][-self.catalog["tuning"]["historyEventLimit"]:]
        candidate["processedTransactionIds"].append(tx)
        self._commit(candidate)
        self._refresh(vessel_id)
        return checked_account

    def remove_refit(self, vessel_id: str, refit_id: str, money: int, year: int, dockyard_id: str, transaction_id: str) -> int:
        candidate, tx = self._transaction(transaction_id)
        vessel = self._record(vessel_id, candidate)
        item = next((x for x in vessel["installedRefits"] if x["refitId"] == refit_id), None)
        if item is None:
            _fail("refit is not installed")
        refit = _index(self.catalog["refits"], "refits")[refit_id]
        _integer(money, "money", 0)
        if money < refit["removalMoneyCost"]:
            _fail("insufficient money for refit removal")
        vessel["installedRefits"].remove(item)
        vessel["history"]["refitEvents"].append({"transactionId": tx, "refitId": refit_id, "action": "remove", "year": year, "dockyardId": _id(dockyard_id, "dockyardId")})
        candidate["processedTransactionIds"].append(tx)
        self._commit(candidate)
        self._refresh(vessel_id)
        return money - refit["removalMoneyCost"]

    def repair(self, vessel_id: str, refit_id: str | None, points: int, money: int, transaction_id: str) -> int:
        candidate, tx = self._transaction(transaction_id)
        vessel = self._record(vessel_id, candidate)
        points, money = _integer(points, "repair points", 1, 100), _integer(money, "money", 0)
        if refit_id is None:
            current, rate, target = vessel["hullCondition"], self.catalog["tuning"]["hullRepairMoneyPerPoint"], vessel
            key = "hullCondition"
        else:
            target = next((x for x in vessel["installedRefits"] if x["refitId"] == refit_id), None)
            if target is None: _fail("refit is not installed")
            current, rate, key = target["condition"], _index(self.catalog["refits"], "refits")[refit_id]["repairMoneyPerPoint"], "condition"
        restored = min(points, 100 - current)
        if restored <= 0: _fail("target does not require repair")
        cost = restored * rate
        if money < cost: _fail("insufficient money for repair")
        target[key] += restored
        candidate["processedTransactionIds"].append(tx)
        self._commit(candidate)
        self._refresh(vessel_id)
        return money - cost

    def apply_damage(self, vessel_id: str, *, hull: int = 0, maintenance: int = 0,
                     refit_damage: Mapping[str, int] | None = None) -> bool:
        """Atomically reconcile validated combat/storm wear into authority."""
        candidate = self.snapshot(); vessel = self._record(vessel_id, candidate)
        hull = _integer(hull, "hull damage", 0, 100)
        maintenance = _integer(maintenance, "maintenance damage", 0, 100)
        vessel["hullCondition"] = max(0, vessel["hullCondition"] - hull)
        vessel["maintenance"] = max(0, vessel["maintenance"] - maintenance)
        installed = {x["refitId"]: x for x in vessel["installedRefits"]}
        if not isinstance(refit_damage or {}, Mapping): _fail("refit damage must be an object")
        for refit_id, points in (refit_damage or {}).items():
            if refit_id not in installed: _fail(f"refit {refit_id!r} is not installed")
            installed[refit_id]["condition"] = max(0, installed[refit_id]["condition"] -
                                                    _integer(points, f"refit damage {refit_id}", 0, 100))
        changed = self._commit(candidate)
        self._refresh(vessel_id)
        return changed

    def restore_maintenance(self, vessel_id: str, points: int, money: int, transaction_id: str) -> int:
        candidate, tx = self._transaction(transaction_id); vessel = self._record(vessel_id, candidate)
        points, money = _integer(points, "maintenance points", 1, 100), _integer(money, "money", 0)
        restored = min(points, 100 - vessel["maintenance"])
        if restored <= 0: _fail("vessel does not require maintenance")
        cost = restored * self.catalog["tuning"]["maintenanceMoneyPerPoint"]
        if money < cost: _fail("insufficient money for maintenance")
        vessel["maintenance"] += restored; candidate["processedTransactionIds"].append(tx)
        self._commit(candidate); self._refresh(vessel_id)
        return money - cost

    def award(self, vessel_id: str, award_id: str, accomplishment_id: str | None = None,
              history: Mapping[str, Any] | None = None) -> bool:
        candidate = self.snapshot()
        vessel = self._record(vessel_id, candidate)
        award = _index(self.catalog["experienceAwards"], "experienceAwards").get(award_id)
        if award is None or vessel["roleId"] not in award["roleIds"]:
            _fail("experience award is missing or incompatible with vessel role")
        if award["oneShot"]:
            accomplishment_id = _id(accomplishment_id, "accomplishmentId")
            if accomplishment_id in vessel["history"]["completedAccomplishmentIds"]:
                return False
            vessel["history"]["completedAccomplishmentIds"].append(accomplishment_id)
        before = _milestone(self.catalog, vessel["experience"])
        vessel["experience"] += award["experience"]
        after = _milestone(self.catalog, vessel["experience"])
        if history:
            for key, value in history.items():
                if key in HISTORY_COUNTERS:
                    vessel["history"][key] += _integer(value, f"history.{key}", 0)
                elif key in HISTORY_SETS:
                    ident = _id(value, f"history.{key}")
                    if ident not in vessel["history"][key]: vessel["history"][key].append(ident)
                else: _fail(f"unsupported history field {key!r}")
        if after and (before is None or before["id"] != after["id"]):
            vessel["history"]["milestoneEvents"].append({"milestoneId": after["id"], "experience": vessel["experience"]})
        vessel["history"]["events"].append({"awardId": award_id, "experience": award["experience"], "accomplishmentId": accomplishment_id})
        limit = self.catalog["tuning"]["historyEventLimit"]
        vessel["history"]["events"] = vessel["history"]["events"][-limit:]
        vessel["history"]["milestoneEvents"] = vessel["history"]["milestoneEvents"][-limit:]
        return self._commit(candidate)

    def choose_specialization(self, vessel_id: str, specialization_id: str) -> bool:
        candidate = self.snapshot(); vessel = self._record(vessel_id, candidate)
        if specialization_id in vessel["specializationIds"]: return False
        vessel["specializationIds"].append(specialization_id)
        return self._commit(candidate)

    def update(self, vessel_id: str, **changes: Any) -> bool:
        mapping = {"fleet_id": "fleetId", "owner_polity_id": "ownerPolityId", "controller_polity_id": "controllerPolityId",
                   "crew_quality": "crewQuality", "hull_condition": "hullCondition", "maintenance": "maintenance",
                   "captain_character_id": "captainCharacterId", "admiral_character_id": "admiralCharacterId",
                   "locally_relevant": "locallyRelevant", "retired": "retired"}
        if set(changes) - set(mapping): _fail("unsupported vessel update")
        candidate = self.snapshot(); vessel = self._record(vessel_id, candidate)
        for key, value in changes.items(): vessel[mapping[key]] = value
        changed = self._commit(candidate)
        self._refresh(vessel_id)
        return changed

    def derived_effects(self, vessel_id: str) -> dict[str, int]:
        vessel = self._record(vessel_id)
        tuning = self.catalog["tuning"]
        continuous = round(tuning["maximumContinuousBasisPoints"] * vessel["experience"] / (vessel["experience"] + tuning["curveScale"]))
        result = {stat: continuous * weight // 10000 for stat, weight in tuning["roleWeights"][vessel["roleId"]].items()}
        indexes = {k: _index(self.catalog[k], k) for k in ("refits", "traits", "specializations")}
        sources = [indexes["refits"][x["refitId"]]["effects"] for x in vessel["installedRefits"]]
        # Milestones layer traits on continuous growth; reaching a later title
        # never silently removes an earlier ship-company capability.
        reached = [x for x in self.catalog["milestones"] if x["experience"] <= vessel["experience"]]
        sources += [indexes["traits"][trait_id]["effects"]
                    for milestone in reached for trait_id in milestone["traitIds"]]
        sources += [indexes["specializations"][x]["effects"] for x in vessel["specializationIds"]]
        for effects in sources:
            for stat, amount in effects.items(): result[stat] = result.get(stat, 0) + amount
        cap = tuning["maximumCombinedBasisPoints"]
        return {key: max(-cap, min(cap, value)) for key, value in sorted(result.items())}

    def comparison(self, vessel_id: str) -> dict[str, Any]:
        vessel, view = self._record(vessel_id), self.view(vessel_id)
        archetype = _index(self.catalog["archetypes"], "archetypes")[vessel["archetypeId"]]
        return {"vesselId": vessel_id, "name": view.name, "archetypeId": view.archetype_id,
                "hullPowerRating": archetype["powerRating"], "roleId": view.role_id, "experience": view.experience,
                "milestoneId": view.milestone_id, "effectsBasisPoints": self.derived_effects(vessel_id),
                "crewQuality": view.crew_quality, "hullCondition": view.hull_condition,
                "maintenance": view.maintenance, "installedRefitIds": list(view.installed_refit_ids)}

    def reconstruct(self) -> None:
        for vessel in self.state["vessels"]:
            self._refresh(vessel["id"])

    def _refresh(self, vessel_id: str) -> None:
        vessel = self._record(vessel_id)
        should_exist = vessel["locallyRelevant"] and not vessel["retired"]
        handle = self.representations.get(vessel_id)
        if handle is not None and (not self.adapter.exists(handle) or not should_exist):
            if self.adapter.exists(handle): self.adapter.retire(handle)
            self.representations.pop(vessel_id, None); handle = None
        if should_exist and handle is None:
            archetype = _index(self.catalog["archetypes"], "archetypes")[vessel["archetypeId"]]
            self.representations[vessel_id] = self.adapter.create(vessel_id, {"runtimeTemplateId": archetype["runtimeTemplateId"],
                "effectsBasisPoints": self.derived_effects(vessel_id), "hullCondition": vessel["hullCondition"],
                "maintenance": vessel["maintenance"], "crewQuality": vessel["crewQuality"]})

    def restore(self, state: Mapping[str, Any], reconstruct: bool = True) -> None:
        checked = validate_state(self.catalog, state, self.references)
        for handle in tuple(self.representations.values()):
            if self.adapter.exists(handle): self.adapter.retire(handle)
        self.representations.clear(); self.state = checked
        if reconstruct: self.reconstruct()


class VesselSaveAdapter:
    def __init__(self, runtime: VesselProgressionRuntime, base_world: Mapping[str, Any]):
        self.runtime, self.base_world = runtime, copy.deepcopy(dict(base_world))

    def capture_world(self) -> dict[str, Any]:
        result = copy.deepcopy(self.base_world); result[VESSEL_WORLD_STATE_KEY] = self.runtime.snapshot(); return result

    def validate_world(self, world: Mapping[str, Any]) -> None:
        validate_state(self.runtime.catalog, world.get(VESSEL_WORLD_STATE_KEY), self.runtime.references)

    def reconstruct(self, world: Mapping[str, Any]) -> dict[str, Any]:
        return validate_state(self.runtime.catalog, world[VESSEL_WORLD_STATE_KEY], self.runtime.references)

    def activate(self, world: Mapping[str, Any], rebuilt: Mapping[str, Any]) -> None:
        self.runtime.restore(rebuilt)

    def migrate_legacy_world(self, world: Mapping[str, Any]) -> dict[str, Any]:
        result = copy.deepcopy(dict(world))
        if VESSEL_WORLD_STATE_KEY not in result: result[VESSEL_WORLD_STATE_KEY] = self.runtime.snapshot()
        self.validate_world(result); return result


def migrate_state_v0(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Pure one-version migration; legacy records gain bounded history/transactions."""
    result = copy.deepcopy(dict(candidate))
    if result.get("schemaVersion") != 0: _fail("vessel migration requires schemaVersion 0")
    result["schemaVersion"] = 1; result.setdefault("processedTransactionIds", [])
    for vessel in result.get("vessels", []):
        vessel.setdefault("specializationIds", []); vessel.setdefault("installedRefits", [])
        vessel.setdefault("captainCharacterId", None); vessel.setdefault("admiralCharacterId", None)
        vessel.setdefault("locallyRelevant", False); vessel.setdefault("retired", False)
        history = vessel.setdefault("history", {})
        for key in HISTORY_COUNTERS: history.setdefault(key, 0)
        for key in HISTORY_SETS | {"completedAccomplishmentIds"}: history.setdefault(key, [])
        for key in ("events", "refitEvents", "milestoneEvents"): history.setdefault(key, [])
    return result

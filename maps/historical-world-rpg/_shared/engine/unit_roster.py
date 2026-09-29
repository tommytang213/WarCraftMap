"""Scenario-neutral ordinary-unit roster validation and projection.

Roster catalogs are definitions, not campaign state.  Scenario balance and names
remain in data; this module resolves inheritance, checks cross-domain references,
and projects strategic strength into bounded, reconstructible runtime proxies.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
CATEGORIES = {"infantry", "cavalry", "artillery", "specialist", "marine", "transport", "merchant", "warship"}
LAND = {"infantry", "cavalry", "artillery", "specialist", "marine"}
NAVAL = CATEGORIES - LAND
MECHANICS = {"passive", "active", "aura", "formation", "weapon", "morale", "discipline", "resistance", "counter", "logistics", "terrain", "boarding", "siege"}
ROSTER_STATE_VERSION = 1


class RosterError(ValueError):
    pass


def _id(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise RosterError(f"{context}: invalid stable ID {value!r}")
    return value


def _index(rows: Any, domain: str) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        raise RosterError(f"{domain}: must be an array")
    out = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise RosterError(f"{domain}: entries must be objects")
        ident = _id(row.get("id"), f"{domain}.id")
        if ident in out:
            raise RosterError(f"{domain}: duplicate ID {ident!r}")
        out[ident] = copy.deepcopy(dict(row))
    return out


def _positive(value: Any, context: str, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < (0 if allow_zero else 1):
        raise RosterError(f"{context}: must be a {'non-negative' if allow_zero else 'positive'} integer")
    return value


def _unique_ids(value: Any, context: str) -> list[str]:
    if not isinstance(value, list):
        raise RosterError(f"{context}: must be an array")
    result = [_id(x, context) for x in value]
    if len(result) != len(set(result)):
        raise RosterError(f"{context}: duplicate reference")
    return result


def _merge(parent: Mapping[str, Any], child: Mapping[str, Any], context: str) -> dict[str, Any]:
    """Explicit merge: scalars replace, maps merge, ID arrays replace or append."""
    policy = child.get("inheritance", {"mode": "replace_lists"})
    if not isinstance(policy, Mapping) or policy.get("mode") not in {"replace_lists", "append_lists"}:
        raise RosterError(f"{context}.inheritance: invalid mode")
    result = copy.deepcopy(dict(parent))
    for key, value in child.items():
        if key in {"extends", "inheritance"}:
            continue
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            merged = copy.deepcopy(dict(result[key])); merged.update(copy.deepcopy(dict(value))); result[key] = merged
        elif isinstance(value, list) and isinstance(result.get(key), list) and policy["mode"] == "append_lists":
            result[key] = copy.deepcopy(result[key]) + copy.deepcopy(value)
        else:
            result[key] = copy.deepcopy(value)
    result["id"] = child["id"]
    result.pop("abstract", None)
    return result


@dataclass(frozen=True)
class Availability:
    available: bool
    historical_modifier: int
    early_access: bool


class RosterCatalog:
    """Validated and fully resolved catalog of ordinary-unit archetypes."""

    def __init__(self, source: Mapping[str, Any], references: Mapping[str, set[str]] | None = None):
        if not isinstance(source, Mapping) or source.get("schemaVersion") != 1:
            raise RosterError("roster schemaVersion must be 1")
        self.source = copy.deepcopy(dict(source))
        self.campaign_years = source.get("campaignYears")
        if not isinstance(self.campaign_years, Mapping) or not all(isinstance(self.campaign_years.get(k), int) for k in ("start", "end")) or self.campaign_years["start"] > self.campaign_years["end"]:
            raise RosterError("campaignYears: invalid range")
        self.movement_classes = _index(source.get("movementClasses"), "movementClasses")
        self.weapons = _index(source.get("weapons"), "weapons")
        self.armor = _index(source.get("armor"), "armor")
        self.abilities = _index(source.get("abilities"), "abilities")
        self.formations = _index(source.get("formations"), "formations")
        self.ships = _index(source.get("ships"), "ships")
        self.templates = _index(source.get("runtimeTemplates"), "runtimeTemplates")
        self.archetype_sources = _index(source.get("archetypes"), "archetypes")
        self.references = references or {}
        self._validate_components()
        self.archetypes = self._resolve_archetypes()
        self._validate_archetypes()
        self._validate_relationships()

    def _validate_components(self) -> None:
        for ident, movement in self.movement_classes.items():
            if movement.get("domain") not in {"land", "naval"}:
                raise RosterError(f"movement class {ident}: invalid domain")
        for domain, rows in (("weapon", self.weapons), ("armor", self.armor)):
            for ident, row in rows.items():
                cats = _unique_ids(row.get("compatibleCategories"), f"{domain} {ident}.compatibleCategories")
                if not set(cats) <= CATEGORIES:
                    raise RosterError(f"{domain} {ident}: invalid compatible category")
        for ident, ability in self.abilities.items():
            if ability.get("mechanic") not in MECHANICS:
                raise RosterError(f"ability {ident}: invalid mechanic")
            cats = _unique_ids(ability.get("compatibleCategories"), f"ability {ident}.compatibleCategories")
            if not set(cats) <= CATEGORIES:
                raise RosterError(f"ability {ident}: invalid compatible category")
        for ident, formation in self.formations.items():
            cats = _unique_ids(formation.get("compatibleCategories"), f"formation {ident}.compatibleCategories")
            if not set(cats) <= LAND:
                raise RosterError(f"formation {ident}: formations require land categories")
        for ident, ship in self.ships.items():
            if ship.get("category") not in NAVAL:
                raise RosterError(f"ship {ident}: invalid category")
            _positive(ship.get("crewStrength"), f"ship {ident}.crewStrength")
        for ident, template in self.templates.items():
            if template.get("domain") not in {"land", "naval"}:
                raise RosterError(f"runtime template {ident}: invalid domain")
            _positive(template.get("strengthPerObject"), f"runtime template {ident}.strengthPerObject")
            _positive(template.get("maxActiveObjects"), f"runtime template {ident}.maxActiveObjects")
            rawcode = template.get("warcraftUnitTypeId")
            if not isinstance(rawcode, str) or len(rawcode) != 4:
                raise RosterError(f"runtime template {ident}: Warcraft unit type must be four characters")

    def _resolve_archetypes(self) -> dict[str, dict[str, Any]]:
        resolved, visiting = {}, set()
        def visit(ident: str) -> dict[str, Any]:
            if ident in visiting:
                raise RosterError(f"archetype inheritance cycle at {ident!r}")
            if ident in resolved:
                return resolved[ident]
            row = self.archetype_sources[ident]; visiting.add(ident)
            parent_id = row.get("extends")
            if parent_id is None:
                value = copy.deepcopy(row); value.pop("inheritance", None)
            else:
                parent_id = _id(parent_id, f"archetype {ident}.extends")
                if parent_id not in self.archetype_sources:
                    raise RosterError(f"archetype {ident}: missing parent {parent_id!r}")
                value = _merge(visit(parent_id), row, f"archetype {ident}")
            visiting.remove(ident); resolved[ident] = value
            return value
        for ident in sorted(self.archetype_sources): visit(ident)
        return resolved

    def _validate_archetypes(self) -> None:
        required = {"id", "name", "category", "movementClassId", "weaponIds", "armorIds", "abilityIds", "formationIds", "strategicStrength", "runtimeTemplateId", "cost", "upkeep", "supply", "availability", "upgradeToIds", "replacementIds", "militaryTraditionIds", "technologyIds", "countryId"}
        for ident, row in self.archetypes.items():
            if row.get("abstract") is True:
                continue
            missing = required - set(row)
            if missing:
                raise RosterError(f"archetype {ident}: missing fields {sorted(missing)}")
            category = row.get("category")
            if category not in CATEGORIES:
                raise RosterError(f"archetype {ident}: invalid category")
            domain = "land" if category in LAND else "naval"
            movement = row.get("movementClassId")
            if movement not in self.movement_classes or self.movement_classes[movement]["domain"] != domain:
                raise RosterError(f"archetype {ident}: incompatible movement class")
            template = row.get("runtimeTemplateId")
            if template not in self.templates or self.templates[template]["domain"] != domain:
                raise RosterError(f"archetype {ident}: missing or incompatible runtime template")
            for field, index in (("weaponIds", self.weapons), ("armorIds", self.armor), ("abilityIds", self.abilities)):
                for ref in _unique_ids(row.get(field), f"archetype {ident}.{field}"):
                    if ref not in index:
                        raise RosterError(f"archetype {ident}: broken {field} reference {ref!r}")
                    if category not in index[ref]["compatibleCategories"]:
                        raise RosterError(f"archetype {ident}: incompatible {field} reference {ref!r}")
            for ref in _unique_ids(row.get("formationIds"), f"archetype {ident}.formationIds"):
                if ref not in self.formations or category not in self.formations[ref]["compatibleCategories"]:
                    raise RosterError(f"archetype {ident}: incompatible formation {ref!r}")
            ship_id = row.get("shipId")
            if (category in NAVAL) != (ship_id is not None) or (ship_id is not None and (ship_id not in self.ships or self.ships[ship_id]["category"] != category)):
                raise RosterError(f"archetype {ident}: incompatible ship reference")
            for key in ("strategicStrength", "cost", "upkeep", "supply"):
                _positive(row.get(key), f"archetype {ident}.{key}", allow_zero=key in {"upkeep", "supply"})
            availability = row.get("availability")
            if not isinstance(availability, Mapping) or set(availability) != {"historicalStartYear", "historicalEndYear", "earlyAccessTechnologyIds", "earlyAccessYear"}:
                raise RosterError(f"archetype {ident}: invalid availability")
            start, end, early = availability["historicalStartYear"], availability["historicalEndYear"], availability["earlyAccessYear"]
            if not all(isinstance(x, int) and not isinstance(x, bool) for x in (start, end, early)) or not self.campaign_years["start"] <= early <= start <= end <= self.campaign_years["end"]:
                raise RosterError(f"archetype {ident}: invalid historical availability range")
            self._check_external(row, ident)

    def _check_external(self, row: Mapping[str, Any], ident: str) -> None:
        for field, key in (("technologyIds", "technologies"), ("militaryTraditionIds", "militaryTraditions")):
            values = _unique_ids(row.get(field), f"archetype {ident}.{field}")
            known = self.references.get(key)
            if known is not None and not set(values) <= known:
                raise RosterError(f"archetype {ident}: missing {key} reference")
        early = _unique_ids(row["availability"].get("earlyAccessTechnologyIds"), f"archetype {ident}.earlyAccessTechnologyIds")
        known = self.references.get("technologies")
        if known is not None and not set(early) <= known:
            raise RosterError(f"archetype {ident}: missing early-access technology")
        country = row.get("countryId")
        if country is not None:
            _id(country, f"archetype {ident}.countryId")
            known = self.references.get("countries")
            if known is not None and country not in known:
                raise RosterError(f"archetype {ident}: missing country reference")

    def _validate_relationships(self) -> None:
        graph = {}
        concrete = {i for i, x in self.archetypes.items() if not x.get("abstract")}
        for ident in concrete:
            row = self.archetypes[ident]; graph[ident] = []
            for field in ("upgradeToIds", "replacementIds"):
                for target in _unique_ids(row.get(field), f"archetype {ident}.{field}"):
                    if target not in concrete or target == ident:
                        raise RosterError(f"archetype {ident}: impossible {field} target {target!r}")
                    if self.archetypes[target]["category"] != row["category"]:
                        raise RosterError(f"archetype {ident}: relationship changes category")
                    graph[ident].append(target)
        visiting, done = set(), set()
        def visit(ident):
            if ident in visiting: raise RosterError(f"impossible upgrade chain cycle at {ident!r}")
            if ident not in done:
                visiting.add(ident)
                for child in graph[ident]: visit(child)
                visiting.remove(ident); done.add(ident)
        for ident in sorted(graph): visit(ident)

    def availability(self, archetype_id: str, year: int, completed_technology_ids: set[str]) -> Availability:
        row = self.archetypes.get(archetype_id)
        if row is None or row.get("abstract"):
            raise RosterError(f"unknown concrete archetype {archetype_id!r}")
        availability = row["availability"]
        required = set(row["technologyIds"])
        early_required = set(availability["earlyAccessTechnologyIds"])
        historical = availability["historicalStartYear"] <= year <= availability["historicalEndYear"]
        early = availability["earlyAccessYear"] <= year < availability["historicalStartYear"] and bool(early_required) and early_required <= completed_technology_ids
        unlocked = required <= completed_technology_ids
        distance = min(abs(year - availability["historicalStartYear"]), abs(year - availability["historicalEndYear"]))
        return Availability(unlocked and (historical or early), 100 if historical else max(25, 100 - distance * 5), early and unlocked)

    def generated_unit_data(self) -> list[dict[str, Any]]:
        return [copy.deepcopy(self.archetypes[x]) for x in sorted(self.archetypes) if not self.archetypes[x].get("abstract")]

    def digest(self) -> str:
        raw = json.dumps(self.generated_unit_data(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()


class RosterProjection:
    """Authoritative instance state with derived, non-persistent runtime proxies."""

    def __init__(self, catalog: RosterCatalog, instances: list[Mapping[str, Any]]):
        self.catalog = catalog
        self._state = self.validate_snapshot({"schemaVersion": ROSTER_STATE_VERSION, "instances": instances})
        self._representations: dict[str, list[dict[str, Any]]] = {}

    def validate_snapshot(self, snapshot: Any) -> dict[str, Any]:
        if not isinstance(snapshot, Mapping) or set(snapshot) != {"schemaVersion", "instances"} or snapshot.get("schemaVersion") != 1:
            raise RosterError("roster state must contain schemaVersion 1 and instances")
        indexed = _index(snapshot["instances"], "roster instances")
        output = []
        expected = {"id", "archetypeId", "representedStrength", "regionId", "active", "morale", "discipline", "supply"}
        for ident in sorted(indexed):
            row = indexed[ident]
            if set(row) != expected or row.get("archetypeId") not in self.catalog.archetypes or self.catalog.archetypes[row["archetypeId"]].get("abstract"):
                raise RosterError(f"roster instance {ident}: incompatible fields or archetype")
            for key in ("representedStrength", "morale", "discipline", "supply"):
                _positive(row.get(key), f"roster instance {ident}.{key}", allow_zero=key != "representedStrength")
            if any(row[x] > 100 for x in ("morale", "discipline", "supply")) or not isinstance(row.get("active"), bool):
                raise RosterError(f"roster instance {ident}: invalid operational state")
            _id(row.get("regionId"), f"roster instance {ident}.regionId")
            output.append(copy.deepcopy(row))
        return {"schemaVersion": 1, "instances": output}

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    def project(self, active_region_id: str, global_object_limit: int) -> tuple[dict[str, Any], ...]:
        _positive(global_object_limit, "global object limit", allow_zero=True)
        result = []
        for unit in self._state["instances"]:
            if not unit["active"] or unit["regionId"] != active_region_id: continue
            archetype = self.catalog.archetypes[unit["archetypeId"]]; template = self.catalog.templates[archetype["runtimeTemplateId"]]
            count = min(template["maxActiveObjects"], (unit["representedStrength"] + template["strengthPerObject"] - 1) // template["strengthPerObject"])
            count = min(count, max(0, global_object_limit - len(result)))
            for ordinal in range(count):
                result.append({"instanceId": unit["id"], "ordinal": ordinal, "runtimeTemplateId": archetype["runtimeTemplateId"], "warcraftUnitTypeId": template["warcraftUnitTypeId"]})
        self._representations = {}
        for item in result: self._representations.setdefault(item["instanceId"], []).append(copy.deepcopy(item))
        return tuple(copy.deepcopy(result))

    def lose_representations(self) -> None:
        self._representations = {}

    def restore(self, snapshot: Any) -> None:
        self._state = self.validate_snapshot(snapshot); self._representations = {}

    def derived_modifiers(self, instance_id: str) -> tuple[str, ...]:
        unit = next((x for x in self._state["instances"] if x["id"] == instance_id), None)
        if unit is None: raise RosterError(f"unknown roster instance {instance_id!r}")
        return tuple(sorted(self.catalog.archetypes[unit["archetypeId"]]["abilityIds"]))

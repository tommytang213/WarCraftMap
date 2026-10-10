"""Scenario-neutral, deterministic long-campaign hero progression.

Progression state deliberately contains references to, but never owns, inventory,
relationship, loyalty, title, office, command, or quest state.  Warcraft objects are
disposable projections of this authoritative strategic state.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

SCHEMA_VERSION = 1
WORLD_STATE_KEY = "heroProgressionState"


class HeroProgressionError(ValueError):
    pass


def _index(rows, name):
    if not isinstance(rows, list):
        raise HeroProgressionError(f"{name} must be an array")
    result = {}
    for row in rows:
        ident = row.get("id") if isinstance(row, Mapping) else None
        if not isinstance(ident, str) or not ident or ident in result:
            raise HeroProgressionError(f"{name}: invalid or duplicate id {ident!r}")
        result[ident] = copy.deepcopy(dict(row))
    return result


@dataclass(frozen=True)
class ExperienceResult:
    source_id: str
    awarded: int
    old_level: int
    new_level: int
    levels_gained: int
    skill_points_gained: int
    choice_points_gained: int
    mastery_points_gained: int


class HeroProgressionRuntime:
    """Atomic progression, assignment, injury, and local-representation authority."""

    def __init__(self, catalog, character_ids, *, item_ids=(), quest_ids=(), event_ids=(), office_ids=(), command_ids=()):
        self.catalog = copy.deepcopy(dict(catalog))
        if self.catalog.get("format") != "warcraftmap_hero_progression_v1":
            raise HeroProgressionError("unsupported hero progression format")
        self.cap = self.catalog.get("levelCap")
        if self.cap != 300:
            raise HeroProgressionError("hero level cap must be 300")
        self.sources = _index(self.catalog.get("experienceSources"), "experienceSources")
        self.skills = _index(self.catalog.get("skills"), "skills")
        self.masteries = _index(self.catalog.get("masteries"), "masteries")
        self.abilities = _index(self.catalog.get("abilities"), "abilities")
        self.perks = _index(self.catalog.get("perks"), "perks")
        self.trees = _index(self.catalog.get("personalTrees"), "personalTrees")
        self.profiles = _index(self.catalog.get("characterProfiles"), "characterProfiles")
        self.character_ids = frozenset(character_ids)
        if set(self.profiles) != self.character_ids:
            raise HeroProgressionError("every and only authoritative characters require progression profiles")
        self.refs = {"item": frozenset(item_ids), "quest": frozenset(quest_ids), "event": frozenset(event_ids),
                     "office": frozenset(office_ids), "command": frozenset(command_ids)}
        self._validate_catalog()
        self._state = {ident: self._initial_state(profile) for ident, profile in self.profiles.items()}
        self._runtime_objects = {}

    @staticmethod
    def experience_for_level(level):
        """Cumulative convex curve; exact integer arithmetic through level 300."""
        if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 300:
            raise HeroProgressionError("level must be an integer from 1 through 300")
        n = level - 1
        return 50 * n * (n + 1) + 25 * n * (n - 1) * (2 * n - 1) // 6

    @classmethod
    def level_for_experience(cls, experience):
        if isinstance(experience, bool) or not isinstance(experience, int) or experience < 0:
            raise HeroProgressionError("experience must be a nonnegative integer")
        low, high = 1, 300
        while low < high:
            middle = (low + high + 1) // 2
            if cls.experience_for_level(middle) <= experience: low = middle
            else: high = middle - 1
        return low

    def _validate_catalog(self):
        progression = self.catalog.get("growth", {})
        if progression != {"skillPointEveryLevels": 1, "choicePointEveryLevels": 10, "masteryPointEveryLevels": 5}:
            raise HeroProgressionError("growth cadence must provide frequent growth and regular choices")
        for source in self.sources.values():
            if source.get("kind") not in {"combat", "command", "quest", "office", "exploration", "diplomacy", "craft", "event"}:
                raise HeroProgressionError("invalid experience source kind")
            if not isinstance(source.get("baseAward"), int) or source["baseAward"] <= 0:
                raise HeroProgressionError("experience source award must be a positive integer")
        for perk_id, perk in self.perks.items():
            if perk.get("abilityId") not in self.abilities:
                raise HeroProgressionError(f"perk {perk_id}: missing ability")
            if not 1 <= perk.get("minimumLevel", 0) <= self.cap:
                raise HeroProgressionError(f"perk {perk_id}: invalid minimum level")
            for required in perk.get("prerequisitePerkIds", []):
                if required not in self.perks: raise HeroProgressionError(f"perk {perk_id}: missing prerequisite")
        for tree_id, tree in self.trees.items():
            nodes = tree.get("perkIds", [])
            if not nodes or len(nodes) != len(set(nodes)) or any(x not in self.perks for x in nodes):
                raise HeroProgressionError(f"tree {tree_id}: invalid perks")
        for ident, profile in self.profiles.items():
            level = profile.get("startingLevel")
            if not isinstance(level, int) or not 1 <= level <= self.cap:
                raise HeroProgressionError(f"profile {ident}: invalid starting level")
            if profile.get("personalTreeId") not in self.trees:
                raise HeroProgressionError(f"profile {ident}: missing personal tree")
            for row in profile.get("startingSkills", []):
                if row.get("skillId") not in self.skills or not 0 <= row.get("rank", -1) <= 100:
                    raise HeroProgressionError(f"profile {ident}: invalid skill")
            for row in profile.get("startingMasteries", []):
                if row.get("masteryId") not in self.masteries or not 0 <= row.get("rank", -1) <= 100:
                    raise HeroProgressionError(f"profile {ident}: invalid mastery")
            for unlock in profile.get("scenarioUnlocks", []):
                kind, ref = unlock.get("kind"), unlock.get("id")
                if kind not in self.refs or (self.refs[kind] and ref not in self.refs[kind]):
                    raise HeroProgressionError(f"profile {ident}: invalid scenario unlock")

    def _initial_state(self, profile):
        level = profile["startingLevel"]
        return {"level": level, "experience": self.experience_for_level(level),
                "skillPoints": 0, "choicePoints": 0, "masteryPoints": 0,
                "skills": {x["skillId"]: x["rank"] for x in profile.get("startingSkills", [])},
                "masteries": {x["masteryId"]: x["rank"] for x in profile.get("startingMasteries", [])},
                "perkIds": [], "commandExperience": 0,
                "assignment": {"kind": "reserve", "targetId": None},
                "locationId": profile["startingLocationId"],
                "condition": "ready", "recoveryUntilDay": None}

    def require(self, character_id):
        if character_id not in self._state: raise HeroProgressionError(f"unknown character {character_id!r}")
        return MappingProxyType(copy.deepcopy(self._state[character_id]))

    def award_experience(self, character_id, source_id, *, multiplier=1, command=False):
        if source_id not in self.sources: raise HeroProgressionError(f"unknown experience source {source_id!r}")
        if isinstance(multiplier, bool) or not isinstance(multiplier, int) or multiplier <= 0:
            raise HeroProgressionError("experience multiplier must be a positive integer")
        candidate = copy.deepcopy(self._state); state = candidate.get(character_id)
        if state is None: raise HeroProgressionError(f"unknown character {character_id!r}")
        award = self.sources[source_id]["baseAward"] * multiplier
        old = state["level"]; state["experience"] += award
        state["level"] = self.level_for_experience(state["experience"])
        gained = state["level"] - old
        state["skillPoints"] += gained
        state["choicePoints"] += state["level"] // 10 - old // 10
        state["masteryPoints"] += state["level"] // 5 - old // 5
        if command or self.sources[source_id]["kind"] == "command": state["commandExperience"] += award
        self._state = candidate
        return ExperienceResult(source_id, award, old, state["level"], gained, gained,
                                state["level"] // 10 - old // 10, state["level"] // 5 - old // 5)

    def choose_perk(self, character_id, perk_id):
        candidate = copy.deepcopy(self._state); state = candidate.get(character_id)
        if state is None or perk_id not in self.perks: raise HeroProgressionError("unknown character or perk")
        perk = self.perks[perk_id]; tree = self.trees[self.profiles[character_id]["personalTreeId"]]
        if perk_id not in tree["perkIds"] or perk_id in state["perkIds"]: raise HeroProgressionError("perk is unavailable")
        if state["choicePoints"] < 1 or state["level"] < perk["minimumLevel"] or not set(perk.get("prerequisitePerkIds", [])) <= set(state["perkIds"]):
            raise HeroProgressionError("perk prerequisites are not met")
        state["choicePoints"] -= 1; state["perkIds"].append(perk_id); state["perkIds"].sort(); self._state = candidate

    def improve_skill(self, character_id, skill_id):
        candidate = copy.deepcopy(self._state); state = candidate.get(character_id)
        if state is None or skill_id not in self.skills or state["skillPoints"] < 1: raise HeroProgressionError("skill improvement is unavailable")
        if state["skills"].get(skill_id, 0) >= 100: raise HeroProgressionError("skill is already at maximum")
        state["skillPoints"] -= 1; state["skills"][skill_id] = state["skills"].get(skill_id, 0) + 1; self._state = candidate

    def improve_mastery(self, character_id, mastery_id):
        candidate = copy.deepcopy(self._state); state = candidate.get(character_id)
        if state is None or mastery_id not in self.masteries or state["masteryPoints"] < 1: raise HeroProgressionError("mastery improvement is unavailable")
        if state["masteries"].get(mastery_id, 0) >= 100: raise HeroProgressionError("mastery is already at maximum")
        state["masteryPoints"] -= 1; state["masteries"][mastery_id] = state["masteries"].get(mastery_id, 0) + 1; self._state = candidate

    def comparison_card(self, character_id, *, equipment=(), relationships=(), loyalty=None,
                        titles=(), offices=(), commands=(), quest_unlocks=()):
        """UI-ready projection; external axes remain owned by their native systems."""
        state = self.require(character_id)
        return {"characterId": character_id, "level": state["level"], "experience": state["experience"],
                "nextLevelExperience": None if state["level"] == self.cap else self.experience_for_level(state["level"] + 1),
                "skills": dict(state["skills"]), "masteries": dict(state["masteries"]), "perkIds": list(state["perkIds"]),
                "commandExperience": state["commandExperience"], "equipment": list(equipment),
                "relationships": list(relationships), "loyalty": loyalty, "titles": list(titles),
                "offices": list(offices), "commands": list(commands), "questUnlocks": list(quest_unlocks)}

    def assign(self, character_id, kind, target_id, location_id):
        if kind not in {"field", "governor", "adviser", "army_command", "fleet_command", "specialist", "reserve"}:
            raise HeroProgressionError("invalid assignment kind")
        if not isinstance(location_id, str) or not location_id: raise HeroProgressionError("assignment requires one authoritative location")
        candidate = copy.deepcopy(self._state); state = candidate.get(character_id)
        if state is None or state["condition"] != "ready": raise HeroProgressionError("character cannot be assigned")
        state["assignment"] = {"kind": kind, "targetId": target_id}; state["locationId"] = location_id; self._state = candidate

    def defeat(self, character_id, current_day, recovery_days=30, *, permanent_death=False):
        if permanent_death: raise HeroProgressionError("permanent death requires a separate explicit campaign rule")
        if not isinstance(current_day, int) or not isinstance(recovery_days, int) or recovery_days <= 0: raise HeroProgressionError("invalid recovery schedule")
        candidate = copy.deepcopy(self._state); state = candidate.get(character_id)
        if state is None: raise HeroProgressionError("unknown character")
        if state["condition"] == "wounded": return
        state["condition"] = "wounded"; state["recoveryUntilDay"] = current_day + recovery_days
        state["assignment"] = {"kind": "reserve", "targetId": None}; self._state = candidate
        self._runtime_objects.pop(character_id, None)

    def recover(self, through_day):
        candidate = copy.deepcopy(self._state); recovered = []
        for ident, state in candidate.items():
            if state["condition"] == "wounded" and state["recoveryUntilDay"] <= through_day:
                state["condition"] = "ready"; state["recoveryUntilDay"] = None; recovered.append(ident)
        self._state = candidate; return tuple(sorted(recovered))

    def instantiate_local_group(self, location_id, factory, *, budget=32):
        ids = [x for x, state in sorted(self._state.items()) if state["condition"] == "ready" and state["locationId"] == location_id and state["assignment"]["kind"] == "field"]
        if len(ids) > budget: raise HeroProgressionError(f"local hero group exceeds finalized budget {budget}")
        self._runtime_objects = {ident: factory(ident, self.require(ident)) for ident in ids}
        return MappingProxyType(dict(self._runtime_objects))

    def snapshot(self):
        return {"schemaVersion": SCHEMA_VERSION, "characters": [{"id": ident, **copy.deepcopy(state)} for ident, state in sorted(self._state.items())]}

    def restore(self, snapshot):
        if not isinstance(snapshot, Mapping) or snapshot.get("schemaVersion") != SCHEMA_VERSION: raise HeroProgressionError("unsupported progression snapshot")
        rows = _index(snapshot.get("characters"), "characters")
        if set(rows) != self.character_ids: raise HeroProgressionError("progression snapshot character coverage mismatch")
        candidate = {}
        for ident, row in rows.items():
            row.pop("id"); level = row.get("level"); xp = row.get("experience")
            if self.level_for_experience(xp) != level: raise HeroProgressionError(f"character {ident}: level and experience disagree")
            if row.get("condition") not in {"ready", "wounded"}: raise HeroProgressionError("invalid condition")
            candidate[ident] = row
        self._state = candidate; self._runtime_objects = {}

    def migrate_legacy_world(self, world):
        result = copy.deepcopy(dict(world)); result.setdefault(WORLD_STATE_KEY, self.snapshot()); return result


class HeroProgressionSaveAdapter:
    """Two-phase save/load adapter suitable for cross-map reconstruction."""

    def __init__(self, runtime, world_state):
        self.runtime = runtime; self.world_state = copy.deepcopy(dict(world_state))

    def capture_world(self):
        result = copy.deepcopy(self.world_state); result[WORLD_STATE_KEY] = self.runtime.snapshot(); return result

    def migrate_legacy_world(self, candidate):
        return self.runtime.migrate_legacy_world(candidate)

    def reconstruct(self, candidate):
        if not isinstance(candidate, Mapping) or WORLD_STATE_KEY not in candidate:
            raise HeroProgressionError(f"world state is missing {WORLD_STATE_KEY}")
        probe = copy.deepcopy(self.runtime); probe.restore(candidate[WORLD_STATE_KEY]); return probe.snapshot()

    def activate(self, candidate, reconstructed):
        if reconstructed != self.reconstruct(candidate): raise HeroProgressionError("reconstructed progression does not match candidate")
        self.runtime.restore(candidate[WORLD_STATE_KEY]); self.world_state = copy.deepcopy(dict(candidate))

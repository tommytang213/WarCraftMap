"""Scenario-neutral authoritative character and relationship simulation.

Definitions are copied once and exposed as frozen values.  Mutable campaign state
contains stable IDs and JSON values only; Warcraft objects are reconstructible views.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable, Mapping

CHARACTER_STATE_SCHEMA_VERSION = 1
CHARACTER_WORLD_STATE_KEY = "characterState"
_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_SCORE_MIN, _SCORE_MAX = -100, 100


class CharacterError(ValueError):
    pass


@dataclass(frozen=True)
class ThresholdEvent:
    event_type: str
    threshold_id: str
    scope: str
    subject_ids: tuple[str, ...]
    content_id: str
    active: bool
    score: float

    def to_dict(self):
        return {"type": self.event_type, "thresholdId": self.threshold_id,
                "scope": self.scope, "subjectIds": list(self.subject_ids),
                "contentId": self.content_id, "active": self.active, "score": self.score}


@dataclass(frozen=True)
class CharacterDefinition:
    id: str
    display_name: str
    biography: str
    initial_trait_ids: tuple[str, ...]
    initial_skills: tuple[tuple[str, float], ...]
    initial_profession_ids: tuple[str, ...]
    personal_quest_ids: tuple[str, ...]
    recruitment_costs: tuple[tuple[str, float], ...]
    reward_ids: tuple[str, ...]
    title_grant_ids: tuple[str, ...]
    runtime_template_id: str | None


@dataclass(frozen=True)
class CharacterView:
    definition: CharacterDefinition
    allegiance_polity_id: str | None
    available: bool
    recruited: bool
    active: bool
    loyalty: float
    permanent_state: str
    trait_ids: tuple[str, ...]
    skills: Mapping
    profession_ids: tuple[str, ...]

    @property
    def id(self):
        return self.definition.id


def _stable_id(value, context, *, optional=False):
    if optional and value is None:
        return None
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise CharacterError(f"{context}: invalid stable ID {value!r}")
    return value


def _index(values, domain):
    if not isinstance(values, list):
        raise CharacterError(f"{domain}: must be an array")
    result = {}
    for value in values:
        if not isinstance(value, Mapping):
            raise CharacterError(f"{domain}: every entry must be an object")
        ident = _stable_id(value.get("id"), f"{domain}.id")
        if ident in result:
            raise CharacterError(f"{domain}: duplicate ID {ident!r}")
        result[ident] = value
    return result


def _number(value, context, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not minimum <= value <= maximum:
        raise CharacterError(f"{context}: must be a number between {minimum} and {maximum}")
    return value


def _ids(values, context, catalog):
    if not isinstance(values, list):
        raise CharacterError(f"{context}: must be an array")
    result = []
    for value in values:
        ident = _stable_id(value, context)
        if ident in result:
            raise CharacterError(f"{context}: duplicate reference {ident!r}")
        if ident not in catalog:
            raise CharacterError(f"{context}: missing reference {ident!r}")
        result.append(ident)
    return tuple(sorted(result))


class CharacterRuntime:
    """Deterministic character state machine with atomic validated transitions."""

    def __init__(self, world_definitions, *, reference_catalogs=None):
        world = copy.deepcopy(dict(world_definitions))
        catalogs = dict(reference_catalogs or {})
        self._polities = frozenset(catalogs.get("polities", (x.get("id") for x in world.get("polities", []))))
        self._titles = frozenset(catalogs.get("title_grants", (x.get("id") for x in world.get("titleGrants", []))))
        traits, skills, professions = (_index(world.get(key, []), key) for key in ("traits", "skills", "professions"))
        self._trait_ids, self._skill_ids, self._profession_ids = frozenset(traits), frozenset(skills), frozenset(professions)
        quests = _index(world.get("personalQuests", []), "personalQuests")
        records = _index(world.get("characters", []), "characters")
        self._definitions = []
        initial = {}
        for ident, value in records.items():
            text = (value.get("displayName"), value.get("biography"))
            if any(not isinstance(x, str) or not x.strip() for x in text):
                raise CharacterError(f"character {ident}: displayName and biography must be non-empty")
            trait_ids = _ids(value.get("traitIds"), f"character {ident}.traitIds", traits)
            profession_ids = _ids(value.get("professionIds"), f"character {ident}.professionIds", professions)
            quest_ids = _ids(value.get("personalQuestIds"), f"character {ident}.personalQuestIds", quests)
            rating_records = value.get("skills")
            if not isinstance(rating_records, list):
                raise CharacterError(f"character {ident}.skills: must be an array")
            ratings = {}
            for rating in rating_records:
                if not isinstance(rating, Mapping):
                    raise CharacterError(f"character {ident}.skills: entries must be objects")
                skill_id = _stable_id(rating.get("skillId"), f"character {ident}.skills.skillId")
                if skill_id not in skills:
                    raise CharacterError(f"character {ident}.skills: missing skill {skill_id!r}")
                if skill_id in ratings:
                    raise CharacterError(f"character {ident}.skills: duplicate skill {skill_id!r}")
                ratings[skill_id] = _number(rating.get("rating"), f"character {ident}.skills {skill_id}", 0, 100)
            allegiance = _stable_id(value.get("allegiancePolityId"), f"character {ident}.allegiancePolityId", optional=True)
            if allegiance is not None and allegiance not in self._polities:
                raise CharacterError(f"character {ident}: missing polity {allegiance!r}")
            loyalty = value.get("loyalty")
            if not isinstance(loyalty, Mapping) or loyalty.get("permanentState") not in {"none", "oathbound"}:
                raise CharacterError(f"character {ident}.loyalty: invalid state")
            costs = value.get("recruitmentCosts", [])
            if not isinstance(costs, list):
                raise CharacterError(f"character {ident}.recruitmentCosts: must be an array")
            parsed_costs = []
            for cost in costs:
                if not isinstance(cost, Mapping):
                    raise CharacterError(f"character {ident}.recruitmentCosts: entries must be objects")
                resource_id = _stable_id(cost.get("resourceId"), f"character {ident}.recruitmentCosts.resourceId")
                amount = _number(cost.get("amount"), f"character {ident}.recruitmentCosts.amount", 0, float("inf"))
                if any(x[0] == resource_id for x in parsed_costs):
                    raise CharacterError(f"character {ident}.recruitmentCosts: duplicate resource {resource_id!r}")
                parsed_costs.append((resource_id, amount))
            reward_ids = tuple(sorted(_stable_id(x, f"character {ident}.rewardIds") for x in value.get("rewardIds", [])))
            title_ids = tuple(sorted(_stable_id(x, f"character {ident}.titleGrantIds") for x in value.get("titleGrantIds", [])))
            missing_titles = set(title_ids) - self._titles
            if missing_titles:
                raise CharacterError(f"character {ident}: missing title grant {sorted(missing_titles)[0]!r}")
            definition = CharacterDefinition(ident, text[0], text[1], trait_ids,
                tuple(sorted(ratings.items())), profession_ids, quest_ids,
                tuple(sorted(parsed_costs)), reward_ids, title_ids,
                _stable_id(value.get("runtimeTemplateId"), f"character {ident}.runtimeTemplateId", optional=True))
            self._definitions.append(definition)
            initial[ident] = {"allegiancePolityId": allegiance, "available": value.get("available", True),
                "recruited": value.get("recruited", False), "active": value.get("active", True),
                "loyalty": _number(loyalty.get("score"), f"character {ident}.loyalty.score", -100, 100),
                "permanentState": loyalty["permanentState"], "traitIds": list(trait_ids),
                "skills": dict(ratings), "professionIds": list(profession_ids)}
            for field in ("available", "recruited", "active"):
                if not isinstance(initial[ident][field], bool):
                    raise CharacterError(f"character {ident}.{field}: must be boolean")
            if initial[ident]["recruited"] and not initial[ident]["available"]:
                raise CharacterError(f"character {ident}: recruited character must be available")
        self._definitions = tuple(sorted(self._definitions, key=lambda x: x.id))
        self._by_id = MappingProxyType({x.id: x for x in self._definitions})
        self._thresholds = self._parse_thresholds(world.get("relationshipThresholds", []))
        self._relationships, self._relationship_pairs = self._parse_relationships(world.get("companionRelationships", []), records)
        self._state = initial
        self._runtime_objects = {}

    def _parse_thresholds(self, values):
        records = _index(values, "relationshipThresholds"); result = []
        allowed = {"buff", "debuff", "content_unlock", "unlock", "synergy", "friction", "content_availability"}
        for ident, value in records.items():
            scope = value.get("scope")
            if scope not in {"loyalty", "companion_relationship"}:
                raise CharacterError(f"relationship threshold {ident}: invalid scope")
            low = _number(value.get("minimum"), f"relationship threshold {ident}.minimum", -100, 100)
            high = _number(value.get("maximum"), f"relationship threshold {ident}.maximum", -100, 100)
            if low > high:
                raise CharacterError(f"relationship threshold {ident}: minimum cannot exceed maximum")
            consequences = value.get("consequences")
            if not isinstance(consequences, list) or not consequences:
                raise CharacterError(f"relationship threshold {ident}: consequences must be non-empty")
            parsed = []
            for consequence in consequences:
                if not isinstance(consequence, Mapping) or consequence.get("kind") not in allowed:
                    raise CharacterError(f"relationship threshold {ident}: invalid consequence")
                parsed.append((consequence["kind"], _stable_id(consequence.get("contentId"), f"relationship threshold {ident}.contentId")))
            result.append((ident, scope, low, high, tuple(parsed)))
        return tuple(sorted(result))

    def _parse_relationships(self, values, characters):
        records = _index(values, "companionRelationships"); result, pairs = {}, {}
        for ident, value in records.items():
            first, second = value.get("characterAId"), value.get("characterBId")
            if first not in characters or second not in characters:
                raise CharacterError(f"companion relationship {ident}: missing character")
            if first == second:
                raise CharacterError(f"companion relationship {ident}: self relationship")
            pair = tuple(sorted((first, second)))
            if pair in pairs:
                raise CharacterError(f"companion relationship {ident}: duplicate companion pair")
            result[ident] = {"characterAId": pair[0], "characterBId": pair[1],
                             "score": _number(value.get("score"), f"companion relationship {ident}.score", -100, 100)}
            pairs[pair] = ident
        return result, pairs

    @property
    def definitions(self):
        return self._definitions

    def ids(self, active_only=False):
        return tuple(x.id for x in self._definitions if not active_only or self._state[x.id]["active"])

    def require(self, character_id):
        if character_id not in self._by_id:
            raise CharacterError(f"unknown character {character_id!r}")
        state = self._state[character_id]
        return CharacterView(self._by_id[character_id], state["allegiancePolityId"], state["available"],
            state["recruited"], state["active"], state["loyalty"], state["permanentState"],
            tuple(state["traitIds"]), MappingProxyType(dict(state["skills"])), tuple(state["professionIds"]))

    def _mutate(self, character_id, operation):
        self.require(character_id); candidate = copy.deepcopy(self._state)
        events = operation(candidate[character_id]) or ()
        self._validate_character_state(character_id, candidate[character_id])
        self._state = candidate
        return tuple(events)

    def _validate_character_state(self, ident, state):
        expected = {"allegiancePolityId", "available", "recruited", "active", "loyalty", "permanentState", "traitIds", "skills", "professionIds"}
        if set(state) != expected:
            raise CharacterError(f"character state {ident}: invalid fields")
        if state["allegiancePolityId"] is not None and state["allegiancePolityId"] not in self._polities:
            raise CharacterError(f"character state {ident}: missing polity")
        for field in ("available", "recruited", "active"):
            if not isinstance(state[field], bool): raise CharacterError(f"character state {ident}.{field}: must be boolean")
        if state["recruited"] and (not state["available"] or not state["active"]):
            raise CharacterError(f"character state {ident}: recruited character must be active and available")
        _number(state["loyalty"], f"character state {ident}.loyalty", -100, 100)
        if state["permanentState"] not in {"none", "oathbound"}: raise CharacterError(f"character state {ident}: invalid permanent state")
        for field, catalog in (("traitIds", self._trait_ids), ("professionIds", self._profession_ids)):
            if not isinstance(state[field], list) or len(state[field]) != len(set(state[field])): raise CharacterError(f"character state {ident}.{field}: invalid references")
            for ref in state[field]:
                _stable_id(ref, f"character state {ident}.{field}")
                if ref not in catalog: raise CharacterError(f"character state {ident}.{field}: missing reference {ref!r}")
        if not isinstance(state["skills"], dict): raise CharacterError(f"character state {ident}.skills: must be an object")
        for ref, rating in state["skills"].items():
            _stable_id(ref, f"character state {ident}.skills")
            if ref not in self._skill_ids: raise CharacterError(f"character state {ident}.skills: missing reference {ref!r}")
            _number(rating, f"character state {ident}.skills.{ref}", 0, 100)

    def _require_mutable(self, state, action):
        if not state["active"]: raise CharacterError(f"cannot {action} inactive character")

    def recruit(self, character_id):
        def change(state):
            self._require_mutable(state, "recruit")
            if not state["available"]: raise CharacterError("character is unavailable")
            if state["recruited"]: raise CharacterError("character is already recruited")
            state["recruited"] = True
        return self._mutate(character_id, change)

    def dismiss(self, character_id):
        def change(state):
            self._require_mutable(state, "dismiss")
            if state["permanentState"] == "oathbound": raise CharacterError("oathbound character cannot be dismissed")
            if not state["recruited"]: raise CharacterError("character is not recruited")
            state["recruited"] = False
        return self._mutate(character_id, change)

    def set_allegiance(self, character_id, polity_id):
        if polity_id is not None:
            _stable_id(polity_id, "allegiance polity");
            if polity_id not in self._polities: raise CharacterError(f"missing polity {polity_id!r}")
        def change(state):
            self._require_mutable(state, "change allegiance")
            if state["permanentState"] == "oathbound" and polity_id != state["allegiancePolityId"]: raise CharacterError("oathbound allegiance cannot change")
            if polity_id == state["allegiancePolityId"]: raise CharacterError("allegiance transition must change polity")
            state["allegiancePolityId"] = polity_id
        return self._mutate(character_id, change)

    def set_available(self, character_id, available):
        if not isinstance(available, bool): raise CharacterError("availability must be boolean")
        def change(state):
            self._require_mutable(state, "change availability")
            if not available and state["permanentState"] == "oathbound": raise CharacterError("oathbound character cannot become unavailable")
            if not available and state["recruited"]: raise CharacterError("recruited character cannot become unavailable")
            state["available"] = available
        return self._mutate(character_id, change)

    def set_active(self, character_id, active):
        if not isinstance(active, bool): raise CharacterError("active status must be boolean")
        def change(state):
            if not active and state["permanentState"] == "oathbound": raise CharacterError("oathbound character cannot be deactivated")
            if not active and state["recruited"]: raise CharacterError("recruited character cannot be deactivated")
            state["active"] = active
        return self._mutate(character_id, change)

    def change_loyalty(self, character_id, delta):
        if isinstance(delta, bool) or not isinstance(delta, (int, float)): raise CharacterError("loyalty delta must be numeric")
        def change(state):
            self._require_mutable(state, "change loyalty")
            if state["permanentState"] == "oathbound" and delta < 0: raise CharacterError("oathbound loyalty cannot regress")
            old = state["loyalty"]; state["loyalty"] = _number(old + delta, "loyalty result", -100, 100)
            return self._threshold_events("loyalty", (character_id,), old, state["loyalty"])
        return self._mutate(character_id, change)

    def enter_oathbound(self, character_id):
        def change(state):
            self._require_mutable(state, "enter oathbound")
            if not state["recruited"]: raise CharacterError("only a recruited character can become oathbound")
            if state["permanentState"] != "none": raise CharacterError("invalid permanent loyalty transition")
            state["permanentState"] = "oathbound"
        return self._mutate(character_id, change)

    def set_relationship(self, first, second, score):
        pair = tuple(sorted((first, second))); relationship_id = self._relationship_pairs.get(pair)
        if relationship_id is None: raise CharacterError(f"undefined companion relationship {pair!r}")
        _number(score, "relationship score", -100, 100)
        if not all(self.require(x).active for x in pair): raise CharacterError("relationship participants must be active")
        candidate = copy.deepcopy(self._relationships); old = candidate[relationship_id]["score"]
        candidate[relationship_id]["score"] = score; self._relationships = candidate
        return self._threshold_events("companion_relationship", pair, old, score)

    def change_relationship(self, first, second, delta):
        if isinstance(delta, bool) or not isinstance(delta, (int, float)): raise CharacterError("relationship delta must be numeric")
        pair = tuple(sorted((first, second))); relationship_id = self._relationship_pairs.get(pair)
        if relationship_id is None: raise CharacterError(f"undefined companion relationship {pair!r}")
        return self.set_relationship(first, second, self._relationships[relationship_id]["score"] + delta)

    def relationship_score(self, first, second):
        ident = self._relationship_pairs.get(tuple(sorted((first, second))))
        if ident is None: raise CharacterError("undefined companion relationship")
        return self._relationships[ident]["score"]

    def set_skill(self, character_id, skill_id, rating):
        _stable_id(skill_id, "skill ID"); _number(rating, "skill rating", 0, 100)
        if skill_id not in self._skill_ids: raise CharacterError(f"missing skill {skill_id!r}")
        def change(state): self._require_mutable(state, "change skill"); state["skills"][skill_id] = rating
        return self._mutate(character_id, change)

    def add_trait(self, character_id, trait_id): return self._change_member(character_id, "traitIds", trait_id, True)
    def remove_trait(self, character_id, trait_id): return self._change_member(character_id, "traitIds", trait_id, False)
    def add_profession(self, character_id, profession_id): return self._change_member(character_id, "professionIds", profession_id, True)
    def remove_profession(self, character_id, profession_id): return self._change_member(character_id, "professionIds", profession_id, False)

    def _change_member(self, character_id, field, ident, add):
        _stable_id(ident, field)
        catalog = self._trait_ids if field == "traitIds" else self._profession_ids
        if ident not in catalog: raise CharacterError(f"missing attribute {ident!r}")
        def change(state):
            self._require_mutable(state, "change character attributes")
            exists = ident in state[field]
            if exists == add: raise CharacterError("attribute transition must change state")
            if not add and state["permanentState"] == "oathbound": raise CharacterError("oathbound attributes cannot be removed")
            if add: state[field].append(ident); state[field].sort()
            else: state[field].remove(ident)
        return self._mutate(character_id, change)

    def _threshold_events(self, scope, subjects, old, new):
        events = []
        for threshold_id, threshold_scope, low, high, consequences in self._thresholds:
            if threshold_scope != scope: continue
            was, now = low <= old <= high, low <= new <= high
            if was == now: continue
            for kind, content_id in consequences:
                events.append(ThresholdEvent(kind, threshold_id, scope, tuple(subjects), content_id, now, new))
        return tuple(events)

    def snapshot(self):
        return {"schemaVersion": CHARACTER_STATE_SCHEMA_VERSION,
            "characters": [{"id": ident, **copy.deepcopy(self._state[ident])} for ident in sorted(self._state)],
            "relationships": [{"id": ident, **copy.deepcopy(self._relationships[ident])} for ident in sorted(self._relationships)]}

    def validate_snapshot(self, candidate):
        if not isinstance(candidate, Mapping) or candidate.get("schemaVersion") != CHARACTER_STATE_SCHEMA_VERSION:
            raise CharacterError("character state schemaVersion must be 1")
        characters = candidate.get("characters"); relationships = candidate.get("relationships")
        if not isinstance(characters, list) or not isinstance(relationships, list): raise CharacterError("character state collections must be arrays")
        restored = {}
        for record in characters:
            if not isinstance(record, Mapping): raise CharacterError("character state entries must be objects")
            ident = record.get("id")
            if ident in restored: raise CharacterError(f"character state: duplicate ID {ident!r}")
            if ident not in self._by_id: raise CharacterError(f"character state: incompatible character {ident!r}")
            state = copy.deepcopy(dict(record)); state.pop("id", None); self._validate_character_state(ident, state); restored[ident] = state
            current = self._state[ident]
            if current["permanentState"] == "oathbound":
                if state["permanentState"] != "oathbound": raise CharacterError("oathbound state cannot be removed")
                if state["loyalty"] < current["loyalty"]: raise CharacterError("oathbound loyalty cannot regress")
                if not state["recruited"] or not state["available"] or not state["active"]: raise CharacterError("oathbound character cannot be removed")
                if state["allegiancePolityId"] != current["allegiancePolityId"]: raise CharacterError("oathbound allegiance cannot change")
                if not set(current["traitIds"]).issubset(state["traitIds"]) or not set(current["professionIds"]).issubset(state["professionIds"]): raise CharacterError("oathbound attributes cannot be removed")
        missing = set(self._by_id) - set(restored)
        if missing: raise CharacterError(f"character state: missing character {sorted(missing)[0]!r}")
        restored_relationships = {}
        for record in relationships:
            if not isinstance(record, Mapping) or set(record) != {"id", "characterAId", "characterBId", "score"}: raise CharacterError("relationship state entry has invalid fields")
            ident = record.get("id")
            if ident in restored_relationships: raise CharacterError(f"relationship state: duplicate ID {ident!r}")
            if ident not in self._relationships: raise CharacterError(f"relationship state: incompatible relationship {ident!r}")
            expected = self._relationships[ident]
            if (record["characterAId"], record["characterBId"]) != (expected["characterAId"], expected["characterBId"]): raise CharacterError("relationship state pair is incompatible")
            restored_relationships[ident] = copy.deepcopy(dict(record)); restored_relationships[ident].pop("id")
            _number(record["score"], f"relationship state {ident}.score", -100, 100)
        if set(restored_relationships) != set(self._relationships): raise CharacterError("relationship state is incomplete")
        return restored, restored_relationships

    def restore(self, candidate):
        characters, relationships = self.validate_snapshot(candidate)
        self._state, self._relationships = characters, relationships; self._runtime_objects = {}

    def reconstruct_runtime(self, factory: Callable[[CharacterDefinition, CharacterView], object]):
        """Recreate local representations; returned objects never enter snapshots."""
        rebuilt = {}
        for ident in self.ids(active_only=True):
            view = self.require(ident)
            if view.recruited and view.definition.runtime_template_id is not None:
                rebuilt[ident] = factory(view.definition, view)
        self._runtime_objects = rebuilt
        return MappingProxyType(dict(rebuilt))

    def lose_runtime_representation(self, character_id):
        self.require(character_id); return self._runtime_objects.pop(character_id, None) is not None


class CharacterSaveAdapter:
    def __init__(self, runtime, world_state): self.runtime, self.world_state = runtime, copy.deepcopy(dict(world_state))
    def capture_world(self):
        result = copy.deepcopy(self.world_state); result[CHARACTER_WORLD_STATE_KEY] = self.runtime.snapshot(); return result
    def migrate_legacy_world(self, candidate):
        if not isinstance(candidate, Mapping): raise CharacterError("legacy world state must be an object")
        migrated = copy.deepcopy(dict(candidate)); migrated.setdefault(CHARACTER_WORLD_STATE_KEY, self.runtime.snapshot()); self.validate_world(migrated); return migrated
    def validate_world(self, candidate):
        if not isinstance(candidate, Mapping) or CHARACTER_WORLD_STATE_KEY not in candidate: raise CharacterError(f"world state is missing {CHARACTER_WORLD_STATE_KEY}")
        self.runtime.validate_snapshot(candidate[CHARACTER_WORLD_STATE_KEY])
    def reconstruct(self, candidate): self.validate_world(candidate); return self.runtime.validate_snapshot(candidate[CHARACTER_WORLD_STATE_KEY])
    def activate(self, candidate, reconstructed):
        if reconstructed != self.runtime.validate_snapshot(candidate[CHARACTER_WORLD_STATE_KEY]): raise CharacterError("reconstructed character state does not match candidate")
        self.runtime.restore(candidate[CHARACTER_WORLD_STATE_KEY]); self.world_state = copy.deepcopy(dict(candidate))

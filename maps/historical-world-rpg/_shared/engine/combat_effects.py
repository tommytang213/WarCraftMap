"""Typed combat ratings, shared by represented and abstract combat.

Profiles are compiled from authoritative roster metadata, never inferred from
tradition eligibility or a Warcraft proxy's appearance. All arithmetic stays
rational until the caller commits damage/casualties. No effect is save state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from military_tradition import MilitaryTraditionRuntime, RecordingTraditionAdapter


class CombatBindingError(ValueError):
    pass


def _index(rows, label):
    if not isinstance(rows, list) or not rows:
        raise CombatBindingError(f"{label}: expected nonempty definitions")
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"] or row["id"] in result:
            raise CombatBindingError(f"{label}: missing/duplicate identity")
        result[row["id"]] = row
    return result


def _fields(row, names):
    if not isinstance(row, dict) or set(row) != set(names):
        raise CombatBindingError("unknown or missing combat binding metadata (release blocker)")


def verify_executable_bindings(source, expected):
    """Reject additions as well as omissions/changes to generated consumers."""
    def calls(text):
        return [line for line in text.splitlines() if any(token in line for token in
                ('bindings.addAttribute(', 'bindings.addEffect(', 'bindings.addProfile(', '.contributions.replace('))]
    if calls(source) != calls(expected):
        raise CombatBindingError("executable combat bindings differ from scenario (release blocker)")


@dataclass
class CombatHit:
    """One damage delivery; reuse this receipt for duplicate callback delivery.

    Death/casualty notifications consume the resulting loss, never its damage
    modifier again. Receipts are transient and must be retired on reconstruction.
    """
    base: Fraction
    attack_id: str
    result: Fraction | None = field(default=None, init=False)


class CombatCatalogue:
    def __init__(self, data, traditions, roster):
        _fields(data, ('format', 'schemaVersion', 'balanceNote', 'attackPredicates', 'effects', 'attributes'))
        if data.get("format") != "warcraftmap_combat_effect_bindings_v1" or data.get("schemaVersion") != 1:
            raise CombatBindingError("unsupported combat-effect binding catalogue")
        MilitaryTraditionRuntime(traditions, RecordingTraditionAdapter())
        self.data = data
        self.predicates = _index(data["attackPredicates"], "attack predicates")
        self.effects = _index(data["effects"], "effects")
        self.attributes = _index(data["attributes"], "attributes")
        expected_effects, expected_attributes = {}, {}
        for tradition in traditions["traditions"]:
            for milestone in tradition["milestones"]:
                effect = milestone["effect"]
                expected_effects[effect["effectId"]] = dict(
                    categoryId=tradition["categoryId"], milestoneId=milestone["id"],
                    threshold=milestone["threshold"], mode=effect["mode"], replacesEffectId=effect["replacesEffectId"])
            for coefficient in tradition["coefficients"]:
                expected_attributes[coefficient["attributeId"]] = dict(categoryId=tradition["categoryId"],
                    numerator=coefficient["numerator"], denominator=coefficient["denominator"])
        if self.effects.keys() != expected_effects.keys() or self.attributes.keys() != expected_attributes.keys():
            raise CombatBindingError("omitted or unknown tradition effect/attribute binding")
        sources = set()
        for ident, expected in expected_effects.items():
            row = self.effects[ident]
            _fields(row, ('id', 'sourceId', 'categoryId', 'milestoneId', 'threshold', 'mode', 'replacesEffectId', 'description', 'contributions'))
            if any(row.get(key) != value for key, value in expected.items()):
                raise CombatBindingError(f"{ident}: mislabeled milestone binding")
            if not row.get("sourceId") or row["sourceId"] in sources or not row.get("description"):
                raise CombatBindingError(f"{ident}: missing/duplicate source or description")
            sources.add(row["sourceId"])
            seen = set()
            if not row.get("contributions"):
                raise CombatBindingError(f"{ident}: empty combat effect")
            for contribution in row["contributions"]:
                _fields(contribution, ('stat', 'attackId', 'basisPoints'))
                key = (contribution.get("stat"), contribution.get("attackId"))
                value = contribution.get("basisPoints")
                if (key in seen or key[0] not in {"damage", "resistance"} or key[1] not in self.predicates
                        or type(value) is not int or value < 0
                        or self.predicates[key[1]]["categoryId"] != row["categoryId"]):
                    raise CombatBindingError(f"{ident}: invalid typed contribution")
                seen.add(key)
        for ident, expected in expected_attributes.items():
            row = self.attributes[ident]
            _fields(row, ('id', 'categoryId', 'numerator', 'denominator', 'attackId'))
            if any(row.get(key) != value for key, value in expected.items()):
                raise CombatBindingError(f"{ident}: coefficient differs from tradition authority")
            if row.get("attackId") is not None and (row["attackId"] not in self.predicates or
                    self.predicates[row["attackId"]]["categoryId"] != row["categoryId"]):
                raise CombatBindingError(f"{ident}: unknown attack consumer")
        for row in self.predicates.values():
            _fields(row, ('id', 'categoryId', 'weaponIds', 'abilityIds', 'rosterCategories', 'movementClassIds', 'requiresShip', 'nativeTemplates'))
            if type(row["requiresShip"]) is not bool or not isinstance(row["nativeTemplates"], dict):
                raise CombatBindingError("invalid weapon predicate")
            if (not row.get("weaponIds") or not set(row["weaponIds"]) <= roster.weapons.keys()
                    or not row.get("abilityIds") or not set(row["abilityIds"]) <= roster.abilities.keys()
                    or not set(row["rosterCategories"]) <= {u.get("category") for u in roster.archetypes.values()}
                    or not set(row["movementClassIds"]) <= roster.movement_classes.keys()
                    or row["categoryId"] not in {r["id"] for r in traditions["categories"]}):
                raise CombatBindingError("unknown weapon/ability/role metadata (release blocker)")
            for template, native in row["nativeTemplates"].items():
                if template not in roster.templates or native not in {"normal", "pierce", "siege"}:
                    raise CombatBindingError("unknown native weapon binding (release blocker)")
        self.profiles = {}
        for ident, unit in sorted(roster.archetypes.items()):
            if unit.get("abstract"):
                continue
            attacks = []
            for attack_id, predicate in self.predicates.items():
                tradition = next(t for t in traditions["traditions"] if t["categoryId"] == predicate["categoryId"])
                if (unit["category"] in predicate["rosterCategories"]
                        and unit["movementClassId"] in predicate["movementClassIds"]
                        and set(unit["weaponIds"]) & set(predicate["weaponIds"])
                        and set(predicate["abilityIds"]) <= set(unit["abilityIds"])
                        and tradition["id"] in unit.get("militaryTraditionIds", [])
                        and (not predicate["requiresShip"] or unit.get("shipId") in roster.ships
                             and roster.ships[unit["shipId"]]["category"] == unit["category"])):
                    template = unit["runtimeTemplateId"]
                    if template not in predicate["nativeTemplates"]:
                        raise CombatBindingError(f"{ident}: unbound native weapon predicate (release blocker)")
                    attacks.append(dict(id=attack_id, categoryId=predicate["categoryId"],
                        nativeAttack=predicate["nativeTemplates"][template]))
            if len(attacks) > 1:
                raise CombatBindingError(f"{ident}: ambiguous primary weapon")
            self.profiles[ident] = dict(id=ident, unitTypeId=roster.templates[unit["runtimeTemplateId"]]["warcraftUnitTypeId"],
                kind=2 if roster.movement_classes[unit["movementClassId"]]["domain"] == "naval" else 1,
                attacks=attacks, weaponIds=unit["weaponIds"], abilityIds=unit["abilityIds"])

    def compatible(self, profile_id, unit_type, category, attack_id):
        profile = self.profiles.get(profile_id)
        return bool(profile and profile["unitTypeId"] == unit_type and any(
            a["id"] == attack_id and a["categoryId"] == category for a in profile["attacks"]))

    def rating(self, view, profile_id, unit_type, attack_id, stat):
        if view is None or not self.compatible(profile_id, unit_type, view.category_id, attack_id):
            return Fraction(0)
        value = Fraction(0)
        if stat == "damage":
            for ident, binding in self.attributes.items():
                if binding["attackId"] == attack_id:
                    value += view.modifiers.get(ident, 0)
        for effect in view.effects:
            binding = self.effects.get(effect)
            if binding is None:
                raise CombatBindingError(f"unknown effect {effect} (release blocker)")
            for contribution in binding["contributions"]:
                if contribution["attackId"] == attack_id and contribution["stat"] == stat:
                    value += contribution["basisPoints"]
        return value

    def resolve(self, hit, attacker, defender, *, legal=True, attack=True, other_sources=None):
        """Participants: (current TraditionView or None, profile ID, rawcode).

        Independently authored sources are keyed by identity. They add ratings;
        they cannot masquerade as a milestone or get multiplied a second time.
        """
        if hit.result is not None:
            return hit.result
        hit.result = Fraction(hit.base)
        if not legal or not attack or hit.base <= 0:
            return hit.result
        view, profile, rawcode = attacker
        # Weapon verification is independent of attacker tradition eligibility:
        # an ineligible enemy's gunfire still encounters the defender's doctrine.
        data = self.profiles.get(profile)
        if not data or data["unitTypeId"] != rawcode or not any(a["id"] == hit.attack_id for a in data["attacks"]):
            return hit.result
        damage = self.rating(view, profile, rawcode, hit.attack_id, "damage")
        resistance = self.rating(*defender, hit.attack_id, "resistance")
        for source, ratings in (other_sources or {}).items():
            if source in {e["sourceId"] for e in self.effects.values()}:
                raise CombatBindingError("duplicate milestone source")
            damage += ratings.get("damage", 0)
            resistance += ratings.get("resistance", 0)
        hit.result *= max(0, 10000 + damage) / (10000 + max(0, resistance))
        return hit.result

    def resolve_roster_hit(self, hit, traditions, roster, source_id, target_id, hostile, *, attack=True):
        """Headless adapter for authoritative roster instances and controller XP.

        Projection presence is irrelevant. Saves reconstruct both authorities;
        callers supply the existing conflict authority, not a guessed enemy flag.
        This returns exact damage; already committed casualties are never scaled.
        """
        units = {row["id"]: row for row in roster.snapshot()["instances"]}
        source, target = units.get(source_id), units.get(target_id)
        attacking, defending = traditions.view_for_unit(source_id), traditions.view_for_unit(target_id)
        legal = bool(source and target and source["active"] and target["active"]
                     and source["representedStrength"] > 0 and target["representedStrength"] > 0
                     and source["regionId"] == target["regionId"] and attacking and defending
                     and hostile(attacking.controller_id, defending.controller_id))

        def participant(unit, view):
            profile = self.profiles.get(unit["archetypeId"]) if unit else None
            return view, profile["id"] if profile else "", profile["unitTypeId"] if profile else ""

        return self.resolve(hit, participant(source, attacking), participant(target, defending), legal=legal, attack=attack)

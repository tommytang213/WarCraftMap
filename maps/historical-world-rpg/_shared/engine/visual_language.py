"""Deterministic, scenario-data-driven visual representation resolver."""
from __future__ import annotations

import copy


class VisualLanguageError(ValueError):
    pass


class VisualResolver:
    def __init__(self, document, active_object_budget=256, *,
                 document_format="warcraftmap_visual_language_v1"):
        if document.get("format") != document_format:
            raise VisualLanguageError("unsupported visual-language document")
        self.document = copy.deepcopy(document)
        self.families = {x["id"]: x for x in document["families"]}
        self.assignments = {(x["polityId"], x["archetypeId"]): x for x in document["rosterAssignments"]}
        self.characters = {x["characterId"]: x for x in document["characterAssignments"]}
        self.active_object_budget = active_object_budget
        self.active = {}

    def resolve(self, *, polity_id, archetype_id, year, technologies=(), controller_id=None,
                imported_from=None, alternate_history=False):
        row = self.assignments.get((polity_id, archetype_id))
        if row is None:
            raise VisualLanguageError(f"missing visual assignment: {polity_id}/{archetype_id}")
        variant = row["baseline"]
        for candidate in row.get("progression", []):
            after = candidate.get("fromYear", -10**9)
            required = set(candidate.get("technologyIds", []))
            if year >= after and required <= set(technologies):
                variant = candidate
        if year < row["availableFromYear"] and not alternate_history:
            raise VisualLanguageError(f"anachronistic visual request: {archetype_id} in {year}")
        result = copy.deepcopy(variant)
        result.update(familyId=row["familyId"], polityId=polity_id, archetypeId=archetype_id,
                      paletteId=row["paletteId"], controllerId=controller_id or polity_id,
                      teamColorSource="controller", importedFrom=imported_from)
        if imported_from:
            result["culturalMarkingId"] = self.assignments.get(
                (imported_from, archetype_id), row).get("culturalMarkingId", row["culturalMarkingId"])
        else:
            result["culturalMarkingId"] = row["culturalMarkingId"]
        return result

    def resolve_character(self, character_id, controller_id=None):
        if character_id not in self.characters:
            raise VisualLanguageError(f"missing character visual: {character_id}")
        result = copy.deepcopy(self.characters[character_id])
        result["controllerId"] = controller_id or result.get("polityId")
        result["teamColorSource"] = "controller"
        return result

    def instantiate(self, representation_id, resolved, object_count=1):
        if object_count < 1 or sum(x["objectCount"] for x in self.active.values()) + object_count > self.active_object_budget:
            raise VisualLanguageError("active visual-object budget exceeded")
        self.active[representation_id] = {"resolved": copy.deepcopy(resolved), "objectCount": object_count}
        return copy.deepcopy(self.active[representation_id])

    def retire(self, representation_id):
        return self.active.pop(representation_id, None)

    def reconstruct(self, rows):
        prior = copy.deepcopy(self.active)
        self.active = {}
        try:
            for representation_id, resolved, count in rows:
                self.instantiate(representation_id, resolved, count)
        except Exception:
            self.active = prior
            raise
        return tuple(sorted(self.active))

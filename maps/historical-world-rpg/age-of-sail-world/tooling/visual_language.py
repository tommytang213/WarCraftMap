#!/usr/bin/env python3
"""Validate and deterministically compile scenario-owned visual assignments."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scenario/visuals/europe-africa-middle-east-india.json"
DATES = (1450, 1550, 1650, 1750, 1820)


class VisualLanguageError(ValueError):
    pass


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _index(items, label):
    result = {}
    for item in items:
        ident = item.get("id")
        if not isinstance(ident, str) or not ident or ident in result:
            raise VisualLanguageError(f"duplicate or invalid {label} ID")
        result[ident] = item
    return result


def load_roster():
    import validate_unit_roster
    return validate_unit_roster.load_catalog()


class VisualCatalog:
    def __init__(self, source=None):
        self.source = source or _load(SOURCE)
        if self.source.get("format") != "age_of_sail_visual_language_v1":
            raise VisualLanguageError("unsupported visual-language format")
        self.contracts = self.source["contracts"]
        self.indexes = {key: _index(self.source[key], key) for key in (
            "historicalPeriods", "roles", "silhouettes", "teamColors", "palettes",
            "animationSets", "attachmentSets", "formationReadability", "rankDistinctions",
            "fallbacks", "assets", "archetypes", "regionalFamilies")}
        self.fit = {entry["assetId"]: entry for entry in self.source["historicalFit"]}
        self.roster = load_roster()
        self.world = _load(ROOT / "scenario/world/world.json")
        self.characters = _load(ROOT / "scenario/characters/global.json")
        self.families = _load(ROOT / "scenario/rosters/global-roster-families.json")["families"]
        self.polity_family = self._polity_families()
        self._validate()

    def _polity_families(self):
        result = {}
        explicit = self.source.get("polityFamilyAssignments", {})
        scoped = set(self.source["scope"]["regions"])
        for family in self.families:
            region = family["politySource"].replace("-1450.json", "").replace("middle-east-india", "middle_east_india")
            if region not in scoped:
                continue
            polities = _load(ROOT / "scenario/politics" / family["politySource"])["polities"]
            for polity in polities:
                polity_id = polity["id"]
                selected = explicit.get(polity_id, family["id"])
                if selected not in self.indexes["regionalFamilies"]:
                    raise VisualLanguageError(f"polity {polity_id} has a broken explicit visual family")
                if polity_id in result and result[polity_id] != selected:
                    raise VisualLanguageError(f"polity {polity_id} belongs to conflicting visual families")
                result[polity_id] = selected
        return result

    def _validate(self):
        required_order = ["archetype", "regionalFamily", "polity", "historicalPeriod", "identity"]
        if self.contracts.get("inheritanceOrder") != required_order:
            raise VisualLanguageError("inheritance order is not the stable visual contract")
        if self.source["scope"].get("roadmapComplete") is not False:
            raise VisualLanguageError("regional slice must not complete the world visual roadmap")
        refs = {
            "roleId": "roles", "silhouetteId": "silhouettes", "teamColorId": "teamColors",
            "paletteId": "palettes", "assetId": "assets", "attachmentSetId": "attachmentSets",
            "animationSetId": "animationSets", "formationReadabilityId": "formationReadability",
            "rankDistinctionId": "rankDistinctions", "fallbackId": "fallbacks"}
        assets = self.indexes["assets"]
        evidence = {x["id"] for x in self.roster.source["historicalEvidence"]}
        for fit in self.source["historicalFit"]:
            if fit.get("assetId") not in assets or fit.get("evidenceId") not in evidence:
                raise VisualLanguageError("historical-fit matrix has a broken asset or evidence reference")
            if fit.get("rating") == "placeholder" and not fit.get("customCandidate"):
                raise VisualLanguageError(f"asset {fit['assetId']} has an undeclared placeholder")
            if not set(fit.get("roles", ())) <= set(self.indexes["roles"]):
                raise VisualLanguageError("historical-fit matrix has a broken role reference")
        for asset in assets.values():
            if asset["kind"] == "unit" and (not asset.get("portrait") or not asset.get("classic") or not asset.get("reforged")):
                raise VisualLanguageError(f"asset {asset['id']} is missing a portrait or version mapping")
        lo, hi = self.contracts["scaleRange"]
        value_sets = [x["values"] for x in self.source["archetypes"] + self.source["regionalFamilies"] +
                      self.source["polities"] + self.source["periodOverrides"] + self.source["unitOverrides"] +
                      self.source["characterArchetypes"]]
        for values in value_sets:
            for field, index in refs.items():
                if field in values and values[field] not in self.indexes[index]:
                    raise VisualLanguageError(f"broken {field} reference {values[field]}")
            if "scale" in values and not lo <= values["scale"] <= hi:
                raise VisualLanguageError("unsafe visual scale")
        for attachment_set in self.indexes["attachmentSets"].values():
            if len(attachment_set["attachments"]) > self.contracts["maxAttachments"] or len(attachment_set["effects"]) > self.contracts["maxEffects"]:
                raise VisualLanguageError("attachment/effect budget exceeded")
            for attachment in attachment_set["attachments"]:
                asset = assets.get(attachment["assetId"])
                if not asset or asset["kind"] != "attachment":
                    raise VisualLanguageError("unsupported attachment")
            for effect in attachment_set["effects"]:
                if effect not in assets or assets[effect]["kind"] != "effect":
                    raise VisualLanguageError("unsupported effect")
        periods = sorted(self.indexes["historicalPeriods"].values(), key=lambda x: x["startYear"])
        if periods[0]["startYear"] != 1450 or periods[-1]["endYear"] != 1820 or any(a["endYear"] + 1 != b["startYear"] for a, b in zip(periods, periods[1:])):
            raise VisualLanguageError("historical periods do not continuously cover the campaign")
        covered_categories = {c for a in self.source["archetypes"] for c in a["matchCategories"]}
        scoped_assignments = {(p, u) for p, u in self.roster.assignments if p in self.polity_family}
        if not scoped_assignments:
            raise VisualLanguageError("regional visual slice has no roster coverage")
        for polity, unit in scoped_assignments:
            category = self.roster.archetypes[unit]["category"]
            if category not in covered_categories:
                raise VisualLanguageError(f"missing visual archetype for {polity}/{unit}")
            self.resolve_unit(polity, unit, 1450, validate=False)
        scoped_characters = [c for c in self.characters["characters"] if c["regionId"] in self.source["scope"]["regions"]]
        if not scoped_characters:
            raise VisualLanguageError("regional character visual coverage is empty")
        for character in scoped_characters:
            self.resolve_character(character)

    def period(self, year):
        for period in self.indexes["historicalPeriods"].values():
            if period["startYear"] <= year <= period["endYear"]:
                return period["id"]
        raise VisualLanguageError(f"year {year} is outside visual coverage")

    def resolve_unit(self, polity_id, unit_id, year, validate=True):
        if polity_id not in self.polity_family or (polity_id, unit_id) not in self.roster.assignments:
            raise VisualLanguageError(f"unit {unit_id} is not assigned to scoped polity {polity_id}")
        category = self.roster.archetypes[unit_id]["category"]
        matches = [x for x in self.source["archetypes"] if category in x["matchCategories"]]
        if len(matches) != 1:
            raise VisualLanguageError(f"category {category} has conflicting visual archetypes")
        result = dict(matches[0]["values"])
        family_id = self.polity_family[polity_id]
        result.update(self.indexes["regionalFamilies"][family_id]["values"])
        for override in self.source["polities"]:
            if override["id"] == polity_id:
                result.update(override["values"])
        period_id = self.period(year)
        for override in self.source["periodOverrides"]:
            if override["periodId"] == period_id and category in override["matchCategories"]:
                result.update(override["values"])
        for override in self.source["unitOverrides"]:
            if override["id"] == unit_id:
                result.update(override["values"])
        required = set(self.contracts["requiredAssignmentFields"])
        if set(result) != required:
            raise VisualLanguageError(f"assignment {polity_id}/{unit_id} is missing or adds contract fields")
        role = self.indexes["roles"][result["roleId"]]
        if role["category"] != category:
            raise VisualLanguageError(f"unit {unit_id} has a misleading role/category combination")
        asset = self.indexes["assets"][result["assetId"]]
        fit = self.fit.get(result["assetId"])
        if asset["kind"] != "unit" or not fit or result["roleId"] not in fit["roles"]:
            raise VisualLanguageError(f"unit {unit_id} has an invalid asset combination")
        if not asset.get("teamColor"):
            raise VisualLanguageError(f"unit {unit_id} loses controller-change readability")
        attachments = self.indexes["attachmentSets"][result["attachmentSetId"]]
        for attachment in attachments["attachments"]:
            if attachment["point"] not in asset.get("attachmentPoints", ()):
                raise VisualLanguageError(f"unit {unit_id} uses unsupported attachment point")
        if result["animationSetId"] not in asset["animations"]:
            raise VisualLanguageError(f"unit {unit_id} uses unsupported animation set")
        return {"polityId":polity_id, "unitId":unit_id, "year":year, "periodId":period_id,
                "regionalFamilyId":family_id, **result}

    def resolve_character(self, character):
        profession_ids = set(character["professionIds"])
        kind = "commander" if profession_ids & {"commander", "admiral"} else "specialist"
        values = dict(next(x["values"] for x in self.source["characterArchetypes"] if x["id"] == kind))
        return {"characterId":character["id"], "regionId":character["regionId"], **values}

    def snapshot(self, years=DATES):
        units = []
        for year in years:
            units.extend(self.resolve_unit(p, u, year) for p, u in self.roster.assignments if p in self.polity_family)
        characters = [self.resolve_character(c) for c in self.characters["characters"] if c["regionId"] in self.source["scope"]["regions"]]
        return {"format":"age_of_sail_visual_snapshot_v1", "years":list(years), "units":units, "characters":characters}

    def object_data(self, edition="classic", year=1650):
        if edition not in ("classic", "reforged"):
            raise VisualLanguageError("unknown Warcraft asset edition")
        objects = []
        for polity, unit in self.roster.assignments:
            if polity not in self.polity_family:
                continue
            assignment = self.resolve_unit(polity, unit, year)
            asset = self.indexes["assets"][assignment["assetId"]]
            objects.append({"id":f"visual_{polity}_{unit}", "polityId":polity, "unitId":unit,
                "model":asset[edition], "portrait":asset["portrait"], "scale":assignment["scale"],
                "tint":self.indexes["palettes"][assignment["paletteId"]]["tint"],
                "teamColorMode":self.indexes["teamColors"][assignment["teamColorId"]]["mode"],
                "attachmentSetId":assignment["attachmentSetId"], "animationSetId":assignment["animationSetId"]})
        return {"format":"age_of_sail_visual_object_data_v1", "edition":edition, "year":year, "objects":objects}

    def preview(self, year=1650):
        representatives = {}
        for assignment in self.snapshot((year,))["units"]:
            key = (assignment["regionalFamilyId"], assignment["roleId"])
            representatives.setdefault(key, assignment)
        scenes = [{"label":f"{family}: {role}", "familyId":family, "roleId":role,
                   "unitId":item["unitId"], "assetId":item["assetId"], "silhouetteId":item["silhouetteId"],
                   "teamColorId":item["teamColorId"]} for (family, role), item in sorted(representatives.items())]
        return {"format":"age_of_sail_visual_preview_v1", "year":year, "sceneType":"contact_sheet", "scenes":scenes}


def normalized(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--object-data", type=Path)
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--edition", choices=("classic", "reforged"), default="classic")
    parser.add_argument("--year", type=int, default=1650)
    args = parser.parse_args(argv)
    try:
        catalog = VisualCatalog()
        outputs = ((args.snapshot, catalog.snapshot()), (args.object_data, catalog.object_data(args.edition, args.year)),
                   (args.preview, catalog.preview(args.year)))
        for path, data in outputs:
            if path:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(normalized(data), encoding="utf-8")
        digest = hashlib.sha256(normalized(catalog.snapshot()).encode()).hexdigest()
        print(f"Visual language valid: {len(catalog.snapshot()['units'])} dated assignments; digest {digest}")
    except (OSError, KeyError, TypeError, json.JSONDecodeError, VisualLanguageError) as error:
        print(f"Visual-language validation failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

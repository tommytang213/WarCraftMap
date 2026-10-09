"""Translate composed scenario profiles into the live residual-XP contract."""
import re

ID = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")


def identity(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError(f"invalid progression identity: {value!r}")
    return value


def integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"invalid {label}: {value!r}")
    return value


def index(rows, label):
    if not isinstance(rows, list):
        raise ValueError(f"{label} must be an array")
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"invalid {label} record")
        ident = identity(row.get("id"))
        if ident in result:
            raise ValueError(f"duplicate {label}: {ident}")
        result[ident] = row
    return result


def ranks(rows, key, known):
    if not isinstance(rows, list):
        raise ValueError(f"{key} ranks must be an array")
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"invalid {key} rank record")
        ident = identity(row.get(key))
        if ident not in known or ident in result:
            raise ValueError(f"unknown or duplicate {key}: {ident}")
        result[ident] = integer(row.get("rank"), 0, 100, "rank")
    return result


def rank_text(values):
    return "".join(f"{ident}:{rank}~" for ident, rank in sorted(values.items()))


def starting_definitions(world, catalog=None):
    profiles = {}
    skills, masteries, trees = {}, {}, {}
    if catalog is not None:
        if catalog.get("format") != "warcraftmap_hero_progression_v1" or catalog.get("levelCap") != 300:
            raise ValueError("unsupported hero progression catalogue")
        profiles = index(catalog.get("characterProfiles"), "characterProfiles")
        skills = index(catalog.get("skills"), "skills")
        masteries = index(catalog.get("masteries"), "masteries")
        trees = index(catalog.get("personalTrees"), "personalTrees")
        # Validate all records, including profiles outside a particular map.
        for profile in profiles.values():
            integer(profile.get("startingLevel"), 1, 300, "starting level")
            ranks(profile.get("startingSkills", []), "skillId", skills)
            ranks(profile.get("startingMasteries", []), "masteryId", masteries)
            if profile.get("personalTreeId") not in trees:
                raise ValueError(f"unknown personal tree: {profile.get('personalTreeId')}")
    result = {}
    for hero in world.get("characters", []):
        profile = profiles.get(hero["id"])
        if profile is None:
            # Non-catalogue characters retain explicitly authored defaults.
            # World skill ratings predate the progression catalogue.
            profile = hero.get("startingProgression", {
                "startingLevel": hero.get("level", 1),
                "startingSkills": [{"skillId": r["skillId"], "rank": r["rating"]}
                                   for r in hero.get("skills", [])],
                "startingMasteries": hero.get("masteries", []),
                "personalTreeId": hero.get("signatureProgressionId", ""),
            })
            if not isinstance(profile, dict):
                raise ValueError("startingProgression must be an object")
            for row in profile.get("startingSkills", []):
                skills.setdefault(identity(row.get("skillId")), {})
            for row in profile.get("startingMasteries", []):
                masteries.setdefault(identity(row.get("masteryId")), {})
            if profile.get("personalTreeId"):
                trees.setdefault(identity(profile["personalTreeId"]), {})
        tree = profile.get("personalTreeId", "")
        if tree != "":
            identity(tree)
        result[hero["id"]] = {
            "level": integer(profile.get("startingLevel", 1), 1, 300, "starting level"),
            # Headless starts exactly at experience_for_level(level). Live XP
            # is the residual toward the next level, not that cumulative sum.
            "experience": 0, "skillPoints": 0, "masteryPoints": 0,
            "skills": ranks(profile.get("startingSkills", []), "skillId", skills),
            "masteries": ranks(profile.get("startingMasteries", []), "masteryId", masteries),
            "personalTreeId": tree,
        }
    return {"profiles": result, "skillIds": sorted(skills),
            "masteryIds": sorted(masteries), "personalTreeIds": sorted(trees)}

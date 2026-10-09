import copy
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT / "tooling"), str(PROJECT.parent / "_shared/tooling"),
               str(PROJECT.parent / "_shared/engine")]
from hero_progression_catalog import load_catalog
from hero_progression import HeroProgressionRuntime
from hero_starting_profiles import starting_definitions, rank_text
from package_wurst_map import generate, load_config, verify_generated, PackagingError


class HeroStartingProfilesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog, _ = load_catalog()
        cls.world = json.loads((PROJECT / "scenario/world/world.json").read_text())

    def test_generated_definitions_match_every_composed_headless_start(self):
        ids = [p["id"] for p in self.catalog["characterProfiles"]]
        headless = HeroProgressionRuntime(self.catalog, ids)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            config = load_config(PROJECT / "package.json")
            generate(config, output)
            verify_generated(config, output)
            source = (output / "ScenarioData.wurst").read_text()
            data = json.loads((output / "scenario-runtime.json").read_text())["heroStartingDefinitions"]
            provenance = json.loads((output / "provenance.json").read_text())
        self.assertEqual(set(ids), set(data["profiles"]))
        for i, hero in enumerate(self.world["characters"]):
            ident = hero["id"]
            start, profile = headless.require(ident), headless.profiles[ident]
            expected = {k: start[k] for k in ("level", "skillPoints", "masteryPoints", "skills", "masteries")}
            expected["experience"] = start["experience"] - headless.experience_for_level(start["level"])
            expected["personalTreeId"] = profile["personalTreeId"]
            self.assertEqual(expected, data["profiles"][ident], ident)
            self.assertIn(f'hero{i}.startingProfile=new HeroStartingProfile({start["level"]},'
                          f'"{rank_text(start["skills"])}","{rank_text(start["masteries"])}",'
                          f'"{profile["personalTreeId"]}")', source)
        for relative in ("scenario/progression/hero-progression.json", "scenario/characters/global.json",
                         "scenario/characters/phase8.json", "scenario/characters/release-scale.json",
                         "tooling/global_characters.py", "tooling/hero_progression_catalog.py"):
            self.assertIn("age-of-sail-world/" + relative, provenance["inputs"])
        # Live command test vectors are independently checked against the
        # headless authority, including distinct roles and early/late eras.
        wurst = (PROJECT / "wurst/HeroStartingProfileTests.wurst").read_text()
        vectors = re.findall(r'assertStart\(f, "([^"]+)", (\d+), "([^"]*)", "([^"]*)", "([^"]*)"\)', wurst)
        self.assertGreaterEqual(len(vectors), 3)
        for ident, level, skills, masteries, tree in vectors:
            state = headless.require(ident)
            self.assertEqual((int(level), skills, masteries, tree),
                             (state["level"], rank_text(state["skills"]), rank_text(state["masteries"]),
                              headless.profiles[ident]["personalTreeId"]))

    def test_non_catalogue_scenarios_and_explicit_defaults(self):
        world = {"characters": [{"id": "default_hero"}, {"id": "authored", "level": 17,
                 "skills": [{"skillId": "craft", "rating": 42}],
                 "masteries": [{"masteryId": "artisan", "rank": 13}],
                 "signatureProgressionId": "local_tree"}]}
        for catalog in (None, self.catalog):
            starts = starting_definitions(world, catalog)["profiles"]
            self.assertEqual(starts["default_hero"]["level"], 1)
            self.assertEqual(starts["authored"]["level"], 17)
            self.assertEqual(starts["authored"]["skills"], {"craft": 42})
            self.assertEqual(starts["authored"]["masteries"], {"artisan": 13})
            self.assertEqual(starts["authored"]["personalTreeId"], "local_tree")

    def test_invalid_profiles_fail_generation_before_writing_scenario_data(self):
        profile = self.catalog["characterProfiles"][0]
        invalid = [{**profile, "startingLevel": n} for n in (True, 0, 301, 1.5, "64")]
        invalid += [{**profile, "personalTreeId": "missing"}]
        for key, axis in (("startingSkills", "skillId"), ("startingMasteries", "masteryId")):
            for value in (True, -1, 101, 1.5, "40"):
                invalid.append({**profile, key: [{**profile[key][0], "rank": value}]})
            invalid.append({**profile, key: [{axis: "unknown", "rank": 1}]})
            invalid.append({**profile, key: [profile[key][0], profile[key][0]]})
        for replacement in invalid:
            with self.subTest(replacement=replacement):
                catalog = copy.deepcopy(self.catalog)
                catalog["characterProfiles"][0] = replacement
                with tempfile.TemporaryDirectory() as directory:
                    output = Path(directory)
                    # Inject at the shared composition boundary, then exercise
                    # the actual packager and its atomic pre-output validation.
                    with patch("package_wurst_map.subprocess.run") as run:
                        run.return_value.stdout = json.dumps({"catalog": catalog, "sources": []})
                        with self.assertRaises(PackagingError):
                            generate(load_config(PROJECT / "package.json"), output)
                    self.assertFalse((output / "ScenarioData.wurst").exists())
                    self.assertFalse((output / "scenario-runtime.json").exists())
        catalog = copy.deepcopy(self.catalog)
        catalog["characterProfiles"].append(profile)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            starting_definitions(self.world, catalog)


if __name__ == "__main__":
    unittest.main()

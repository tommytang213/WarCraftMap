import copy
from dataclasses import replace
from datetime import date
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
sys.path.insert(0, str(PROJECT / "tooling"))
from global_characters import load_source
from package_wurst_map import PackagingError, generate, load_config


class RecruitmentGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config(PROJECT / "package.json")
        cls.world = json.loads(cls.config.scenario_file.read_text())

    def test_every_authored_window_survives_production_generation_by_stable_id(self):
        expected = {row["id"]: row["availabilityWindow"] for row in load_source()["characters"]}
        self.assertEqual(expected, {row["id"]: row["availabilityWindow"] for row in self.world["characters"]})
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory) / "generated"
            generate(self.config, generated)
            source = (generated / "ScenarioData.wurst").read_text()
            runtime = json.loads((generated / "scenario-runtime.json").read_text())
        self.assertEqual(expected, runtime["characterRecruitmentWindows"])
        records = re.findall(
            r'let (hero\d+)=new RpgHero\("([^"]+)"[^\n]*\n'
            r'\s*\1\.availabilityStartDay=(\d+)\n\s*\1\.availabilityEndDay=(\d+)', source)
        self.assertEqual(len(expected), len(records))
        self.assertEqual(expected, {
            ident: {"startDate": date.fromordinal(int(start)).isoformat(),
                    "endDate": date.fromordinal(int(end)).isoformat()}
            for _, ident, start, end in records
        })
        self.assertEqual("1470-01-01", expected["leonardo_da_vinci"]["startDate"])

    def reject(self, characters, diagnostic):
        # Generation itself must fail even if a caller bypasses scenario validation.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scenario = root / "world.json"
            scenario.write_text(json.dumps({"characters": characters}))
            with self.assertRaisesRegex(PackagingError, diagnostic):
                generate(replace(self.config, scenario_file=scenario), root / "generated")
            self.assertFalse((root / "generated/ScenarioData.wurst").exists())

    def test_generation_rejects_malformed_full_dates_on_either_boundary(self):
        for field in ("startDate", "endDate"):
            for value in (None, 1470, True, "", "1470", "1470-01", "14700101", "1470-W01-1",
                          "1470-1-01", "1470-01-1", "1470-01-01T00:00:00", "1470-01-01Z",
                          " 1470-01-01", "1470-02-29", "1500-02-29", "1470-04-31",
                          "0000-01-01", "10000-01-01", "1470-13-01", "1470-00-01"):
                with self.subTest(field=field, value=value):
                    hero = copy.deepcopy(self.world["characters"][0])
                    hero["availabilityWindow"][field] = value
                    self.reject([hero], f"character {hero['id']}: invalid availabilityWindow.{field}")

    def test_generation_rejects_missing_and_reversed_windows(self):
        for window in (None, [], {}, {"startDate": "1470-01-01"}, {"endDate": "1519-05-02"},
                       {"startDate": "1519-05-03", "endDate": "1519-05-02"}):
            with self.subTest(window=window):
                hero = copy.deepcopy(self.world["characters"][0])
                hero["availabilityWindow"] = window
                self.reject([hero], "character leonardo_da_vinci: .*availabilityWindow")
        hero.pop("availabilityWindow")
        self.reject([hero], "availabilityWindow is required")

    def test_generation_rejects_duplicate_or_invalid_stable_identities(self):
        hero = copy.deepcopy(self.world["characters"][0])
        self.reject([hero, hero], "duplicate character ID: leonardo_da_vinci")
        for ident in (None, "", "leonardo,other", "Leonardo", "a" * 65):
            with self.subTest(ident=ident):
                hero["id"] = ident
                self.reject([hero], "valid stable ID")

    def test_generation_preserves_a_single_day_leap_window_and_authored_ownership(self):
        world = copy.deepcopy(self.world)
        hero = world["characters"][0]
        hero["availabilityWindow"] = {"startDate": "1600-02-29", "endDate": "1600-02-29"}
        hero["recruited"] = True
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scenario = root / "world.json"
            scenario.write_text(json.dumps(world))
            generate(replace(self.config, scenario_file=scenario), root / "generated")
            source = (root / "generated/ScenarioData.wurst").read_text()
        self.assertIn("hero0.availabilityStartDay=584082\n\thero0.availabilityEndDay=584082", source)
        self.assertIn("hero0.recruited=true", source)


if __name__ == "__main__":
    unittest.main()

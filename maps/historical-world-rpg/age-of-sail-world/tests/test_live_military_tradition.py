"""Authored generation and the oracle used by the native-callback receipts."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT.parent / "_shared/tooling"), str(PROJECT.parent / "_shared/engine")]
from military_tradition import MilitaryTraditionRuntime, RecordingTraditionAdapter, TraditionError
from package_wurst_map import generate, load_config
from requirement_traceability import records


class LiveMilitaryTraditionTests(unittest.TestCase):
    def setUp(self):
        self.definitions = json.loads((PROJECT / "scenario/military-traditions.json").read_text())

    def test_generation_retains_sources_starts_eligibility_and_authored_assignments(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            generate(load_config(PROJECT / "package.json"), output)
            source = (output / "ScenarioData.wurst").read_text()
            runtime = json.loads((output / "scenario-runtime.json").read_text())
        self.assertEqual(self.definitions, runtime["militaryTraditions"])
        catalogues = json.loads((PROJECT / "scenario/traceability/catalogues.json").read_text())
        census = next(row for row in catalogues if row["id"] == "military-traditions")
        self.assertEqual({row["id"]: row for row in self.definitions["traditions"]}, records(runtime, census["runtime"]))
        self.assertIn('runtime.traditionDefinitions = new GeneratedMilitaryTraditions()', source)
        for row in self.definitions["experienceSources"]:
            self.assertIn(f'runtime.registerContribution("{row["id"]}", {row["weightNumerator"]}, {row["weightDenominator"]})', source)
        for controller in self.definitions["eligibleControllerIds"]:
            for tradition in self.definitions["traditions"]:
                self.assertIn(f'runtime.reconcileTradition("{controller}", "{tradition["categoryId"]}", {tradition["startingExperience"]}, 0,', source)
        for row in self.definitions["unitAssignments"]:
            self.assertRegex(source, rf'new RuntimeForce\("{row["id"]}", "{row["controllerId"]}", "[^"]+", "{row["categoryId"]}"')

    def test_callback_fixture_values_match_weighted_oracle_for_each_controller_category(self):
        for controller in ("player", "france"):
            for category in ("land_formation", "sailing_naval"):
                for numerator, denominator, amount, expected in ((1, 1, 40, 40), (1, 1, 13, 13), (1, 1, 17, 17), (1, 1, 19, 19), (3, 4, 13, 9), (5, 2, 13, 32), (3, 4, 2000000000, 1500000000), (5, 2, 2000000000, 5000000000), (2147483647, 1, 2147483647, 4611686014132420609), (2147483647, 2147483646, 2147483647, 2147483648), (1, 2147483647, 1, 0)):
                    with self.subTest(controller=controller, category=category, weight=(numerator, denominator), amount=amount):
                        definitions = copy.deepcopy(self.definitions)
                        definitions["experienceSources"][0].update(weightNumerator=numerator, weightDenominator=denominator)
                        definitions["unitAssignments"][0].update(controllerId=controller, categoryId=category)
                        runtime = MilitaryTraditionRuntime(definitions, RecordingTraditionAdapter())
                        event = dict(sourceId="enemy_kill", unitId="english_guard_formation", enemyControllerId="england", amount=amount)
                        if expected == 0:
                            with self.assertRaisesRegex(TraditionError, "rounds to zero"):
                                runtime.award([event])
                        else:
                            self.assertEqual(expected, runtime.award([event]))
                        self.assertEqual(expected, runtime.view(controller, category).experience)
                        self.assertEqual(0, runtime.view("england", category).experience)

    def test_unbounded_totals_round_trip_and_continue_without_rounding(self):
        for before in (2147483647, 9007199254740991, 9007199254740992, 10**60 - 1, 10**512):
            with self.subTest(before=before):
                runtime = MilitaryTraditionRuntime(self.definitions, RecordingTraditionAdapter())
                runtime.change_unit("english_guard_formation", controller_id="player")
                checkpoint = runtime.snapshot()
                track = next(row for row in checkpoint["tracks"]
                             if row["controllerId"] == "player" and row["categoryId"] == "land_formation")
                track["experience"] = before
                runtime.restore(checkpoint)
                event = dict(sourceId="enemy_kill", unitId="english_guard_formation", enemyControllerId="france", amount=1)
                self.assertEqual(1, runtime.award([event]))
                self.assertEqual(before + 1, runtime.view("player", "land_formation").experience)
                fresh = MilitaryTraditionRuntime(self.definitions, RecordingTraditionAdapter())
                fresh.restore(runtime.snapshot())
                self.assertEqual(before + 1, fresh.view("player", "land_formation").experience)
                self.assertEqual(before, track["experience"])

    def test_v1_migrates_only_missing_player_tracks_and_rejects_bad_saves_atomically(self):
        runtime = MilitaryTraditionRuntime(self.definitions, RecordingTraditionAdapter())
        legacy = runtime.snapshot()
        legacy["schemaVersion"] = 1
        legacy["tracks"] = [row for row in legacy["tracks"] if row["controllerId"] != "player"]
        legacy["tracks"][0]["experience"] = 73
        runtime.restore(legacy)
        saved = runtime.snapshot()
        self.assertEqual(2, saved["schemaVersion"])
        self.assertEqual(73, runtime.view("england", "land_formation").experience)
        self.assertEqual(0, runtime.view("player", "land_formation").experience)
        for version, missing_controller in ((1, "england"), (2, "player")):
            bad = copy.deepcopy(saved)
            bad["schemaVersion"] = version
            bad["tracks"] = [row for row in bad["tracks"] if row["controllerId"] != missing_controller]
            with self.assertRaises(TraditionError):
                runtime.restore(bad)
            self.assertEqual(saved, runtime.snapshot())

    def test_transferring_a_contributor_leaves_earned_controller_experience_in_place(self):
        runtime = MilitaryTraditionRuntime(self.definitions, RecordingTraditionAdapter())
        runtime.change_unit("english_guard_formation", controller_id="player")
        event = dict(sourceId="enemy_kill", unitId="english_guard_formation", enemyControllerId="france", amount=13)
        runtime.award([event])
        runtime.change_unit("english_guard_formation", controller_id="france")
        runtime.award([{**event, "enemyControllerId": "england", "amount": 17}])
        self.assertEqual(13, runtime.view("player", "land_formation").experience)
        self.assertEqual(17, runtime.view("france", "land_formation").experience)
        self.assertEqual(0, runtime.view("england", "land_formation").experience)


if __name__ == "__main__":
    unittest.main()

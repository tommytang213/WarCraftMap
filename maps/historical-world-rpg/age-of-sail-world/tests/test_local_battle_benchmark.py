import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "_shared" / "engine"))
import local_battle_benchmark as benchmark  # noqa: E402

CONFIG = PROJECT / "scenario/benchmarks/local-battle.json"


class LocalBattleBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.profiles = benchmark.load_profiles(CONFIG)

    def test_every_documented_profile_passes_headless(self):
        for profile in self.profiles.values():
            with self.subTest(profile=profile.id):
                result = benchmark.run(profile)
                self.assertTrue(result["passed"], result.get("failures"))
                self.assertEqual(profile.repeats, result["runs"])

    def test_fixture_and_script_are_deterministic(self):
        profile = self.profiles["maximum_mixed"]
        first_adapter = benchmark.RecordingBattleAdapter()
        first = benchmark.run_once(profile, first_adapter)
        second = benchmark.run_once(profile, benchmark.RecordingBattleAdapter())
        self.assertEqual(benchmark.canonical(first["fixture"]), benchmark.canonical(second["fixture"]))
        self.assertEqual(first["authoritativeState"], second["authoritativeState"])
        self.assertEqual(list(benchmark.STAGES), [op[1] for op in first_adapter.operations if op[0] == "stage"])
        self.assertEqual(profile.orders, first["metrics"]["orders_issued"])
        self.assertEqual(profile.orders, first["metrics"]["pathing_queries"])

    def test_casualty_reconciliation_strength_and_cleanup(self):
        profile = self.profiles["maximum_land"]
        adapter = benchmark.RecordingBattleAdapter()
        result = benchmark.run_once(profile, adapter)
        fixture_strength = sum(unit["representedStrength"] for unit in result["fixture"]["authoritativeUnits"])
        self.assertLess(result["representedStrength"], fixture_strength)
        self.assertNotEqual(result["representedStrength"], result["spawnedObjectCount"])
        self.assertEqual((0, 0), adapter.live_counts())
        self.assertEqual(adapter.counts["handles_created"], adapter.counts["handles_retired"])
        self.assertEqual(adapter.counts["effects_created"], adapter.counts["effects_retired"])
        self.assertEqual(profile.units + profile.effects, adapter.counts["peak_active_objects"])
        self.assertGreater(sum(x["experience"] for x in result["traditionState"]), 0)

    def test_repeated_run_stability_uses_fresh_fully_retired_adapters(self):
        adapters = []

        def factory():
            adapter = benchmark.RecordingBattleAdapter()
            adapters.append(adapter)
            return adapter

        profile = self.profiles["maximum_mixed"]
        result = benchmark.run(profile, factory)
        self.assertTrue(result["passed"])
        self.assertEqual(profile.repeats, len(adapters))
        self.assertTrue(all(adapter.live_counts() == (0, 0) for adapter in adapters))

    def test_budget_diagnostic_identifies_profile_stage_metric_and_limit(self):
        profile = copy.deepcopy(self.profiles["maximum_land"])
        object.__setattr__(profile, "budgets", {metric: 0.5 for metric in benchmark.METRICS})
        result = benchmark.run(profile)
        self.assertEqual("performance_budget_failure", result["status"])
        expected = {"profile", "stage", "metric", "observed", "limit", "message", "kind"}
        self.assertEqual(expected, set(result["failures"][0]))
        self.assertIn(result["failures"][0]["stage"], benchmark.STAGES)

    def test_cli_emits_canonical_generated_fixtures(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "local-battle-results.json"
            command = [sys.executable, str(PROJECT / "tooling/run_local_battle_benchmark.py"), "--output", str(output)]
            completed = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(0, completed.returncode, completed.stderr)
            parsed = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(parsed["passed"])
            self.assertEqual(set(self.profiles), {item["profile"] for item in parsed["results"]})
            expected = json.dumps(parsed, sort_keys=True, separators=(",", ":")) + "\n"
            self.assertEqual(expected, output.read_text(encoding="utf-8"))

    def test_warcraft_harness_is_compile_visible_but_not_release_activated(self):
        harness = (PROJECT / "wurst/LocalBattleBenchmark.wurst").read_text(encoding="utf-8")
        compatibility = (PROJECT / "wurst/WC3Compatibility.wurst").read_text(encoding="utf-8")
        bootstrap = (PROJECT / "wurst/Bootstrap.wurst").read_text(encoding="utf-8")
        canonical_map = (PROJECT / "map/AgeOfSailWorld.w3x/war3map.j").read_text(errors="ignore")
        self.assertIn("package LocalBattleBenchmark", harness)
        self.assertIn("WarcraftLocalBattleRuntime", harness)
        self.assertIn("compatBenchmarkCreateUnit", compatibility)
        self.assertNotIn("LocalBattleBenchmark", bootstrap)
        self.assertNotIn("runLocalBattleBenchmark", canonical_map)


if __name__ == "__main__":
    unittest.main()

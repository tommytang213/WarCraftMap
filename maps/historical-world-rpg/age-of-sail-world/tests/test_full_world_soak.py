import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "_shared/engine"))
import full_world_soak as soak

CONFIG = PROJECT / "scenario/benchmarks/full-world-soak.json"
CLI = PROJECT / "tooling/run_full_world_soak.py"


class FullWorldSoakTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config, cls.sources, cls.profiles = soak.load_config(CONFIG)

    def test_complete_authored_fixture_loads_every_required_domain(self):
        state = soak.build_fixture(self.config, self.sources, 1450)
        required = {"polities", "provinces", "settlements", "technologies", "institutions",
                    "characters", "armies", "fleets", "quests", "events", "treasures", "tradeRoutes"}
        self.assertFalse(required - set(state["domains"]))
        self.assertTrue(all(state["domains"][x] for x in required))
        self.assertEqual(set(self.config["sources"]), set(state["sourceCounts"]))
        self.assertTrue(all(state["sourceCounts"].values()))
        for prefix in ("politics", "settlements", "geography"):
            self.assertEqual(7, len([name for name in self.config["sources"] if name.startswith(prefix)]))
        self.assertIn("militaryTraditions", self.config["sources"])
        self.assertEqual("1450-01-01", state["date"])
        self.assertEqual("1820-12-31", state["endDate"])

    def test_smoke_repeats_seeds_jumps_and_checkpoint_resume(self):
        first = soak.run_profile(self.config, self.sources, self.profiles["smoke"])
        second = soak.run_profile(self.config, self.sources, self.profiles["smoke"])
        self.assertTrue(first["passed"], first["failures"])
        self.assertEqual(first, second)
        self.assertEqual([1450, 1701], [x["seed"] for x in first["runs"]])
        self.assertTrue(all(len(x["normalizedStateHash"]) == 64 for x in first["runs"]))
        expected = dict(self.profiles["smoke"].expected_hashes)
        self.assertEqual(expected, {x["seed"]: x["normalizedStateHash"] for x in first["runs"]})
        self.assertTrue(all(x["activeRepresentations"] <= 64 for x in first["runs"]))

    def test_normalized_hash_regression_is_reported_as_an_invariant_failure(self):
        profile = copy.copy(self.profiles["smoke"])
        object.__setattr__(profile, "expected_hashes", tuple(
            (seed, "0" * 64 if seed == 1450 else expected)
            for seed, expected in profile.expected_hashes))
        result = soak.run_profile(self.config, self.sources, profile)
        self.assertFalse(result["passed"])
        self.assertEqual("normalized_state_hash", result["failures"][0]["invariant"])
        self.assertEqual("seed:1450", result["failures"][0]["entityId"])

    def test_inactive_world_scale_never_expands_active_representation(self):
        profile = self.profiles["smoke"]
        state = soak.build_fixture(self.config, self.sources, 1450)
        before = len(state["activeRepresentations"])
        state["settlementRegions"].update({f"inactive_{x}": "inactive_region" for x in range(10000)})
        state["regions"].append("inactive_region")
        soak.reconstruct(state, profile.representation_limit)
        self.assertEqual(before, len(state["activeRepresentations"]))
        state["activeRegionId"] = "inactive_region"
        soak.reconstruct(state, profile.representation_limit)
        self.assertLessEqual(before, profile.representation_limit)
        self.assertEqual(profile.representation_limit, len(state["activeRepresentations"]))

    def test_injected_failures_have_bounded_stable_diagnostics(self):
        cases = []
        ownership = soak.build_fixture(self.config, self.sources, 1450)
        province = sorted(ownership["provinceOwnership"])[0]
        ownership["provinceOwnership"][province]["controllerId"] = "missing_polity"
        cases.append((ownership, "military", "ownership_control", province))
        scheduling = soak.build_fixture(self.config, self.sources, 1450)
        scheduling["nextTickDay"] += 1
        cases.append((scheduling, "timeline", "scheduling", "logical_tick"))
        references = soak.build_fixture(self.config, self.sources, 1450)
        references["resolvedTreasures"].append("missing_treasure")
        cases.append((references, "treasure", "reference", "missing_treasure"))
        for state, subsystem, invariant, entity_id in cases:
            day = date.fromisoformat(state["date"]).toordinal()
            with self.assertRaises(soak.InvariantFailure) as caught:
                soak.validate(state, day, subsystem, self.config["workload"], 64)
            self.assertEqual({"date", "subsystem", "invariant", "entityId", "message"},
                             set(caught.exception.diagnostic))
            self.assertEqual("1450-01-01", caught.exception.diagnostic["date"])
            self.assertEqual(subsystem, caught.exception.diagnostic["subsystem"])
            self.assertEqual(invariant, caught.exception.diagnostic["invariant"])
            self.assertEqual(entity_id, caught.exception.diagnostic["entityId"])
        corrupt = soak.checkpoint(soak.build_fixture(self.config, self.sources, 1450))
        corrupt["state"]["ticks"] += 1
        with self.assertRaisesRegex(soak.SoakError, "hash mismatch"):
            soak.resume(corrupt)

    def test_cli_emits_compact_machine_readable_summary(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "summary.json"
            completed = subprocess.run([sys.executable, str(CLI), "--summary-out", str(output)],
                                       text=True, capture_output=True, check=False)
            self.assertEqual(0, completed.returncode, completed.stderr or completed.stdout)
            self.assertEqual(json.loads(completed.stdout), json.loads(output.read_text()))
            self.assertEqual(soak.SUMMARY_FORMAT, json.loads(completed.stdout)["format"])


if __name__ == "__main__":
    unittest.main()

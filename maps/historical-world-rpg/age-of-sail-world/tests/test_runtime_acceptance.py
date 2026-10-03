import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("runtime_acceptance", PROJECT / "tooling/runtime_acceptance.py")
runtime = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(runtime)


class RuntimeAcceptanceTests(unittest.TestCase):
    def test_manifest_covers_required_player_systems_and_reports_stage_distinctions(self):
        report = runtime.audit_sources()
        ids = {row["id"] for row in report["systems"] if row["releaseRequired"]}
        self.assertTrue({"campaign_launch", "origin_selection", "country_diplomacy", "trade",
                         "army_fleet_control", "city_capture", "garrisons", "administration",
                         "heroes", "inventory_equipment", "technology_institutions",
                         "quests_journal", "treasures_discovery", "save_autosave_load",
                         "cross_map_travel", "world_map", "remote_management",
                         "government_rewards"} <= ids)
        self.assertEqual(list(runtime.STAGES), report["stages"])
        self.assertEqual("fail", report["status"])

    def test_backend_only_feature_is_a_release_failure(self):
        report = runtime.audit_sources()
        trade = next(row for row in report["systems"] if row["id"] == "trade")
        self.assertTrue(trade["stages"]["dataComplete"])
        self.assertFalse(trade["stages"]["playerFacingComplete"])
        self.assertTrue(any(message.startswith("trade:") for message in report["failures"]))

    def test_country_diplomacy_and_government_rewards_use_real_release_entry_points(self):
        report = runtime.audit_sources()
        rows = {row["id"]: row for row in report["systems"]}
        for system_id in ("country_diplomacy", "government_rewards"):
            self.assertEqual({stage: True for stage in runtime.STAGES},
                             rows[system_id]["stages"])
            self.assertEqual([], rows[system_id]["diagnostics"])
        self.assertFalse(any("RUNTIME-MISSING-COUNTRY-DIPLOMACY" in failure or
                             "RUNTIME-MISSING-GOVERNMENT-REWARDS" in failure
                             for failure in report["failures"]))

    def test_compiled_artifact_must_contain_every_required_link_marker(self):
        manifest = runtime.load_manifest()
        script = "\n".join(token for row in manifest["systems"] if row["releaseRequired"]
                           for token in row["artifactMarkers"])
        self.assertEqual("pass", runtime.verify_compiled_script(script)["status"])
        result = runtime.verify_compiled_script(script.replace("registerOriginSelection", ""))
        self.assertEqual("fail", result["status"])
        self.assertTrue(any("origin_selection" in x for x in result["failures"]))

    def test_required_system_cannot_be_declared_simulation_only(self):
        data = runtime.load_manifest(); data = copy.deepcopy(data)
        data["systems"][0]["simulationOnly"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(runtime.RuntimeAcceptanceError, "cannot be simulation-only"):
                runtime.audit_sources(path)


if __name__ == "__main__":
    unittest.main()

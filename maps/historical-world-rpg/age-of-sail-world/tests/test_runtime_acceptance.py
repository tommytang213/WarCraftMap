import copy
import importlib.util
import json
import tempfile
import unittest
import zipfile
import struct
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("runtime_acceptance", PROJECT / "tooling/runtime_acceptance.py")
runtime = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(runtime)


class RuntimeAcceptanceTests(unittest.TestCase):
    def test_locked_current_client_w3i_and_exact_rc1_regression(self):
        current = (PROJECT / "map/AgeOfSailWorld.w3x/war3map.w3i").read_bytes()
        info = runtime.validate_current_w3i(current)
        self.assertEqual((33, 6116, (3, 0, 0, 24268)),
                         (info["format"], info["editorVersion"], info["gameVersion"]))
        fixture = Path(__file__).parent / "fixtures/phase9-rc1-failing-map-metadata.json"
        failing = json.loads(fixture.read_text())
        malformed = bytearray(current)
        struct.pack_into("<i", malformed, 0, failing["w3i"]["format"])
        with self.assertRaisesRegex(runtime.MapInfoError, "not current format"):
            runtime.validate_current_w3i(bytes(malformed))

    def executable_script(self):
        calls = sorted({call for required, _ in runtime.EXECUTABLE_PROOFS.values()
                        for call in required})
        commands = sorted({command for _, required in runtime.EXECUTABLE_PROOFS.values()
                           for command in required})
        return ("function main()\n" + "\n".join(f"  {call}()" for call in calls) +
                "\n" + "\n".join(f'  registry:register("{command}", handler)'
                                   for command in commands) + "\nend\n")

    def test_manifest_covers_required_player_systems_and_reports_stage_distinctions(self):
        report = runtime.audit_sources()
        ids = {row["id"] for row in report["systems"] if row["releaseRequired"]}
        self.assertTrue({"campaign_launch", "origin_selection", "country_diplomacy", "trade",
                         "army_fleet_control", "city_capture", "garrisons", "administration",
                         "heroes", "inventory_equipment", "technology_institutions",
                         "quests_journal", "treasures_discovery", "save_autosave_load",
                         "cross_map_travel", "world_map", "remote_management",
                         "government_rewards", "religion", "piracy"} <= ids)
        self.assertEqual(list(runtime.STAGES), report["stages"])
        self.assertEqual("pass", report["status"])

    def test_trade_has_real_runtime_entry_and_release_evidence(self):
        report = runtime.audit_sources()
        trade = next(row for row in report["systems"] if row["id"] == "trade")
        self.assertTrue(all(trade["stages"][stage] for stage in runtime.STAGES[:-1]))
        self.assertFalse(trade["stages"]["releaseValidated"])
        self.assertEqual([], trade["diagnostics"])
        self.assertFalse(any(message.startswith("trade:") for message in report["failures"]))

    def test_country_diplomacy_and_government_rewards_use_real_release_entry_points(self):
        report = runtime.audit_sources()
        rows = {row["id"]: row for row in report["systems"]}
        for system_id in ("country_diplomacy", "government_rewards"):
            self.assertTrue(all(rows[system_id]["stages"][stage]
                                for stage in runtime.STAGES[:-1]))
            self.assertFalse(rows[system_id]["stages"]["releaseValidated"])
            self.assertEqual([], rows[system_id]["diagnostics"])
        self.assertFalse(any("RUNTIME-MISSING-COUNTRY-DIPLOMACY" in failure or
                             "RUNTIME-MISSING-GOVERNMENT-REWARDS" in failure
                             for failure in report["failures"]))

    def test_compiled_artifact_requires_executable_calls_and_registrations(self):
        script = self.executable_script()
        self.assertEqual("pass", runtime.verify_compiled_script(script)["status"])
        result = runtime.verify_compiled_script(script.replace("  registerOriginSelection()", ""))
        self.assertEqual("fail", result["status"])
        self.assertTrue(any("origin_selection" in x for x in result["failures"]))

    def test_classes_commands_and_markers_without_bootstrap_calls_fail(self):
        marker_only = '\n'.join(
            ["function main() end", "-- registerOriginSelection initializePlayableCampaignRuntime",
             'local marker = "commands.register(\\"origin\\")"',
             "function registerOriginSelection() end"])
        result = runtime.verify_compiled_script(marker_only)
        self.assertEqual("fail", result["status"])
        self.assertTrue(any("production calls absent" in x for x in result["failures"]))

    def test_compiled_lua_payload_budgets_reject_pathological_line(self):
        result = runtime.verify_compiled_script("function main() " +
                                                "x" * (runtime.MAX_LUA_LINE_BYTES + 1) + " end")
        self.assertEqual("fail", result["status"])
        self.assertTrue(any("line exceeds" in x for x in result["failures"]))

    def test_bootstrap_compiled_semantics_require_native_transition_before_end(self):
        good = "function main() TimerStart() showPage() SetNextLevel(path) EndGame(true) end"
        self.assertEqual("pass", runtime.verify_compiled_bootstrap(good)["status"])
        lost_native = "-- source said SetNextLevelBJ\nfunction main() TimerStart() showPage() EndGame(true) end"
        self.assertEqual("fail", runtime.verify_compiled_bootstrap(lost_native)["status"])
        reversed_calls = "function main() TimerStart() showPage() EndGame(true) SetNextLevel(path) end"
        self.assertEqual("fail", runtime.verify_compiled_bootstrap(reversed_calls)["status"])

    def test_bootstrap_compiled_semantics_reject_global_scenario_registrations(self):
        script = "function main() TimerStart() showPage() registerSettlement(x) SetNextLevel(path) EndGame(true) end"
        result = runtime.verify_compiled_bootstrap(script)
        self.assertEqual("fail", result["status"])
        self.assertTrue(any("regional registration" in x for x in result["failures"]))

    def test_valid_metadata_with_blank_placeholder_terrain_fails(self):
        source = PROJECT / "map/AgeOfSailWorld.w3x"
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "placeholder.w3x"
            with zipfile.ZipFile(fixture, "w") as archive:
                for name in ("war3mapUnits.doo", "war3map.w3i"):
                    archive.write(source / name, name)
                w3e = bytearray((source / "war3map.w3e").read_bytes())
                offset = 13
                ground = struct.unpack_from("<I", w3e, offset)[0]; offset += 4 + ground * 4
                cliffs = struct.unpack_from("<I", w3e, offset)[0]; offset += 4 + cliffs * 4 + 16
                w3e[offset:] = w3e[offset:offset + 7] * ((len(w3e) - offset) // 7)
                wpm = bytearray((source / "war3map.wpm").read_bytes())
                wpm[16:] = bytes([wpm[16]]) * (len(wpm) - 16)
                archive.writestr("war3map.w3e", w3e)
                archive.writestr("war3map.wpm", wpm)
                archive.writestr("war3map.lua", self.executable_script())
                archive.writestr("runtime/scenario-runtime.json", json.dumps({
                    "ids": {"polities": ["fixture"]}, "regionalGeography": ["fixture"]}))
                archive.writestr("runtime/physical-map.json", json.dumps({
                    "physicalMapId": "placeholder", "bootstrap": False}))
            result = runtime.inspect_built_map(fixture, "placeholder", False)
            self.assertEqual("fail", result["status"])
            self.assertTrue(any("placeholder" in message for message in result["failures"]))

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

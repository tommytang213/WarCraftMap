import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("phase6_asset_audit", ROOT / "tooling/phase6_asset_audit.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class Phase6AssetAuditTests(unittest.TestCase):
    def test_checked_in_report_is_deterministic_and_all_gates_pass(self):
        expected = json.loads((ROOT / "scenario/assets/reports/phase6-asset-audit.json").read_text())
        actual = AUDIT.build_report()
        self.assertEqual(expected, actual)
        self.assertEqual("pass", actual["status"])
        self.assertTrue(all(actual["gates"].values()))
        self.assertFalse(actual["licensing"]["unknownLicenseAssets"])
        self.assertGreater(len(actual["inventory"]), 1200)

    def test_every_resolution_is_final_or_intentionally_generic(self):
        rows = AUDIT.build_report()["inventory"]
        allowed = {"custom_asset", "final_stock_asset", "intentional_data_only", "intentional_generic_stock", "final_profile"}
        self.assertEqual(allowed, {row["resolution"] for row in rows})
        for required in ("unit", "ship", "character", "settlement", "building", "equipment", "treasure",
                         "ability", "effect", "terrain_feature", "ui_concept", "quest", "city_core",
                         "defense", "settlement_role", "music_cue", "ambience_cue", "sound_event",
                         "audio_asset", "audio_profile"):
            self.assertIn(required, {row["kind"] for row in rows})

    def test_budget_and_marker_failures_are_fatal(self):
        report = AUDIT.build_report()
        self.assertTrue(all(row["actual"] <= row["limit"] for row in report["budgets"].values()))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "scenario").mkdir()
            (root / "scenario/bad.json").write_text('{"asset":"placeholder"}')
            old_root = AUDIT.ROOT
            try:
                AUDIT.ROOT = root
                with self.assertRaisesRegex(AUDIT.AuditError, "unallowlisted"):
                    AUDIT._scan_markers({"markerAllowlist":[]})
            finally:
                AUDIT.ROOT = old_root


if __name__ == "__main__":
    unittest.main()

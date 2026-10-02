import importlib.util
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("coverage", ROOT / "tooling/phase8_content_coverage.py")
COVERAGE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(COVERAGE)


class Phase8ContentTests(unittest.TestCase):
    def build_with_defect(self, relative_path, mutate):
        original = COVERAGE.load
        def fixture(path):
            value = copy.deepcopy(original(path))
            if path == relative_path:
                mutate(value)
            return value
        with patch.object(COVERAGE, "load", side_effect=fixture):
            return COVERAGE.build()

    def test_full_release_coverage_report_is_current_and_passes(self):
        actual = COVERAGE.build()
        expected = json.loads((ROOT / "reports/phase8-content-coverage.json").read_text())
        self.assertEqual(expected, actual)
        self.assertEqual("pass", actual["status"])
        self.assertEqual([], actual["failures"])
        self.assertEqual([1450, 1550, 1650, 1750, 1820], actual["snapshotYears"])
        self.assertEqual(7, len(actual["regions"]))
        self.assertTrue((ROOT / "reports/phase8-content-coverage.md").read_text().startswith("# Phase 8 final release-scale content audit"))

    def test_no_region_or_category_is_hidden_by_global_counts(self):
        report = COVERAGE.build()
        for row in report["regions"].values():
            self.assertGreaterEqual(row["regionalQuests"], 2)
            self.assertGreaterEqual(row["personalQuests"], 1)
            self.assertGreaterEqual(row["treasures"], 3)
            self.assertGreater(row["goods"], 0)
            self.assertGreater(row["events"], 0)
        self.assertEqual([], report["thinContentFlags"])

    def test_every_settlement_resolves_all_release_systems(self):
        categories = COVERAGE.build()["categories"]
        count = categories["economy"]["settlementsResolved"]
        self.assertEqual(count, categories["governance"]["settlementsResolved"])
        self.assertEqual(count, categories["garrisons"]["settlementsResolved"])
        self.assertEqual(0, categories["governance"]["authoritativePhysicalDuplicates"])

    def test_content_evolves_after_campaign_start(self):
        report = COVERAGE.build()
        self.assertGreater(report["categories"]["progression"]["newAfter1450"], 0)
        self.assertGreater(report["eras"]["1820"]["progressionNodesAvailable"], report["eras"]["1450"]["progressionNodesAvailable"])
        self.assertGreater(report["eras"]["1820"]["historicalEventsOccurred"], report["eras"]["1450"]["historicalEventsOccurred"])

    def test_controlled_count_defect_has_stable_diagnostic(self):
        report = self.build_with_defect(
            "scenario/inventory/reports/catalogue-coverage.json",
            lambda row: row.update(ordinaryCount=299),
        )
        self.assertEqual("fail", report["status"])
        self.assertIn("phase8.inventory.ordinary.release_scale", report["failures"])

    def test_controlled_quality_defect_cannot_be_hidden_by_count(self):
        def break_quality(row):
            row["status"] = "fail"
            row["failures"] = ["item:controlled_clone"]
        report = self.build_with_defect("scenario/inventory/reports/catalogue-coverage.json", break_quality)
        self.assertIn("phase8.inventory.ordinary.release_scale", report["failures"])
        self.assertEqual(367, report["categories"]["inventory"]["ordinary"])

    def test_controlled_budget_defect_has_stable_diagnostic(self):
        def break_budget(row): row["budgetChecks"][0]["passed"] = False
        report = self.build_with_defect("reports/release-settlement-audit.json", break_budget)
        self.assertIn("phase8.budgets.release_scale", report["failures"])

    def test_human_report_is_deterministic(self):
        report = COVERAGE.build()
        self.assertEqual((ROOT / "reports/phase8-content-coverage.md").read_text(), COVERAGE.markdown(report))


if __name__ == "__main__": unittest.main()

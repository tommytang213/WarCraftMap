import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))
from vessel_progression_report import validate


class VesselProgressionReportTests(unittest.TestCase):
    def test_catalog_references_coverage_balance_and_deterministic_report(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / "first.json", Path(directory) / "second.json"
            report = validate(first); validate(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(8, len(report["coverage"]["refitCategories"]))
        self.assertEqual(5, report["counts"]["milestones"])
        self.assertEqual(3, report["counts"]["initialVessels"])
        bands = report["experienceBands"]
        for role in report["coverage"]["roles"]:
            values = [x for x in bands if x["roleId"] == role]
            self.assertEqual([0, 200, 700, 1600, 3000, 6000, 12000], [x["experience"] for x in values])
            self.assertTrue(all(x["maximumSingleEffectBasisPoints"] <= 4000 for x in values))


if __name__ == "__main__": unittest.main()

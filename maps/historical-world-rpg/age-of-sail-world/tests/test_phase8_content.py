import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("coverage", ROOT / "tooling/phase8_content_coverage.py")
COVERAGE = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(COVERAGE)


class Phase8ContentTests(unittest.TestCase):
    def test_coverage_report_is_current_and_substantial(self):
        actual = COVERAGE.build()
        expected = json.loads((ROOT / "reports/phase8-content-coverage.json").read_text())
        self.assertEqual(expected, actual)
        self.assertGreaterEqual(actual["quests"]["byType"]["regional"], 14)
        self.assertGreaterEqual(actual["quests"]["byType"]["personal"], 7)
        self.assertGreaterEqual(actual["treasures"]["byKind"]["generic"], 21)


if __name__ == "__main__": unittest.main()

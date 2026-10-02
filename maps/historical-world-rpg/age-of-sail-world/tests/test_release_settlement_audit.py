import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tooling/release_settlement_audit.py"
SPEC = importlib.util.spec_from_file_location("release_settlement_audit", TOOL)
AUDIT = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(AUDIT)


class ReleaseSettlementAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = AUDIT.build_report()

    def test_checked_in_machine_and_human_reports_are_deterministic(self):
        self.assertEqual(self.report, AUDIT.build_report())
        self.assertEqual(self.report, json.loads((ROOT / "reports/release-settlement-audit.json").read_text()))
        completed = subprocess.run([sys.executable, str(TOOL)], cwd=ROOT, text=True,
                                   capture_output=True, check=False)
        self.assertEqual(0, completed.returncode, completed.stderr or completed.stdout)
        self.assertIn("Result: **PASS**", (ROOT / "reports/release-settlement-audit.md").read_text())

    def test_global_target_and_regional_variances_are_evidence_led(self):
        report = self.report
        self.assertEqual("pass", report["status"])
        self.assertLessEqual(report["global"]["minimum"], report["global"]["count"])
        self.assertLessEqual(report["global"]["count"], report["global"]["planningMaximum"])
        outside = [row for row in report["regionalGates"].values() if not row["withinPlanningRange"]]
        self.assertTrue(outside)
        self.assertTrue(all(row["acceptedVariance"]["rationale"] and
                            row["acceptedVariance"]["evidenceIds"] for row in outside))

    def test_every_identity_is_integrated_once_without_padding(self):
        report = self.report
        self.assertTrue(report["runtimeIntegration"]["worldIdentityMatch"])
        self.assertEqual(827, report["runtimeIntegration"]["settlementsChecked"])
        self.assertEqual([], report["failures"])
        self.assertEqual([], report["thinness"]["materialFlags"])
        self.assertGreater(report["historicalCoverage"]["settlementEvidenceAssignments"],
                           report["global"]["authoredRegionalRecords"])

    def test_distribution_sparse_treatment_and_finalized_budgets_are_audited(self):
        distribution = self.report["distribution"]
        for key in ("byRegion", "bySubregion", "byPolity", "byProvince", "byAuthorityType",
                    "byProvinceType", "byRole", "byPhysicalMap", "byEvidenceClass"):
            self.assertTrue(distribution[key], key)
        self.assertGreaterEqual(len(self.report["sparseAndAbstractTreatment"]), 7)
        self.assertTrue(all(row["rationale"] for row in self.report["sparseAndAbstractTreatment"]))
        self.assertTrue(all(row["passed"] for row in self.report["budgetChecks"]))

    def test_duplicate_identity_heuristic_catches_trivial_renaming(self):
        self.assertEqual(AUDIT._identity("Kilwa Kisiwani"), AUDIT._identity("Kílwa-Kisiwani"))
        self.assertTrue(AUDIT.PLACEHOLDER.search("placeholder_port"))


if __name__ == "__main__":
    unittest.main()

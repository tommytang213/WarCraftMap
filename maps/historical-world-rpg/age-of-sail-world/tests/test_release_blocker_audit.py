import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
TOOL = PROJECT / "tooling/release_blocker_audit.py"
SPEC = importlib.util.spec_from_file_location("release_blocker_audit", TOOL)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class ReleaseBlockerAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit.build_report()

    def test_gate_passes_when_all_player_runtime_paths_are_release_validated(self):
        self.assertEqual(cls_json(self.report), cls_json(audit.build_report()))
        self.assertEqual("pass", self.report["status"])
        self.assertEqual(0, self.report["unresolvedCampaignBlockers"])
        self.assertEqual("gate_closed", self.report["disposition"])
        runtime = self.report["runtimeAcceptance"]
        self.assertEqual("pass", runtime["status"])
        by_id = {row["id"]: row for row in runtime["systems"]}
        self.assertTrue(all(by_id["trade"]["stages"].values()))

    def test_taxonomy_explicitly_blocks_campaign_failures_and_unclassified_critical_failures(self):
        taxonomy = {row["id"]: row for row in self.report["taxonomy"]}
        self.assertTrue(taxonomy["campaign_blocker"]["releaseBlocking"])
        self.assertIn("starting", taxonomy["campaign_blocker"]["definition"])
        self.assertTrue(taxonomy["critical_unclassified"]["releaseBlocking"])
        self.assertFalse(taxonomy["major"]["releaseBlocking"])

    def test_journeys_span_every_region_system_branch_and_repeated_map_transition(self):
        config = json.loads((PROJECT / "scenario/release-blocker-gate.json").read_text())
        covered = {system for row in self.report["journeys"] for system in row["systems"]}
        regions = {region for row in self.report["journeys"] for region in row["regions"]}
        self.assertEqual(set(config["requiredSystems"]), covered)
        self.assertEqual({"europe", "africa", "middle_east_india", "southeast_asia",
                          "east_asia", "americas_caribbean", "pacific"}, regions)
        self.assertIn("alternate_history", {row["branch"] for row in self.report["journeys"]})
        self.assertTrue(all(row["physicalMaps"][0] == row["physicalMaps"][-1]
                            for row in self.report["journeys"]))
        self.assertTrue(all(row["endDate"].startswith("1820-") for row in self.report["journeys"]))

    def test_every_known_blocker_class_is_detected_with_actionable_stable_diagnostic(self):
        config = json.loads((PROJECT / "scenario/release-blocker-gate.json").read_text())
        injected = [audit._finding(f"INJECT-{index:02d}-{kind.upper().replace('_', '-')}", kind,
                                   f"fixture/{kind}", f"reproduce injected {kind}")
                    for index, kind in enumerate(config["blockerClasses"], 1)]
        report = audit.build_report(injected_findings=injected)
        self.assertEqual("fail", report["status"])
        self.assertGreaterEqual(report["unresolvedCampaignBlockers"], len(injected))
        self.assertEqual(set(config["blockerClasses"]), {row["class"] for row in report["findings"]})
        self.assertTrue(all(audit.STABLE_ID.fullmatch(row["id"]) and row["context"] and row["message"]
                            for row in report["findings"]))

    def test_release_save_compatibility_matrix_is_part_of_the_gate(self):
        compatibility = self.report["releaseSaveCompatibility"]
        self.assertEqual("pass", compatibility["status"])
        self.assertEqual([1, 2, 3, 4, 5], compatibility["schemas"])
        self.assertEqual(["migrated", "migrated", "migrated", "migrated", "compatible"],
                         compatibility["statuses"])
        self.assertEqual(1, len(compatibility["authoritySha256"]))
        self.assertIn(compatibility["manifest"], self.report["releaseInputs"])

    def test_unknown_critical_class_cannot_escape_unclassified_gate(self):
        finding = audit._finding("INJECT-UNKNOWN-CRITICAL", "start_failure", "fixture/unknown",
                                 "unknown failure")
        finding["class"] = "not_classified"
        finding["severity"] = "invented"
        report = audit.build_report(injected_findings=[finding])
        unknown = next(row for row in report["findings"] if row["id"] == "INJECT-UNKNOWN-CRITICAL")
        self.assertEqual("critical_unclassified", unknown["severity"])
        self.assertEqual("fail", report["status"])

    def test_checked_in_machine_and_human_reports_are_current(self):
        completed = subprocess.run([sys.executable, str(TOOL)], cwd=PROJECT, text=True,
                                   capture_output=True, check=False)
        self.assertEqual(0, completed.returncode, completed.stderr or completed.stdout)
        summary = json.loads(completed.stdout)
        self.assertEqual("pass", summary["status"])
        self.assertEqual(0, summary["unresolvedCampaignBlockers"])
        human = (PROJECT / "reports/release-blocker-audit.md").read_text()
        self.assertIn("JOURNEY-ALTERNATE-HISTORY", human)
        self.assertIn("Player-facing runtime acceptance", human)


def cls_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


if __name__ == "__main__":
    unittest.main()

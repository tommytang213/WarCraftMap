import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
TOOL = PROJECT / "tooling/release_blocker_audit.py"
SPEC = importlib.util.spec_from_file_location("release_blocker_audit", TOOL)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class ReleaseBlockerAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit.build_report()

    def test_source_readiness_cannot_pass_the_release_gate(self):
        self.assertEqual(cls_json(self.report), cls_json(audit.build_report()))
        self.assertEqual("fail", self.report["status"])
        self.assertFalse(self.report["candidateReady"])
        self.assertGreater(self.report["unresolvedCampaignBlockers"], 0)
        self.assertEqual("release_blocked", self.report["disposition"])
        runtime = self.report["runtimeAcceptance"]
        self.assertEqual("fail", runtime["status"])
        by_id = {row["id"]: row for row in runtime["systems"]}
        self.assertTrue(all(by_id["trade"]["sourceChecks"][stage]
                            for stage in audit.runtime_acceptance.STAGES[:-1]))
        self.assertFalse(by_id["trade"]["stages"]["releaseValidated"])
        self.assertEqual("same-revision production execution and exact built W3N/W3X inspection",
                         runtime["releaseValidationAuthority"])

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
        self.assertEqual([1, 2, 3, 4, 5, 6, 7, 8, 9], compatibility["schemas"])
        self.assertEqual(["migrated"] * 8 + ["compatible"],
                         compatibility["statuses"])
        self.assertEqual(1, len(compatibility["authoritySha256"]))
        self.assertIn(compatibility["manifest"], self.report["releaseInputs"])

    def test_declared_itineraries_do_not_claim_route_or_native_save_execution(self):
        self.assertEqual("headless_fixture_execution", self.report["soak"]["evidenceLevel"])
        for journey in self.report["journeys"]:
            self.assertEqual("headless_save_fixture_execution", journey["evidenceLevel"])
            self.assertEqual(["save_round_trip", "schema_3_migration"], journey["executedChecks"])
            self.assertEqual("declared_journey_metadata", journey["coverageEvidenceLevel"])
            self.assertEqual("not_run", journey["routeExecutionStatus"])
            self.assertEqual("not_run", journey["nativeSaveExecutionStatus"])
        self.assertIn("not executed by this audit", audit.render_markdown(self.report))

    def test_blocker_aggregation_requires_complete_integration_and_artifact_evidence(self):
        # Synthetic aggregation protocol only; never emitted as release evidence.
        complete = copy.deepcopy(self.report["runtimeAcceptance"])
        identity = {"sourceRevision": "a" * 40, "sourceTreeSha256": "b" * 64}
        complete.update(identity, executionStatus="completed")
        for name in ("runtimeIntegration", "builtArtifact"):
            complete["evidenceLevels"][name].update(identity, status="pass", executionStatus="completed", failures=[])
        complete["evidenceLevels"]["runtimeIntegration"].update(logSha256="c" * 64, inputSetSha256="d" * 64)
        complete["evidenceLevels"]["builtArtifact"]["artifactSha256"] = "e" * 64
        for row in complete["systems"]:
            row.update(executionStatus="completed", executedTests=["synthetic fixture"])
            row["stages"].update({stage: True for stage in audit.runtime_acceptance.STAGES})
        for mode in ("complete", "not_run", "missing", "stale", "declared", "releaseValidated=false",
                     "omitted-system", "exempted-system"):
            current = copy.deepcopy(complete)
            if mode == "not_run":
                current["evidenceLevels"]["runtimeIntegration"]["executionStatus"] = "not_run"
            elif mode == "missing":
                del current["evidenceLevels"]["runtimeIntegration"]
            elif mode == "stale":
                current["evidenceLevels"]["builtArtifact"]["sourceRevision"] = "c" * 40
            elif mode == "declared":
                current["evidenceLevels"]["runtimeIntegration"]["evidenceLevel"] = "declared_journey_metadata"
            elif mode == "releaseValidated=false":
                current["systems"][0]["stages"]["releaseValidated"] = False
            elif mode == "omitted-system":
                current["systems"].pop()
            elif mode == "exempted-system":
                current["systems"][0]["releaseRequired"] = False
            audit.runtime_acceptance.finalize(current)
            with self.subTest(mode=mode), \
                 patch.object(audit, "_audit_reports", return_value=([], [])), \
                 patch.object(audit, "_audit_inputs", return_value=({}, [])), \
                 patch.object(audit, "_audit_release_save_compatibility", return_value=self.report["releaseSaveCompatibility"]), \
                 patch.object(audit, "_run_journeys", return_value=(self.report["journeys"], self.report["soak"])), \
                 patch.object(audit.runtime_acceptance, "audit_acceptance", return_value=current):
                report = audit.build_report()
                self.assertEqual(mode == "complete", report["candidateReady"])
                self.assertEqual("pass" if mode == "complete" else "fail", report["status"])
                self.assertEqual("not_run", report["evidenceLevels"]["realClient"]["executionStatus"])

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
        self.assertEqual(1, completed.returncode, completed.stderr or completed.stdout)
        summary = json.loads(completed.stdout)
        self.assertEqual("fail", summary["status"])
        self.assertGreater(summary["unresolvedCampaignBlockers"], 0)
        human = (PROJECT / "reports/release-blocker-audit.md").read_text()
        self.assertIn("JOURNEY-ALTERNATE-HISTORY", human)
        self.assertIn("Player-facing runtime acceptance", human)


def cls_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


if __name__ == "__main__":
    unittest.main()

"""Synthetic transcripts test the gate protocol; they are never release evidence."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
sys.path.insert(0, str(PROJECT / "tooling"))
import integration_evidence as evidence
import runtime_acceptance as runtime
import wurst_execution as execution
import package_release_candidate as release


class IntegrationEvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name)
        (self.project / "wurst").mkdir()
        self.production = self.project / "wurst/Production.wurst"
        self.production.write_text('package Production\npublic function registration()\n'
                                   '\t// comment before body must not affect indentation\n\tskip\n'
                                   'public function adapter()\n\tskip\n')
        (self.project / "package.json").write_text(json.dumps({"executionCoverage": "coverage.json"}))
        self.contract = {"format": "warcraftmap_execution_coverage_v1", "probes": {
            "register": {"path": "wurst/Production.wurst", "signature": "public function registration()"},
            "adapter": {"path": "wurst/Production.wurst", "signature": "public function adapter()"}},
            "systems": {"trade": ["register", "adapter"]}}
        (self.project / "coverage.json").write_text(json.dumps(self.contract))
        self.revision = "a" * 40
        self.expected = [{"id": "wurst/FixtureTests.wurst:integration", "line": 2}]
        (self.project / "wurst/FixtureTests.wurst").write_text('package FixtureTests\n@test function integration()\n\tskip\n')
        self.baseline = runtime.audit_sources()
        self.baseline["systems"] = [row for row in self.baseline["systems"] if row["id"] == "trade"]
        # This disposable scenario intentionally has one required system.
        required = patch.object(runtime, "MANDATORY_SYSTEMS", frozenset({"trade"}))
        required.start()
        self.addCleanup(required.stop)

    def transcript(self, hits=("register", "adapter")):
        log = ("Running tests\nRunning /test/wurst/FixtureTests.wurst:2 - integration..\n" +
               "".join(f"WCM_PROBE:{hit}\n" for hit in hits) +
               "\tOK!\nTests succeeded: 1/1\nFinished running tests\n").encode()
        rows, issues = execution.parse_results(log.decode(), self.expected)
        inputs = {"wurst/Production.wurst": evidence.digest(evidence.instrument(
            self.production.read_text(), self.contract["probes"]).encode()),
                  "wurst/FixtureTests.wurst": evidence.digest((self.project / "wurst/FixtureTests.wurst").read_bytes())}
        report = {"format": execution.FORMAT, "status": "pass", "executionStatus": "completed",
                  "sourceRevision": self.revision, "sourceIdentity": evidence.source_identity(self.project, self.revision),
                  "expected": self.expected, "tests": rows, "errors": issues, "returnCode": 0,
                  "logSha256": evidence.digest(log), "inputs": inputs,
                  "inputSetSha256": evidence.digest(evidence.canonical(inputs)),
                  "discovered": 1, "succeeded": 1, "compiler": {"sha256": execution.PINNED_COMPILER_SHA256},
                  "productionCoverage": {"contractSha256": evidence.digest(evidence.canonical(self.contract)),
                                         "tests": evidence.observed_probes(log.decode(), rows, self.contract)}}
        return report, log

    def acceptance(self, report, log, *, artifact=True):
        identity = evidence.source_identity(self.project, self.revision)
        built = {"status": "pass", "executionStatus": "completed", "runtimeExecutionStatus": "not_run",
                 "evidenceLevel": "built_artifact_verification", "artifactSha256": "b" * 64,
                 "failures": [], **identity}
        with patch.object(runtime, "PROJECT", self.project), \
             patch.object(runtime, "audit_sources", return_value=copy.deepcopy(self.baseline)), \
             patch.object(release, "load_campaign_config"), \
             patch.object(release, "verify_campaign_runtime", return_value=built):
            return runtime.audit_acceptance(execution=report, execution_log=log, revision=self.revision,
                                            campaign=self.project / "fixture.w3n" if artifact else None)

    def test_complete_evidence_promotes_only_automated_candidate(self):
        report, log = self.transcript()
        result = self.acceptance(report, log)
        self.assertEqual("pass", result["status"])
        self.assertTrue(result["candidateReady"])
        self.assertFalse(result["releaseReady"])
        self.assertEqual("not_run", result["evidenceLevels"]["realClient"]["executionStatus"])
        self.assertTrue(result["systems"][0]["stages"]["releaseValidated"])
        result["evidenceLevels"]["realClient"]["status"] = "pass"
        self.assertFalse(runtime.finalize(result)["releaseReady"])

    def test_missing_not_run_failed_stale_or_declared_evidence_cannot_promote(self):
        original, log = self.transcript()
        variants = [None, {}, "pass", [], {**original, "compiler": "pass"},
                    {**original, "productionCoverage": "pass"}, {**original, "executionStatus": "not_run"},
                    {**original, "sourceRevision": "b" * 40},
                    {**original, "sourceIdentity": {}}, {**original, "productionCoverage": {}},
                    {**original, "status": "fail"}, {**original, "executionStatus": None}]
        for report in variants:
            with self.subTest(report=report):
                result = self.acceptance(report, log)
                self.assertEqual("fail", result["status"])
                self.assertFalse(result["candidateReady"])
                self.assertFalse(result["systems"][0]["stages"]["releaseValidated"])
        self.assertFalse(self.acceptance(original, log, artifact=False)["candidateReady"])

    def test_static_function_test_and_artifact_markers_are_not_production_reachability(self):
        report, log = self.transcript(hits=())
        self.assertEqual({"trade": []}, evidence.verify_execution_coverage(report, log, self.project, self.revision))
        self.assertFalse(self.acceptance(report, log)["candidateReady"])
        # Even explicit coverage declarations cannot replace actual test hits.
        report["productionCoverage"]["tests"] = {self.expected[0]["id"]: ["adapter", "register"]}
        self.assertFalse(self.acceptance(report, log)["candidateReady"])
        report, log = self.transcript(hits=("register",))
        self.assertFalse(self.acceptance(report, log)["candidateReady"])

    def test_false_release_validated_and_stale_artifact_cannot_be_aggregated_to_pass(self):
        report, log = self.transcript()
        good = self.acceptance(report, log)
        cases = []
        bad = copy.deepcopy(good)
        bad["executionStatus"] = "not_run"
        cases.append(bad)
        bad = copy.deepcopy(good)
        bad["evidenceLevels"]["runtimeIntegration"]["evidenceLevel"] = "declared_journey_metadata"
        cases.append(bad)
        bad = copy.deepcopy(good)
        bad["systems"][0]["stages"]["releaseValidated"] = False
        cases.append(bad)
        for key, value in (("executionStatus", "not_run"), ("sourceRevision", "b" * 40),
                           ("sourceTreeSha256", None), ("status", "fail")):
            bad = copy.deepcopy(good)
            bad["evidenceLevels"]["builtArtifact"][key] = value
            cases.append(bad)
        for bad in cases:
            with self.assertRaises(release.PackagingError):
                release.require_candidate_ready(bad)

    def test_malformed_or_missing_acceptance_levels_cannot_authorize_publication(self):
        report, log = self.transcript()
        good = self.acceptance(report, log)
        cases = ["pass", {}, {**good, "systems": []}, {**good, "systems": ["trade"]},
                 {**good, "systems": good["systems"] * 2}]
        for name in ("sourceStatic", "runtimeIntegration", "builtArtifact", "realClient"):
            for value in (None, "pass", []):
                bad = copy.deepcopy(good)
                bad["evidenceLevels"][name] = value
                cases.append(bad)
        for value in (False, None, "false", "true", 1):
            bad = copy.deepcopy(good)
            bad["systems"][0]["stages"]["releaseValidated"] = value
            cases.append(bad)
        for field, value in (("releaseRequired", False), ("simulationOnly", True),
                             ("executedTests", [])):
            bad = copy.deepcopy(good)
            bad["systems"][0][field] = value
            cases.append(bad)
        for stage in runtime.STAGES:
            bad = copy.deepcopy(good)
            del bad["systems"][0]["stages"][stage]
            cases.append(bad)
        for level, field in (("runtimeIntegration", "logSha256"),
                             ("runtimeIntegration", "inputSetSha256"),
                             ("builtArtifact", "artifactSha256")):
            bad = copy.deepcopy(good)
            del bad["evidenceLevels"][level][field]
            cases.append(bad)
        for bad in cases:
            with self.subTest(report=bad), self.assertRaises(release.PackagingError):
                release.require_candidate_ready(bad)

    def test_production_contract_rejects_malformed_json_and_declared_string_lists(self):
        for contract in ("pass", [], {**self.contract, "probes": "register"},
                         {**self.contract, "probes": {"register": "registration"}},
                         {**self.contract, "systems": {"trade": "register"}}):
            (self.project / "coverage.json").write_text(json.dumps(contract))
            with self.subTest(contract=contract), self.assertRaises(ValueError):
                evidence.load_contract(self.project)

    def test_source_edit_at_same_head_invalidates_execution(self):
        report, log = self.transcript()
        self.production.write_text(self.production.read_text() + "// changed\n")
        with self.assertRaisesRegex(ValueError, "stale or missing source identity"):
            evidence.verify_execution_coverage(report, log, self.project, self.revision)

    def test_grill_normalized_build_configuration_retains_both_input_identities(self):
        source = self.project / "wurst.build"
        source.write_text('projectName: "Fixture"\nscriptMode: LUA\nwc3Patch: v3.0\n')
        report, log = self.transcript()
        with self.assertRaisesRegex(ValueError, "compiler configuration input is missing"):
            evidence.verify_execution_coverage(report, log, self.project, self.revision)
        normalized = b'---\nprojectName: "Fixture"\nscriptMode: LUA\nwc3Patch: v3.0\n'
        report["inputs"]["wurst.build"] = evidence.digest(normalized)
        report["inputSetSha256"] = evidence.digest(evidence.canonical(report["inputs"]))
        self.assertTrue(evidence.verify_execution_coverage(report, log, self.project, self.revision)["trade"])
        source.write_text(source.read_text().replace("LUA", "JASS"))
        with self.assertRaisesRegex(ValueError, "stale or missing source identity"):
            evidence.verify_execution_coverage(report, log, self.project, self.revision)

    def test_hits_outside_test_or_after_ok_are_not_coverage(self):
        report, log = self.transcript(hits=())
        log = b"WCM_PROBE:register\n" + log + b"WCM_PROBE:adapter\n"
        self.assertEqual({}, evidence.observed_probes(log.decode(), report["tests"], self.contract))

    def test_fabricated_probe_strings_in_test_source_are_rejected(self):
        (self.project / "wurst/FixtureTests.wurst").write_text(
            'package FixtureTests\n@test function integration()\n\tprint("WCM_PROBE:register")\n')
        with self.assertRaisesRegex(ValueError, "reserved execution probe marker"):
            evidence.instrument_tree(self.project, self.contract)

    def test_passing_different_tests_cannot_combine_into_a_production_path(self):
        tests = [{"id": "wurst/FixtureTests.wurst:first", "status": "pass"},
                 {"id": "wurst/FixtureTests.wurst:second", "status": "pass"}]
        log = ('Running wurst/FixtureTests.wurst:2 - first..\nWCM_PROBE:register\n\tOK!\n'
               'Running wurst/FixtureTests.wurst:4 - second..\nWCM_PROBE:adapter\n\tOK!\n')
        hits = evidence.observed_probes(log, tests, self.contract)
        self.assertFalse(any(set(self.contract["systems"]["trade"]) <= set(row) for row in hits.values()))

    def test_probes_are_executable_body_statements_and_source_is_restored(self):
        original = self.production.read_bytes()
        originals = evidence.instrument_tree(self.project, self.contract)
        instrumented = self.production.read_text()
        self.assertIn('registration()\n\tprint("WCM_PROBE:register")\n', instrumented)
        for path, data in originals.items():
            path.write_bytes(data)
        self.assertEqual(original, self.production.read_bytes())
        for source in ('// public function registration()\n\tskip\n',
                       'interface Production\n\tpublic function registration()\n'):
            with self.assertRaises(ValueError):
                evidence.instrument(source, {"register": self.contract["probes"]["register"]})


if __name__ == "__main__":
    unittest.main()

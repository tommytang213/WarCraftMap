"""Fresh planner audits verify evidence without replacing committed reports."""
import json
import io
import shutil
from pathlib import Path
import sys
import tempfile
import tarfile
import unittest
from unittest import mock

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tooling"))
import planning_audit
import execution_transport as transport
import integration_evidence as evidence
import wurst_execution as execution


class PlanningAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name)
        (self.project / "physical-maps.json").write_text(json.dumps({
            "outputDirectory": "_build/release", "campaign": {"fileName": "Campaign"}}))
        for name, path in planning_audit.REPORTS.items():
            target = self.project / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({"status": "pass", "old": name}))
        self.revision = "a" * 40

    def regenerate(self, *, identity_changed=False, crash=False):
        identity = {"sourceRevision": self.revision, "sourceTreeSha256": "b" * 64}
        with mock.patch.object(planning_audit, "PROJECT", self.project), \
             mock.patch.object(planning_audit, "source_identity", side_effect=[identity, {} if identity_changed else identity]), \
             mock.patch.object(planning_audit.release_blocker_audit, "build_report", return_value={"status": "fail"},
                               side_effect=ValueError("broken manifest") if crash else None) as release, \
             mock.patch.object(planning_audit.runtime_acceptance, "audit_acceptance", return_value={"status": "fail"}) as runtime, \
             mock.patch.object(planning_audit.requirement_traceability_audit, "build_report", return_value={"status": "fail"}) as trace:
            result = planning_audit.regenerate(self.revision)
        return result, release, runtime, trace

    def test_all_audits_regenerate_without_rewriting_recorded_passes(self):
        before = {p: p.read_bytes() for p in self.project.rglob("*.json")}
        result, release, runtime, trace = self.regenerate()
        self.assertTrue(result["regenerated"])
        for name in planning_audit.REPORTS:
            self.assertEqual(result["reports"][name]["report"]["status"], "fail")
            self.assertEqual(result["reports"][name]["recorded"]["status"], "pass")
        self.assertEqual(before, {p: p.read_bytes() for p in self.project.rglob("*.json")})
        for audit in (release, runtime):
            self.assertIsNone(audit.call_args.kwargs["execution"])
            self.assertIsNone(audit.call_args.kwargs["campaign"])
            self.assertEqual(audit.call_args.kwargs["revision"], self.revision)
        self.assertEqual(trace.call_args.args, (None, None, None, self.revision))

    def test_incomplete_or_stale_evidence_is_not_passed_to_verifiers(self):
        execution = self.project / "_build/wurst-tests"
        execution.mkdir(parents=True)
        (execution / "results.json").write_text('{"sourceRevision":"old"}')
        (execution / "execution.log").write_bytes(b"transcript")
        campaign = self.project / "_build/release/Campaign.w3n"
        campaign.parent.mkdir()
        campaign.write_bytes(b"artifact")
        _, release, runtime, trace = self.regenerate()
        for audit in (release, runtime):
            self.assertIsNone(audit.call_args.kwargs["execution"])
            self.assertEqual(audit.call_args.kwargs["revision"], self.revision)
            self.assertEqual(audit.call_args.kwargs["campaign"], campaign)
        self.assertEqual(trace.call_args.args, (campaign, None, None, self.revision))

    def exported_fixture(self):
        """Real export/reader protocol, with synthetic execution, never closure."""
        (self.project / "wurst").mkdir()
        (self.project / "wurst/Fixture.wurst").write_text('package Fixture\n@test function fixture()\n\tskip\n')
        (self.project / "package.json").write_text('{}')
        expected = execution.discover(self.project)
        log = b'Running tests\nRunning wurst/Fixture.wurst:2 - fixture..\n\tOK!\nTests succeeded: 1/1\nFinished running tests\n'
        rows, issues = execution.parse_results(log.decode(), expected)
        inputs = {"wurst/Fixture.wurst": execution.sha((self.project / 'wurst/Fixture.wurst').read_bytes())}
        report = {"format": execution.FORMAT, "status": "pass", "executionStatus": "completed",
                  "returnCode": 0, "errors": issues, "sourceRevision": self.revision,
                  "sourceIdentity": evidence.source_identity(self.project, self.revision),
                  "expected": expected, "tests": rows, "discovered": 1, "succeeded": 1,
                  "inputs": inputs, "inputSetSha256": execution.sha(execution.canonical(inputs)),
                  "compiler": {"sha256": execution.PINNED_COMPILER_SHA256},
                  "logSha256": execution.sha(log), "productionCoverage": {
                      "contractSha256": execution.sha(execution.canonical({"probes": {}, "systems": {}})), "tests": {}}}
        directory = self.project / "_build/wurst-tests"
        directory.mkdir(parents=True)
        (directory / 'results.json').write_text(json.dumps(report))
        (directory / 'execution.log').write_bytes(log)
        transport.snapshot_inputs(self.project, directory / 'verification-inputs', inputs)
        staged = self.project / '_build/export'
        transport.stage(self.project, staged, self.revision)
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode='w') as output:
            output.add(staged, arcname='.')
        shutil.rmtree(directory)
        directory.mkdir()
        archive.seek(0)
        transport.unpack(archive, directory)
        return report, log, directory

    def test_complete_export_reaches_each_existing_audit(self):
        report, log, _ = self.exported_fixture()
        _, release, runtime, trace = self.regenerate()
        for audit in (release, runtime):
            self.assertEqual(report, audit.call_args.kwargs['execution'])
            self.assertEqual(log, audit.call_args.kwargs['execution_log'])
        self.assertEqual(trace.call_args.args, (None, report, log, self.revision))

    def test_export_tampering_source_change_and_missing_inputs_remain_blocking(self):
        report, log, directory = self.exported_fixture()
        cases = [('sourceRevision', 'b' * 40), ('inputSetSha256', '0' * 64),
                 ('compiler', {}), ('expected', []), ('executionStatus', 'focused')]
        for field, value in cases:
            with self.subTest(field=field):
                (directory / 'results.json').write_text(json.dumps({**report, field: value}))
                _, release, runtime, trace = self.regenerate()
                self.assertIsNone(release.call_args.kwargs['execution'])
                self.assertIsNone(runtime.call_args.kwargs['execution'])
                self.assertIsNone(trace.call_args.args[1])
        (directory / 'results.json').write_text(json.dumps(report))
        for name in ('execution.log', 'verification-inputs/wurst/Fixture.wurst', 'source'):
            path = directory / name if name != 'source' else self.project / 'wurst/Fixture.wurst'
            original = path.read_bytes()
            path.write_bytes(original + b'// changed\n')
            _, release, _, _ = self.regenerate()
            self.assertIsNone(release.call_args.kwargs['execution'])
            path.write_bytes(original)
        (directory / 'verification-inputs/wurst/Fixture.wurst').unlink()
        _, release, _, _ = self.regenerate()
        self.assertIsNone(release.call_args.kwargs['execution'])

    def test_focused_discovery_cannot_claim_the_full_current_source_identity(self):
        report, _, directory = self.exported_fixture()
        (self.project / 'wurst/Additional.wurst').write_text(
            'package Additional\n@test function missingFromFocusedRun()\n\tskip\n')
        report['sourceIdentity'] = evidence.source_identity(self.project, self.revision)
        (directory / 'results.json').write_text(json.dumps(report))
        _, release, runtime, trace = self.regenerate()
        self.assertIsNone(release.call_args.kwargs['execution'])
        self.assertIsNone(runtime.call_args.kwargs['execution'])
        self.assertIsNone(trace.call_args.args[1])

    def test_one_audit_crash_preserves_other_findings(self):
        result, _, runtime, trace = self.regenerate(crash=True)
        self.assertIn("broken manifest", result["reports"]["release"]["error"])
        runtime.assert_called_once()
        trace.assert_called_once()

    def test_sources_changing_during_regeneration_cannot_close_gate(self):
        result, _, _, _ = self.regenerate(identity_changed=True)
        self.assertFalse(result["regenerated"])


if __name__ == "__main__":
    unittest.main()

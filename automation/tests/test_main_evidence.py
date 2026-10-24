"""Controller lifecycle using the real transport and planning execution reader.

Synthetic tests establish protocol behavior only, never agriculture closure.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from automation.warcraftmap_agent import main_evidence, worker
from automation.warcraftmap_agent.closure import build_closure

REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY / 'maps/historical-world-rpg/age-of-sail-world/tooling'))
import planning_audit
import execution_transport as transport
import integration_evidence as evidence
import wurst_execution as execution

A, B = 'a' * 40, 'b' * 40


class MainEvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / 'main'
        self.project = self.repo / 'maps/historical-world-rpg/age-of-sail-world'
        self.issue = self.root / 'issue'
        for project in (self.project, self.issue):
            (project / 'wurst').mkdir(parents=True)
            (project / 'wurst/Fixture.wurst').write_text('package Fixture\n@test function fixture()\n\tskip\n')
            (project / 'package.json').write_text('{}')
        self.config = worker.Config(self.repo, self.root / 'state')
        self.current = True
        self.validation_count = 0
        self.revision = A
        project_patch = mock.patch.object(planning_audit, 'PROJECT', self.project)
        project_patch.start()
        self.addCleanup(project_patch.stop)

    def make_bundle(self, project, revision):
        expected = execution.discover(project)
        log = b'Running tests\nRunning wurst/Fixture.wurst:2 - fixture..\n\tOK!\nTests succeeded: 1/1\nFinished running tests\n'
        rows, issues = execution.parse_results(log.decode(), expected)
        inputs = {'wurst/Fixture.wurst': execution.sha((project / 'wurst/Fixture.wurst').read_bytes())}
        report = {'format': execution.FORMAT, 'status': 'pass', 'executionStatus': 'completed',
                  'returnCode': 0, 'errors': issues, 'sourceRevision': revision,
                  'sourceIdentity': evidence.source_identity(project, revision),
                  'expected': expected, 'tests': rows, 'discovered': 1, 'succeeded': 1,
                  'inputs': inputs, 'inputSetSha256': execution.sha(execution.canonical(inputs)),
                  'compiler': {'sha256': execution.PINNED_COMPILER_SHA256},
                  'logSha256': execution.sha(log), 'productionCoverage': {
                      'contractSha256': execution.sha(execution.canonical({'probes': {}, 'systems': {}})), 'tests': {}}}
        directory = project / '_build/wurst-tests'
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'results.json').write_text(json.dumps(report))
        (directory / 'execution.log').write_bytes(log)
        transport.snapshot_inputs(project, directory / 'verification-inputs', inputs)
        return directory

    def command(self, args, **kwargs):
        self.assertEqual(kwargs['cwd'], self.repo)
        if '--execution-only' in args:
            directory = Path(args[args.index('--evidence-directory') + 1])
            revision = args[args.index('--source-revision') + 1]
            value, _, _ = planning_audit.inspect_execution(revision, directory)
            return subprocess.CompletedProcess(args, 0, json.dumps(value), '')
        self.assertEqual(args[2], 'stage')
        transport.stage(Path(args[3]), Path(args[4]), args[-1])
        return subprocess.CompletedProcess(args, 0, '', '')

    def validate(self, log):
        self.validation_count += 1
        log.write_text('synthetic transport fixture; not game closure\n')
        self.make_bundle(self.project, self.revision)

    def ensure(self, **kwargs):
        return main_evidence.ensure(self.config, self.project, self.revision,
            run=self.command, current=lambda: self.current, validate=kwargs.pop('validate', self.validate), **kwargs)

    def receipt(self):
        return self.config.state_dir / 'main-execution' / self.revision / 'attempt.json'

    def test_distinct_issue_pass_does_not_authorize_main_and_wakes_reuse_verified_bundle(self):
        issue_bundle = self.make_bundle(self.issue, B)
        before = (issue_bundle / 'results.json').read_bytes()
        result = self.ensure()
        self.assertFalse(result['reused'])
        self.assertEqual(self.validation_count, 1)
        report, _ = transport.read_bundle(Path(result['directory']), self.project, A)
        self.assertEqual(report['sourceRevision'], A)
        self.assertEqual(before, (issue_bundle / 'results.json').read_bytes())
        for _ in range(3):
            self.assertTrue(self.ensure()['reused'])
        self.assertEqual(self.validation_count, 1)
        # The published copy is independent of the transient checkout build tree.
        shutil.rmtree(self.project / '_build')
        self.assertTrue(self.ensure()['reused'])

    def test_post_merge_requires_new_revision_and_never_relabels_predecessor(self):
        old = self.ensure()
        old_bytes = (Path(old['directory']) / 'results.json').read_bytes()
        self.revision = B
        new = self.ensure()
        self.assertEqual(self.validation_count, 2)
        self.assertNotEqual(old['directory'], new['directory'])
        self.assertEqual(old_bytes, (Path(old['directory']) / 'results.json').read_bytes())
        transport.read_bundle(Path(new['directory']), self.project, B)

    def test_missing_failed_incomplete_and_issue_only_results_fail_closed_without_wake_loop(self):
        for mode in ('missing', 'failed', 'issue', 'focused', 'incomplete', 'wrong-revision'):
            with self.subTest(mode=mode):
                shutil.rmtree(self.config.state_dir, ignore_errors=True)
                shutil.rmtree(self.project / '_build', ignore_errors=True)
                calls = []
                def validate(log):
                    calls.append(log)
                    if mode == 'failed':
                        raise RuntimeError('framework check failed')
                    if mode == 'missing':
                        return
                    if mode == 'issue':
                        self.make_bundle(self.issue, B)
                        return
                    directory = self.make_bundle(self.project, B if mode == 'wrong-revision' else A)
                    if mode == 'focused':
                        path = directory / 'results.json'
                        report = json.loads(path.read_text())
                        report['executionStatus'] = 'focused'
                        path.write_text(json.dumps(report))
                    if mode == 'incomplete':
                        (directory / 'verification-inputs/wurst/Fixture.wurst').unlink()
                result = self.ensure(validate=validate)
                self.assertIn('error', result)
                self.assertFalse(Path(result['directory']).exists())
                self.assertEqual(json.loads(self.receipt().read_text())['status'], 'failed')
                self.assertIn('error', self.ensure(validate=validate))
                self.assertEqual(len(calls), 1)

    def test_interruption_and_publication_failure_cannot_authorize_next_wake(self):
        def interrupted(log):
            self.validate(log)
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.ensure(validate=interrupted)
        self.assertEqual(json.loads(self.receipt().read_text())['status'], 'running')
        self.assertIn('interrupted', self.ensure()['error'])
        self.assertEqual(self.validation_count, 1)
        self.receipt().unlink()
        replace = os.replace
        def fail_publication(source, destination):
            if Path(destination).name == 'bundle':
                raise OSError('interrupted publication')
            return replace(source, destination)
        with mock.patch.object(main_evidence.os, 'replace', side_effect=fail_publication):
            self.assertIn('interrupted publication', self.ensure()['error'])
        self.assertIn('error', self.ensure())
        self.assertEqual(self.validation_count, 2)

    def test_concurrent_merge_and_authored_source_change_invalidate_attempt(self):
        for change in ('merge', 'source'):
            with self.subTest(change=change):
                shutil.rmtree(self.config.state_dir, ignore_errors=True)
                self.current = True
                source = self.project / 'wurst/Fixture.wurst'
                original = source.read_bytes()
                def changed(log):
                    self.validate(log)
                    if change == 'merge':
                        self.current = False
                    else:
                        source.write_bytes(original + b'// concurrent change\n')
                self.assertIn('changed during', self.ensure(validate=changed)['error'])
                self.assertFalse((self.receipt().parent / 'bundle').exists())
                source.write_bytes(original)

    def test_merge_during_publication_and_tampered_reuse_are_rejected(self):
        replace = os.replace
        def merge_during_publication(source, destination):
            replace(source, destination)
            if Path(destination).name == 'bundle':
                self.current = False
        with mock.patch.object(main_evidence.os, 'replace', side_effect=merge_during_publication):
            self.assertIn('changed during', self.ensure()['error'])
        self.current = True
        self.assertIn('error', self.ensure())
        self.receipt().unlink()
        result = self.ensure()
        (Path(result['directory']) / 'execution.log').write_text('altered transcript')
        self.assertIn('rejected', self.ensure()['error'])
        self.assertEqual(self.validation_count, 2)

    def test_dry_run_and_dirty_main_never_launch_validation(self):
        self.assertIn('dry run', self.ensure(allow_execute=False)['error'])
        self.assertFalse(self.receipt().exists())
        self.current = False
        self.assertIn('changed during', self.ensure()['error'])
        self.assertEqual(self.validation_count, 0)

    def test_malformed_receipt_is_reported_without_launching_validation(self):
        self.receipt().parent.mkdir(parents=True)
        for saved in ([], {'revision': B, 'status': 'passed', 'binding': {}}):
            with self.subTest(saved=saved):
                self.receipt().write_text(json.dumps(saved))
                self.assertIn('malformed current-main validation receipt', self.ensure()['error'])
        self.assertEqual(self.validation_count, 0)

    def test_required_main_checks_use_main_cwd_and_override_skip_environment(self):
        log = self.root / 'checks.log'
        self.config.checks_command = 'complete-checks --all'
        with mock.patch.dict(os.environ, {'WARCRAFTMAP_WURST_CHECK': 'skip'}), \
             mock.patch.object(worker.subprocess, 'Popen') as process:
            process.return_value.wait.return_value = 0
            worker.run_main_checks(self.config, A, log)
        self.assertEqual(process.call_args.kwargs['cwd'], self.repo)
        self.assertEqual(process.call_args.kwargs['env']['WARCRAFTMAP_WURST_CHECK'], 'required')
        self.assertEqual(process.call_args.kwargs['env']['SOURCE_REVISION'], A)

    def test_main_validation_deadline_terminates_the_process_group(self):
        with mock.patch.object(worker.subprocess, 'Popen') as process, \
             mock.patch.object(worker.os, 'killpg') as terminate:
            process.return_value.pid = 12345
            process.return_value.wait.side_effect = [subprocess.TimeoutExpired('checks', 60), 0]
            with self.assertRaises(subprocess.TimeoutExpired):
                worker.run_main_checks(self.config, A, self.root / 'checks.log')
        terminate.assert_called_once_with(12345, worker.signal.SIGTERM)

    def test_read_closure_runs_main_lifecycle_and_feeds_explicit_bundle_into_all_audits(self):
        from automation.tests.test_closure import bundle
        reports = bundle()['reports']
        (self.project / 'physical-maps.json').write_text(json.dumps({
            'outputDirectory': '_build/release', 'campaign': {'fileName': 'Campaign'}}))
        # The separate issue has a real verified protocol pass for a different revision.
        self.make_bundle(self.issue, B)
        def command(args, **kwargs):
            if args[0] == 'git':
                return subprocess.CompletedProcess(args, 0, A if args[1] == 'rev-parse' else '', '')
            if '--execution-only' not in args and 'planning_audit.py' in args[1]:
                path = Path(args[args.index('--evidence-directory') + 1])
                return subprocess.CompletedProcess(args, 0, json.dumps(planning_audit.regenerate(A, path)), '')
            return self.command(args, **kwargs)
        with mock.patch.object(worker, 'roadmap_path', return_value=self.project / 'docs/ROADMAP.md'), \
             mock.patch.object(worker, 'default_branch', return_value='main'), \
             mock.patch.object(worker, 'remote_branch_oid', return_value=A), \
             mock.patch.object(worker, 'run', side_effect=command), \
             mock.patch.object(worker, 'run_main_checks', side_effect=lambda config, revision, log: self.validate(log)), \
             mock.patch.object(planning_audit.release_blocker_audit, 'build_report', return_value=reports['release']['report']) as release, \
             mock.patch.object(planning_audit.runtime_acceptance, 'audit_acceptance', return_value=reports['runtime']['report']) as runtime, \
             mock.patch.object(planning_audit.requirement_traceability_audit, 'build_report', return_value=reports['traceability']['report']) as trace:
            for _ in range(2):
                closure = worker.read_closure(self.config, [], [])
                self.assertTrue(closure.fresh)
                self.assertFalse(closure.active)
        self.assertEqual(self.validation_count, 1)
        for audit in (release, runtime):
            self.assertEqual(audit.call_args.kwargs['execution']['sourceRevision'], A)
            self.assertIsInstance(audit.call_args.kwargs['execution_log'], bytes)
        self.assertEqual(trace.call_args.args[1]['sourceRevision'], A)
        saved = json.loads((self.receipt().parent / 'planning-audit.json').read_text())
        self.assertEqual(saved['revision'], A)
        self.assertTrue(saved['execution']['valid'])
        self.assertEqual(set(saved['reports']), {'release', 'runtime', 'traceability'})

    def test_rejection_blocks_consumer_repair_scheduling_but_valid_comparison_does_not(self):
        # Reuse the complete closure report fixture to preserve unrelated gates.
        from automation.tests.test_closure import bundle
        key = 'release:RESEARCH-UNBOUND-AGRARIAN-IMPROVEMENT-BUILDING-GRANARY'
        data = bundle()
        data['reports']['release']['report']['findings'] = [
            {'id': key.split(':', 1)[1], 'severity': 'campaign_blocker', 'message': 'comparison not verified'}]
        data['reports']['release']['report']['unresolvedCampaignBlockers'] = 1
        data['execution'] = {'valid': False, 'error': 'missing verification inputs'}
        closure = build_closure(data, A)
        self.assertIn('missing verification inputs', closure.blockers['runtime:evidence'].messages)
        self.assertNotIn(key, closure.actionable)
        data['execution'] = {'valid': True}
        closure = build_closure(data, A)
        self.assertIn(key, closure.actionable)


if __name__ == '__main__':
    unittest.main()

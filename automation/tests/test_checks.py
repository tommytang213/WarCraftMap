"""Exercise the real container lifecycle and export protocol with a fake Docker.

Synthetic transcripts verify transport only; they never establish game closure.
"""
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

REPOSITORY = Path(__file__).resolve().parents[2]
SHARED = Path('maps/historical-world-rpg/_shared/tooling')
sys.path.insert(0, str(REPOSITORY / SHARED))
sys.path.insert(0, str(REPOSITORY / 'automation'))
import container_validation
import execution_transport as transport
import integration_evidence
import wurst_execution as execution


class RequiredWurstChecksTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.repo = self.root / 'repo'
        (self.repo / 'automation').mkdir(parents=True)
        for name in ('run_checks.sh', 'container_validation.py', 'wurst_container.sh'):
            shutil.copyfile(REPOSITORY / 'automation' / name, self.repo / 'automation' / name)
        (self.repo / SHARED).mkdir(parents=True)
        for name in ('wurst_execution.py', 'execution_transport.py', 'integration_evidence.py'):
            shutil.copyfile(REPOSITORY / SHARED / name, self.repo / SHARED / name)
        self.project = self.repo / 'maps/historical-world-rpg/age-of-sail-world'
        (self.project / 'wurst').mkdir(parents=True)
        (self.project / 'wurst/Test.wurst').write_text('package Test\n@test function fixture()\n\tskip\n')
        (self.project / 'package.json').write_text('{}')
        self.revision = 'a' * 40
        self.archive = self.root / 'evidence.tar'
        self.bundle = self.root / 'bundle'
        self.bundle.mkdir()
        source = self.project / 'wurst/Test.wurst'
        expected = execution.discover(self.project)
        log = b'Running tests\nRunning wurst/Test.wurst:2 - fixture..\n\tOK!\nTests succeeded: 1/1\nFinished running tests\n'
        rows, issues = execution.parse_results(log.decode(), expected)
        inputs = {'wurst/Test.wurst': execution.sha(source.read_bytes())}
        self.report = {'format': execution.FORMAT, 'status': 'pass', 'returnCode': 0,
            'executionStatus': 'completed', 'sourceRevision': self.revision,
            'sourceIdentity': integration_evidence.source_identity(self.project, self.revision),
            'expected': expected, 'tests': rows, 'errors': issues, 'discovered': 1, 'succeeded': 1,
            'inputs': inputs, 'inputSetSha256': execution.sha(execution.canonical(inputs)),
            'logSha256': execution.sha(log), 'compiler': {'sha256': execution.PINNED_COMPILER_SHA256},
            'productionCoverage': {'contractSha256': execution.sha(execution.canonical({'probes': {}, 'systems': {}})), 'tests': {}}}
        (self.bundle / 'results.json').write_text(json.dumps(self.report))
        (self.bundle / 'execution.log').write_bytes(log)
        transport.snapshot_inputs(self.project, self.bundle / 'verification-inputs', inputs)
        self.write_archive()
        (self.bin / 'dirname').symlink_to(shutil.which('dirname'))
        # Run the real lifecycle helper but skip unrelated repository suites.
        self.executable('python3', f'#!{sys.executable}\nimport os, sys\n'
            "if sys.argv[1].endswith(('container_validation.py', 'execution_transport.py')):\n"
            '    os.execv(sys.executable, [sys.executable] + sys.argv[1:])\n')
        self.executable('git', '#!/bin/sh\nprintf "%s\\n" "' + self.revision + '"\n')
        self.env = {**os.environ, 'PATH': str(self.bin),
                    'CHECKS_DOCKER_ARGUMENTS': str(self.root / 'docker.jsonl'),
                    'CHECKS_ARCHIVE': str(self.archive)}
        self.env.pop('WARCRAFTMAP_WURST_CHECK', None)
        self.executable('docker', f'#!{sys.executable}\n' + '''import json, os, pathlib, sys
with open(os.environ['CHECKS_DOCKER_ARGUMENTS'], 'a') as output:
    output.write(json.dumps(sys.argv[1:]) + '\\n')
command = sys.argv[1]
if command == 'create':
    pathlib.Path(sys.argv[sys.argv.index('--cidfile') + 1]).write_text('fixture-container')
    print('fixture-container')
if command == 'inspect':
    print(os.environ.get('CHECKS_EXECUTION_STATUS', '0'))
if command == 'cp':
    if os.environ.get('CHECKS_COPY_HANG'):
        import time
        time.sleep(5)
    sys.stdout.buffer.write(pathlib.Path(os.environ['CHECKS_ARCHIVE']).read_bytes())
sys.exit(int(os.environ.get('CHECKS_' + command.upper() + '_STATUS', '0')))
''')

    def executable(self, name, source):
        path = self.bin / name
        path.write_text(source)
        path.chmod(0o755)

    def write_archive(self):
        with tarfile.open(self.archive, 'w') as archive:
            archive.add(self.bundle, arcname='.')

    def run_checks(self, **environment):
        self.env.update({key: str(value) for key, value in environment.items()})
        return subprocess.run(['/bin/bash', str(self.repo / 'automation/run_checks.sh')],
                              env=self.env, capture_output=True, text=True)

    def commands(self):
        return [json.loads(line) for line in (self.root / 'docker.jsonl').read_text().splitlines()]

    def assert_no_evidence(self):
        self.assertFalse((self.project / '_build/wurst-tests/results.json').exists())
        self.assertFalse(list((self.project / '_build').glob('.execution-export-*')))
        self.assertFalse(list((self.repo / '_build').glob('wurst-container-*')))

    def seed_stale(self):
        target = self.project / '_build/wurst-tests'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.bundle, target)

    def test_success_exports_complete_bundle_before_cleanup_with_read_only_mount(self):
        result = self.run_checks()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        commands = self.commands()
        self.assertEqual(['create', 'start', 'inspect', 'cp', 'rm'], [c[0] for c in commands])
        create = commands[0]
        self.assertEqual([f'{self.repo}:/source:ro'], [create[i + 1] for i, v in enumerate(create) if v == '-v'])
        self.assertIn(execution.PINNED_IMAGE, create)
        self.assertNotIn('--rm', create)
        script = create[-1]
        self.assertIn('tar -C /tmp/historical-world-rpg/age-of-sail-world -xf -', script)
        self.assertIn('tar -C /tmp/historical-world-rpg/conformance-campaign -xf -', script)
        self.assertNotIn('chown -R wurstuser:wurstuser /source', script)
        self.assertIn('execution_transport.py', script)
        report, log = transport.read_bundle(self.project / '_build/wurst-tests', self.project, self.revision)
        self.assertEqual(self.report, report)
        self.assertEqual((self.bundle / 'execution.log').read_bytes(), log)
        for name in ('results.json', 'execution.log', 'verification-inputs/wurst/Test.wurst'):
            self.assertEqual((self.bundle / name).read_bytes(), (self.project / '_build/wurst-tests' / name).read_bytes())

    def test_compiler_and_framework_exit_codes_survive_cleanup(self):
        for status in (37, 41):
            with self.subTest(status=status):
                self.seed_stale()
                result = self.run_checks(CHECKS_EXECUTION_STATUS=status, CHECKS_RM_STATUS=19)
                self.assertEqual(status, result.returncode, result.stdout + result.stderr)
                self.assertEqual('rm', self.commands()[-1][0])
                self.assertNotIn('cp', [c[0] for c in self.commands()])
                self.assert_no_evidence()
                shutil.rmtree(self.project / '_build/wurst-tests')

    def test_partial_export_does_not_reuse_old_evidence(self):
        self.seed_stale()
        (self.bundle / 'execution.log').unlink()
        self.write_archive()
        result = self.run_checks()
        self.assertNotEqual(0, result.returncode)
        self.assertEqual('rm', self.commands()[-1][0])
        self.assert_no_evidence()

    def test_failed_copy_and_cleanup_fail_closed(self):
        for command in ('CP', 'RM', 'START', 'CREATE'):
            with self.subTest(command=command):
                self.seed_stale()
                result = self.run_checks(**{f'CHECKS_{command}_STATUS': 23})
                self.assertNotEqual(0, result.returncode)
                self.assertEqual('rm', self.commands()[-1][0])
                self.assert_no_evidence()
                self.env.pop(f'CHECKS_{command}_STATUS')
                shutil.rmtree(self.project / '_build/wurst-tests')

    def test_stale_revision_hash_and_transcript_tampering_rejected(self):
        original = (self.bundle / 'results.json').read_bytes()
        for field, value in (('sourceRevision', 'b' * 40), ('inputSetSha256', '0' * 64),
                             ('logSha256', '0' * 64), ('executionStatus', 'focused')):
            with self.subTest(field=field):
                report = {**self.report, field: value}
                (self.bundle / 'results.json').write_text(json.dumps(report))
                self.write_archive()
                result = self.run_checks()
                self.assertNotEqual(0, result.returncode)
                self.assert_no_evidence()
        (self.bundle / 'results.json').write_bytes(original)
        (self.bundle / 'verification-inputs/wurst/Test.wurst').write_text('tampered')
        self.write_archive()
        self.assertNotEqual(0, self.run_checks().returncode)
        self.assert_no_evidence()

    def test_atomic_publication_failure_leaves_no_stale_evidence(self):
        self.seed_stale()
        with mock.patch.dict(os.environ, self.env), \
             mock.patch.object(container_validation.os, 'replace', side_effect=OSError('publication failed')):
            self.assertEqual(1, container_validation.validate(self.repo, self.revision))
        self.assertEqual('rm', self.commands()[-1][0])
        self.assert_no_evidence()

    def test_copy_timeout_and_truncated_archive_cleanup_without_stale_reuse(self):
        self.seed_stale()
        with mock.patch.dict(os.environ, {**self.env, 'CHECKS_COPY_HANG': '1'}), \
             mock.patch.object(container_validation, 'EXPORT_TIMEOUT_SECONDS', 0.1):
            self.assertEqual(1, container_validation.validate(self.repo, self.revision))
        self.assertEqual('rm', self.commands()[-1][0])
        self.assert_no_evidence()
        self.archive.write_bytes(b'truncated tar')
        self.assertNotEqual(0, self.run_checks().returncode)
        self.assertEqual('rm', self.commands()[-1][0])
        self.assert_no_evidence()

    def test_aggregate_and_stream_limits_are_enforced(self):
        with self.archive.open('rb') as stream, \
             mock.patch.object(transport, 'MAX_BYTES', 1), self.assertRaises(ValueError):
            transport.unpack(stream, self.root / 'aggregate')
        with mock.patch.object(transport, 'MAX_ARCHIVE_BYTES', 1), self.assertRaises(ValueError):
            transport.LimitedStream(io.BytesIO(b'oversized')).read(100)

    def test_archive_limits_traversal_links_and_unexpected_files(self):
        for name, kind, size in (('../escape', tarfile.REGTYPE, 0), ('execution.log', tarfile.SYMTYPE, 0),
                                  ('compile/map.w3x', tarfile.REGTYPE, 0),
                                  ('execution.log', tarfile.REGTYPE, transport.MAX_FILE_BYTES + 1)):
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode='w') as archive:
                member = tarfile.TarInfo(name)
                member.type, member.size = kind, size
                archive.addfile(member)
            stream.seek(0)
            with self.subTest(name=name, kind=kind), self.assertRaises(ValueError):
                transport.unpack(stream, self.root / 'unpack')

    def container_packaging_result(self, status, transcript, *, fixture_status=0, fixture_logs=None):
        script = (REPOSITORY / 'automation/wurst_container.sh').read_text().split('validation_status=0', 1)[1]
        # Exercise packaging/diagnostics without installing dependencies or staging.
        script = script.split('if [ "$validation_status" -eq 0 ]; then\n  python3', 1)[0] + 'exit "$validation_status"\n'
        category = self.root / 'container'
        for relative, contents in {'age-of-sail-world/_build/wurst-tests/execution.log': transcript,
                                    **(fixture_logs or {})}.items():
            if contents is not None:
                target = category / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(contents)
        self.executable('su', f'#!{sys.executable}\nimport sys\n'
                        f"sys.exit({fixture_status} if 'validate_framework_fixture.py' in sys.argv[-1] else {status})\n")
        if not (self.bin / 'cat').exists():
            (self.bin / 'cat').symlink_to(shutil.which('cat'))
        script = 'validation_status=0' + script.replace('/tmp/historical-world-rpg', str(category))
        return subprocess.run(['/bin/sh', '-eu', '-c', script], env=self.env, capture_output=True, text=True)

    def test_container_failure_emits_execution_log_and_preserves_original_status(self):
        transcript = 'Running tests\nFAILED - TIMEOUT\njava.lang.OutOfMemoryError\n'
        result = self.container_packaging_result(37, transcript)
        self.assertEqual(37, result.returncode)
        self.assertEqual(transcript, result.stdout)

    def test_fixture_and_mutation_failure_emit_diagnostics(self):
        for relative in ('_build/wurst-tests/execution.log', '_build/mutation/campaign/_build/wurst-tests/execution.log'):
            with self.subTest(relative=relative):
                transcript = f'{relative}: FAILED - TIMEOUT\n'
                result = self.container_packaging_result(0, None, fixture_status=41,
                    fixture_logs={'conformance-campaign/' + relative: transcript})
                self.assertEqual(41, result.returncode)
                self.assertIn(transcript, result.stdout)

    def test_absent_execution_tools_prevent_default_validation_success(self):
        (self.bin / 'docker').unlink()
        result = self.run_checks()
        self.assertEqual(1, result.returncode)
        self.assertIn('requires grill or Docker', result.stderr)


if __name__ == '__main__':
    unittest.main()

"""No compiler subprocesses: focused replay failure contract tests."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '_shared/tooling'))
import focused_wurst_replay as replay


class FocusedReplayTests(unittest.TestCase):
    def run_case(self, failure=None):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            project = base / 'repo/project'
            project.mkdir(parents=True)
            compiler = base / 'compiler.jar'
            compiler.write_bytes(b'compiler')
            launcher = base / 'grill'
            launcher.write_text('launcher')
            root = base / 'assembly'
            (root / 'wurst').mkdir(parents=True)
            (root / 'wurst/A.wurst').write_text('@test function one()\n')
            (root / 'wurst/B.wurst').write_text('@test function two()\n')
            (root / '_build/dependencies').mkdir(parents=True)
            dep = root / '_build/dependencies/stdlib.wurst'
            dep.write_text('stdlib')
            (root / 'wurst.build').write_text('build')
            calls = []

            def run(command, **kwargs):
                calls.append(command)
                package = command[-1]
                if failure == 'timeout' and package == 'A':
                    kwargs['stdout'].write('partial transcript')
                    raise subprocess.TimeoutExpired(command, 1)
                if package == 'typecheck':
                    text = 'Typecheck succeeded\n'
                    if failure == 'typecheck_drift':
                        dep.write_text('changed')
                else:
                    fn = 'one' if package == 'A' else 'two'
                    text = f'Running tests\nRunning wurst/{package}.wurst:1 - {fn}..\n OK!\nTests succeeded: 1/1\nFinished running tests\n'
                    if failure == 'malformed' and package == 'A':
                        text = 'not a test result'
                    if failure == 'dependency_drift' and package == 'A':
                        dep.write_text('changed')
                kwargs['stdout'].write(text)
                return subprocess.CompletedProcess(command, 1 if (failure == 'suite_exit' and package == 'A') or (failure == 'typecheck_exit' and package == 'typecheck') else 0)

            def clean(*args):
                if failure == 'revision':
                    raise ValueError('wrong revision')

            identity = {'sourceTreeSha256': 'source'}
            def source(*args):
                return {'sourceTreeSha256': 'changed'} if failure == 'source_drift' and calls else identity

            packages = ['A', 'B'] if failure != 'missing' else ['Missing']
            with patch.object(replay.subprocess, 'check_output', return_value=str(project.parent)), \
                 patch.object(replay, 'require_local_tooling'), \
                 patch.object(replay, 'clean_revision', side_effect=clean), \
                 patch.object(replay, 'source_identity', side_effect=source), \
                 patch.object(replay, 'assemble', return_value=root), \
                 patch.object(replay, 'PINNED_COMPILER_SHA256', replay.sha(b'compiler')), \
                 patch.object(replay, 'compiler_identity', return_value={'sha256': 'wrong' if failure == 'compiler' else replay.sha(b'compiler')}), \
                 patch.object(replay.subprocess, 'run', side_effect=run):
                code = replay.replay(project, base / 'out', 'a' * 40, packages, launcher, compiler, base, timeout=1)
            report = json.loads((base / 'out/results.json').read_text())
            if failure:
                self.assertEqual(code, 1)
                self.assertFalse(report['completed'])
                self.assertTrue(report['errors'])
                self.assertFalse(any(command[-1] == 'B' for command in calls))
            else:
                self.assertEqual(code, 0, report)
                self.assertTrue(report['completed'])
                self.assertEqual(len(report['suites']), 3)
            if failure == 'timeout':
                self.assertIn('partial transcript', (base / 'out/A.log').read_text())

    def test_all_pass(self):
        self.run_case()

    def test_fail_closed_cases(self):
        for failure in ['revision', 'missing', 'suite_exit', 'malformed', 'timeout',
                        'typecheck_drift', 'dependency_drift', 'source_drift', 'typecheck_exit', 'compiler']:
            with self.subTest(failure=failure):
                self.run_case(failure)

    def test_clean_revision_checks_actual_head_and_untracked_files(self):
        for head, status in [('b' * 40, ''), ('a' * 40, '?? unknown')]:
            with patch.object(replay.subprocess, 'check_output', side_effect=[head, status]):
                with self.assertRaises(ValueError):
                    replay.clean_revision(Path('.'), 'a' * 40)

    def test_different_checkout_rejected(self):
        tooling = Path(replay.__file__).resolve().parent
        replay.require_local_tooling(tooling.parent.parent / "age-of-sail-world")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "runner checkout tooling"):
                replay.require_local_tooling(Path(directory) / "other/age-of-sail-world")

    def test_inventory_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'link').symlink_to('/tmp')
            with self.assertRaises(ValueError):
                replay.inventory(root)


if __name__ == '__main__':
    unittest.main()

"""Focused replay contracts; no real compiler subprocesses."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import os
import select
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

            def assemble(*args):
                if failure == 'assembly_compiler_drift':
                    compiler.write_bytes(b'replaced compiler')
                return root

            packages = ['A', 'B'] if failure != 'missing' else ['Missing']
            with patch.object(replay.subprocess, 'check_output', return_value=str(project.parent)), \
                 patch.object(replay, 'require_local_tooling'), \
                 patch.object(replay, 'clean_revision', side_effect=clean), \
                 patch.object(replay, 'source_identity', side_effect=source), \
                 patch.object(replay, 'assemble', side_effect=assemble), \
                 patch.object(replay, 'PINNED_COMPILER_SHA256', replay.sha(b'compiler')), \
                 patch.object(replay, 'compiler_identity', return_value={'sha256': 'wrong' if failure == 'compiler' else replay.sha(b'compiler')}), \
                 patch.object(replay, 'run_launcher', side_effect=run):
                code = replay.replay(project, base / 'out', 'a' * 40, packages, launcher, compiler, base, timeout=1)
            report = json.loads((base / 'out/results.json').read_text())
            if failure:
                self.assertEqual(code, 1)
                self.assertFalse(report['completed'])
                self.assertTrue(report['errors'])
                expected = ([] if failure in {'revision', 'missing', 'assembly_compiler_drift'}
                            else ['typecheck'] if failure in {'typecheck_exit', 'typecheck_drift', 'source_drift', 'compiler'}
                            else ['typecheck', 'A'])
                self.assertEqual([command[-1] for command in calls], expected)
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
                        'assembly_compiler_drift', 'typecheck_drift', 'dependency_drift', 'source_drift', 'typecheck_exit', 'compiler']:
            with self.subTest(failure=failure):
                self.run_case(failure)

    @unittest.skipUnless(replay.os.name == 'posix', 'POSIX process groups required')
    def test_timeout_and_cancel_kill_owned_group_and_reap_launcher(self):
        from unittest.mock import MagicMock
        for error in (subprocess.TimeoutExpired(['launcher'], 1), KeyboardInterrupt()):
            with self.subTest(error=type(error).__name__):
                process = MagicMock()
                process.pid = 314159
                process.wait.side_effect = [error, -9]
                with patch.object(replay.subprocess, 'Popen') as popen, patch.object(replay.os, 'killpg') as kill:
                    popen.return_value.__enter__.return_value = process
                    with self.assertRaises(type(error)) as raised:
                        replay.run_launcher(['launcher'], cwd=Path('.'), env={}, stdout=None, timeout=1)
                    self.assertIs(raised.exception, error)
                    self.assertTrue(popen.call_args.kwargs['start_new_session'])
                    kill.assert_called_once_with(process.pid, replay.signal.SIGKILL)
                    self.assertEqual(process.wait.call_count, 2)

    @unittest.skipUnless(replay.os.name == 'posix', 'POSIX process groups required')
    def test_timeout_closes_ready_descendants_inherited_pipe(self):
        # The descendant reports readiness and holds stdout open until killed.
        # EOF, not a guessed sleep/absent marker, proves its descriptor closed.
        # Deadlines only bound a broken test; timeout is injected after readiness.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            read_fd, write_fd = os.pipe()
            real_popen = subprocess.Popen
            launched = []
            child = "import os, signal; os.write(1, b'R'); signal.pause()"
            parent = f"import subprocess, sys; p=subprocess.Popen([sys.executable, '-c', {child!r}]); p.wait()"
            def start(*args, **kwargs):
                process = real_popen(*args, **kwargs)
                launched.append(process)
                real_wait = process.wait
                def wait(timeout=None):
                    if timeout is not None:
                        self.assertTrue(select.select([read_fd], [], [], 10)[0], 'descendant never became ready')
                        self.assertEqual(b'R', os.read(read_fd, 1))
                        raise subprocess.TimeoutExpired(args[0], timeout)
                    return real_wait(timeout=10)
                process.wait = wait
                return process
            try:
                with os.fdopen(write_fd, 'wb') as output:
                    with patch.object(replay.subprocess, 'Popen', side_effect=start):
                        with self.assertRaises(subprocess.TimeoutExpired):
                            replay.run_launcher([sys.executable, '-c', parent], cwd=root,
                                                env=os.environ.copy(), stdout=output, timeout=1)
                self.assertTrue(select.select([read_fd], [], [], 10)[0], 'descendant retained output after cleanup')
                self.assertEqual(b'', os.read(read_fd, 1))
            finally:
                # Even a deliberately broken cleanup implementation must not
                # leave this test's own child process behind.
                for process in launched:
                    try:
                        os.killpg(process.pid, replay.signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    real_popen.wait(process, timeout=10)
                os.close(read_fd)

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

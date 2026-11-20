"""Execute the rendered CI shell up to the real build command with safe stubs."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest

REPOSITORY = Path(__file__).resolve().parents[4]
WORKFLOWS = (
    ("wurst-typecheck.yml", "Execute complete suite, typecheck, and package fixture and content mutation"),
    ("map-build.yml", "Execute complete Wurst suite and package with pinned compiler"),
)


def rendered_shell(path, step_name):
    source = (REPOSITORY / ".github/workflows" / path).read_text()
    start = re.search(r"(?m)^      - name: " + re.escape(step_name) + r"\s*$", source)
    if not start:
        raise AssertionError("missing workflow step")
    rest = source[start.end():]
    end = re.search(r"(?m)^      - (?:name:|uses:)", rest)
    step = rest[:end.start()] if end else rest
    if "        run: |\n" not in step:
        raise AssertionError("missing rendered shell block")
    return textwrap.dedent(step.split("        run: |\n", 1)[1])


class WorkflowDockerShellTests(unittest.TestCase):
    def test_optional_git_outcomes_reach_build_and_preserve_failure(self):
        for filename, step in WORKFLOWS:
            for git_fails, python_fails, expected_exit in ((False, False, 42), (True, False, 42),
                                                            (False, True, 74)):
                with self.subTest(filename=filename, git_fails=git_fails, python_fails=python_fails), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    bin_dir = root / "bin"
                    bin_dir.mkdir()
                    trace = root / "trace"
                    args_file = root / "docker-args.json"
                    docker = bin_dir / "docker"
                    docker.write_text("#!" + sys.executable + "\n" + textwrap.dedent("""
                        import json, os, pathlib, subprocess, sys
                        args = sys.argv[1:]
                        pathlib.Path(os.environ['DOCKER_ARGS']).write_text(json.dumps(args))
                        if args[-3:-1] != ['/bin/sh', '-lc']:
                            sys.exit(78)
                        lines = []
                        for line in args[-1].splitlines():
                            lines.append(line)
                            if line.strip().startswith('su -s '):
                                break
                        else:
                            sys.exit(79)
                        status = 'candidate_status' if 'candidate_status=0' in args[-1] else 'validation_status'
                        lines.append('exit "$' + status + '"')
                        sys.exit(subprocess.run(['/bin/sh', '-c', '\\n'.join(lines)], env=os.environ).returncode)
                    """))
                    for name, body in {
                        "apt-get": "printf 'apt:%s\\n' \"$*\" >> \"$TRACE\"; if [ \"$FAIL_PYTHON\" = 1 ] && [ \"$*\" = 'install -y --no-install-recommends python3' ]; then exit 74; fi; if [ \"$FAIL_GIT\" = 1 ] && [ \"$*\" = 'install -y --no-install-recommends git' ]; then exit 75; fi",
                        "cp": "exit 0",
                        "chown": "exit 0",
                        "su": "printf 'build reached\\n' >> \"$TRACE\"; exit 42",
                    }.items():
                        file = bin_dir / name
                        file.write_text("#!/bin/sh\n" + body + "\n")
                        file.chmod(0o755)
                    docker.chmod(0o755)
                    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
                               TRACE=str(trace), DOCKER_ARGS=str(args_file), FAIL_GIT="1" if git_fails else "0",
                               FAIL_PYTHON="1" if python_fails else "0",
                               RUNNER_TEMP=str(root), WURST_RUN_IMAGE="stub-image", GITHUB_SHA="a" * 40,
                               SOURCE_REVISION="a" * 40,
                               MAP_PROJECT="maps/historical-world-rpg/age-of-sail-world",
                               RELEASE_ARTIFACT="unused.zip")
                    result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", rendered_shell(filename, step)],
                                            cwd=REPOSITORY, env=env, capture_output=True, text=True)
                    self.assertEqual(expected_exit, result.returncode, result.stderr)
                    self.assertEqual(0 if python_fails else 1, trace.read_text().count("build reached"))
                    self.assertIn("apt:install -y --no-install-recommends python3", trace.read_text())
                    if not python_fails:
                        self.assertIn("apt:install -y --no-install-recommends git", trace.read_text())
                    args = json.loads(args_file.read_text())
                    self.assertEqual(args[-3:-1], ["/bin/sh", "-lc"])
                    self.assertIn("su -s /bin/sh wurstuser", args[-1])
                    self.assertNotIn("command not found", result.stderr)


if __name__ == "__main__":
    unittest.main()

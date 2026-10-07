"""Required checks must propagate compiler failures without writable source mounts."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


CHECKS = Path(__file__).resolve().parents[1] / "run_checks.sh"
REPOSITORY = CHECKS.parent.parent


class RequiredWurstChecksTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        # Isolate command discovery from host Grill/Docker installations. The
        # Python suites are assumed successful here; their real runs are separate.
        (self.bin / "dirname").symlink_to(shutil.which("dirname"))
        self.executable("python3", "#!/bin/sh\nexit 0\n")
        self.executable("git", "#!/bin/sh\nprintf '%s\\n' '" + "a" * 40 + "'\n")
        self.env = {**os.environ, "PATH": str(self.bin),
                    "CHECKS_DOCKER_ARGUMENTS": str(self.root / "docker.json")}
        self.env.pop("WARCRAFTMAP_WURST_CHECK", None)

    def executable(self, name, source):
        path = self.bin / name
        path.write_text(source)
        path.chmod(0o755)

    def run_checks(self, docker_status=None):
        if docker_status is not None:
            self.executable("docker", f"#!{sys.executable}\n"
                "import json, os, pathlib, sys\n"
                "pathlib.Path(os.environ['CHECKS_DOCKER_ARGUMENTS']).write_text(json.dumps(sys.argv[1:]))\n"
                f"sys.exit({docker_status})\n")
        return subprocess.run(["/bin/bash", str(CHECKS)], cwd=self.root,
                              env=self.env, capture_output=True, text=True)

    def test_default_validation_uses_pinned_compiler_user_in_private_copy(self):
        result = self.run_checks(0)
        self.assertEqual(0, result.returncode, result.stderr)
        arguments = json.loads((self.root / "docker.json").read_text())
        mounts = [arguments[i + 1] for i, value in enumerate(arguments) if value == "-v"]
        self.assertEqual([f"{REPOSITORY}:/source:ro"], mounts)
        self.assertIn("frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a", arguments)
        script = arguments[-1]
        self.assertIn("tar -C /tmp/historical-world-rpg/age-of-sail-world -xf -", script)
        self.assertIn("tar -C /tmp/historical-world-rpg/conformance-campaign -xf -", script)
        self.assertIn("chown -R wurstuser:wurstuser /tmp/historical-world-rpg", script)
        self.assertIn('su -s /bin/sh wurstuser -c "cd /tmp/historical-world-rpg/age-of-sail-world && PATH=/home/wurstuser/.wurst:/usr/local/bin:/usr/bin:/bin ./tooling/package_release.sh"', script)
        self.assertIn("python3 _shared/tooling/validate_framework_fixture.py conformance-campaign", script)
        self.assertNotIn("grill install wurstscript", script)
        self.assertNotIn("chown -R wurstuser:wurstuser /source", script)

    def test_compiler_failure_propagates_after_successful_python_checks(self):
        result = self.run_checks(37)
        self.assertEqual(37, result.returncode, result.stdout + result.stderr)

    def container_packaging_result(self, status, transcript, *, fixture_status=None, fixture_logs=None):
        self.run_checks(0)
        arguments = json.loads((self.root / "docker.json").read_text())
        # Execute the real packaging/diagnostic shell block with a recording su
        # boundary; dependency installation and source copying are separate.
        script = arguments[-1].split("validation_status=0", 1)[1]
        container_category = self.root / "container"
        container_project = container_category / "age-of-sail-world"
        log = container_project / "_build/wurst-tests/execution.log"
        log.parent.mkdir(parents=True)
        if transcript is not None:
            log.write_text(transcript)
        for relative, contents in (fixture_logs or {}).items():
            fixture_log = container_category / "conformance-campaign" / relative
            fixture_log.parent.mkdir(parents=True, exist_ok=True)
            fixture_log.write_text(contents)
        if fixture_status is None:
            fixture_status = status
        self.executable("su", f"#!{sys.executable}\nimport sys\n"
                        f"sys.exit({fixture_status} if 'validate_framework_fixture.py' in sys.argv[-1] else {status})\n")
        (self.bin / "cat").symlink_to(shutil.which("cat"))
        script = "validation_status=0" + script.replace(
            "/tmp/historical-world-rpg", str(container_category))
        return subprocess.run(["/bin/sh", "-eu", "-c", script], env=self.env,
                              capture_output=True, text=True)

    def test_container_failure_emits_execution_log_before_removal(self):
        transcript = "Running tests\nFAILED - TIMEOUT\njava.lang.OutOfMemoryError\n"
        result = self.container_packaging_result(37, transcript)
        self.assertEqual(37, result.returncode, result.stdout + result.stderr)
        self.assertEqual(transcript, result.stdout)

    def test_container_failure_without_execution_log_retains_original_status(self):
        result = self.container_packaging_result(29, None)
        self.assertEqual(29, result.returncode, result.stdout + result.stderr)
        self.assertEqual("", result.stdout + result.stderr)

    def assert_fixture_failure_diagnostic(self, relative):
        transcript = f"{relative}: FAILED - TIMEOUT\n"
        result = self.container_packaging_result(
            0, None, fixture_status=41, fixture_logs={relative: transcript})
        self.assertEqual(41, result.returncode, result.stdout + result.stderr)
        self.assertEqual(transcript, result.stdout)

    def test_fixture_failure_propagates_and_preserves_execution_log(self):
        self.assert_fixture_failure_diagnostic("_build/wurst-tests/execution.log")

    def test_mutation_failure_propagates_and_preserves_execution_log(self):
        self.assert_fixture_failure_diagnostic("_build/mutation/campaign/_build/wurst-tests/execution.log")

    def test_container_success_does_not_replay_execution_log(self):
        result = self.container_packaging_result(0, "Tests succeeded: 228/228\n")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual("", result.stdout + result.stderr)

    def test_absent_execution_tools_prevent_default_validation_success(self):
        result = self.run_checks()
        self.assertEqual(1, result.returncode)
        self.assertIn("requires grill or Docker", result.stderr)


if __name__ == "__main__":
    unittest.main()

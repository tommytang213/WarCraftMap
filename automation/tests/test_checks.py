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
        self.assertIn("chown -R wurstuser:wurstuser /tmp/historical-world-rpg", script)
        self.assertIn('su -s /bin/sh wurstuser -c "cd /tmp/historical-world-rpg/age-of-sail-world && PATH=/home/wurstuser/.wurst:/usr/local/bin:/usr/bin:/bin ./tooling/package_release.sh"', script)
        self.assertNotIn("grill install wurstscript", script)
        self.assertNotIn("chown -R wurstuser:wurstuser /source", script)

    def test_compiler_failure_propagates_after_successful_python_checks(self):
        result = self.run_checks(37)
        self.assertEqual(37, result.returncode, result.stdout + result.stderr)

    def test_absent_execution_tools_prevent_default_validation_success(self):
        result = self.run_checks()
        self.assertEqual(1, result.returncode)
        self.assertIn("requires grill or Docker", result.stderr)


if __name__ == "__main__":
    unittest.main()

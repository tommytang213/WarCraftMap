"""Exercise registry failures without pulling images or starting containers."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "automation/prepare_wurst_image.sh"
PIN = "frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a"
MIRROR = "mirror.gcr.io/" + PIN
WORKFLOWS = ("wurst-typecheck.yml", "map-build.yml", "age-of-sail-launch-smoke.yml")


class PrepareWurstImageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.state = self.root / "state.json"
        self.calls = self.root / "calls.jsonl"
        docker = self.root / "docker"
        docker.write_text(f"#!{sys.executable}\n" + '''
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
state_path = Path(os.environ["TEST_IMAGE_STATE"])
state = json.loads(state_path.read_text())
with open(os.environ["TEST_IMAGE_CALLS"], "a") as stream:
    stream.write(json.dumps(args) + "\\n")
if args[:2] == ["image", "inspect"]:
    sys.exit(0 if args[2] in state["cached"] else 1)
if args[0] == "pull":
    image = args[1]
    if image not in state["available"]:
        print("registry unavailable / unauthenticated pull rate limit", file=sys.stderr)
        sys.exit(125)
    if image not in state["missing_after_pull"]:
        state["cached"].append(image)
    state_path.write_text(json.dumps(state))
    print("Pulled " + image)
    sys.exit(0)
if args[0] == "run":
    sys.exit(state["run_status"])
raise SystemExit("unexpected Docker operation: " + repr(args))
''')
        docker.chmod(0o755)
        (self.root / "bash").symlink_to(shutil.which("bash"))
        self.env = {**os.environ, "PATH": str(self.root),
                    "TEST_IMAGE_STATE": str(self.state), "TEST_IMAGE_CALLS": str(self.calls)}

    def configure(self, *, cached=(), available=(), missing_after_pull=(), run_status=0):
        self.state.write_text(json.dumps({"cached": list(cached), "available": list(available),
                                         "missing_after_pull": list(missing_after_pull),
                                         "run_status": run_status}))

    def recorded_calls(self):
        return [json.loads(line) for line in self.calls.read_text().splitlines()] if self.calls.exists() else []

    def prepare(self, reference=PIN):
        return subprocess.run(["/bin/bash", str(SCRIPT), reference], env=self.env,
                              capture_output=True, text=True)

    def test_cached_immutable_images_need_no_registry(self):
        for reference in (PIN, MIRROR):
            with self.subTest(reference=reference):
                self.configure(cached=[reference])
                result = self.prepare()
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(reference + "\n", result.stdout)
        self.assertTrue(all(call[:2] == ["image", "inspect"] for call in self.recorded_calls()))

    def test_hub_rate_limit_does_not_block_available_mirror_of_same_digest(self):
        self.configure(available=[MIRROR])
        result = self.prepare()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(MIRROR + "\n", result.stdout)
        self.assertIn("Pulled " + MIRROR, result.stderr)
        self.assertEqual([["pull", MIRROR]], [call for call in self.recorded_calls() if call[0] == "pull"])

    def test_mirror_cache_miss_falls_back_to_exact_canonical_digest(self):
        self.configure(available=[PIN])
        result = self.prepare()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(PIN + "\n", result.stdout)
        self.assertEqual([["pull", MIRROR], ["pull", PIN]],
                         [call for call in self.recorded_calls() if call[0] == "pull"])

    def test_both_registries_unavailable_fail_without_a_selected_image(self):
        self.configure()
        result = self.prepare()
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("validation has not run", result.stderr)
        self.assertEqual(2, sum(call[0] == "pull" for call in self.recorded_calls()))

    def test_successful_pull_must_leave_the_exact_reference_available(self):
        self.configure(available=[MIRROR], missing_after_pull=[MIRROR])
        result = self.prepare()
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("", result.stdout)

    def test_mutable_wrong_repository_and_malformed_inputs_never_reach_docker(self):
        for reference in ("frotty/wurstscript:latest", PIN[:-1], PIN + "\n", "other/" + PIN, ""):
            with self.subTest(reference=reference):
                result = self.prepare(reference)
                self.assertEqual(2, result.returncode)
                self.assertEqual("", result.stdout)
        self.assertEqual([], self.recorded_calls())

    def test_workflows_use_selected_image_and_keep_validation_failures_blocking(self):
        for filename in WORKFLOWS:
            source = (ROOT / ".github/workflows" / filename).read_text()
            # Execute the actual preparation and docker invocation at a recording
            # boundary. The private compiler program is passed intact, never run.
            preparation = re.search(
                r"      - name: Prepare pinned Wurst image\n        run: \|\n((?:          .*\n)+)", source)
            self.assertIsNotNone(preparation, filename)
            command = re.search(r"          docker run --rm \\\n.*?^            '\n", source, re.M | re.S)
            self.assertIsNotNone(command, filename)
            script = "\n".join(line[10:] for line in preparation[1].splitlines())
            script += '\nsource "$GITHUB_ENV"\n'
            script += "\n".join(line[10:] for line in command[0].splitlines())
            for available, run_status, expected in (([MIRROR], 0, 0), ([PIN], 0, 0),
                                                    ([MIRROR], 37, 37), ([], 0, 1)):
                with self.subTest(workflow=filename, available=available, run_status=run_status):
                    self.configure(available=available, run_status=run_status)
                    self.calls.unlink(missing_ok=True)
                    env_file = self.root / "github.env"
                    env_file.write_text("")
                    result = subprocess.run(["/bin/bash", "-euo", "pipefail", "-c", script],
                                            cwd=ROOT, env=self.env | {"WURST_IMAGE": PIN,
                                                "GITHUB_ENV": str(env_file), "GITHUB_SHA": "a" * 40,
                                                "artifact_dir": str(self.root / "artifacts")},
                                            capture_output=True, text=True)
                    self.assertEqual(expected, result.returncode, result.stdout + result.stderr)
                    runs = [call for call in self.recorded_calls() if call[0] == "run"]
                    if not available:
                        self.assertEqual([], runs)
                        self.assertEqual("", env_file.read_text())
                        continue
                    self.assertEqual(1, len(runs))
                    self.assertIn(available[0], runs[0])
                    self.assertIn("--pull=never", runs[0])
                    self.assertIn("WURST_IMAGE", runs[0])
                    self.assertIn(f"{ROOT}:/source:ro", runs[0])

    def test_required_workflows_cover_helper_changes(self):
        for filename in WORKFLOWS[:2]:
            source = (ROOT / ".github/workflows" / filename).read_text()
            header = source.split("\njobs:\n", 1)[0]
            self.assertEqual(2, header.count('"automation/prepare_wurst_image.sh"'), filename)


if __name__ == "__main__":
    unittest.main()

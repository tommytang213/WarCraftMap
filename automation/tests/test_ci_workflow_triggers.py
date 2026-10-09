"""Keep CI event isolation safe when editing the heavy map workflows.

These are intentionally small, dependency-free source contract checks.
They do not replace compiling the campaign or testing Warcraft III.
"""
from pathlib import Path
import re
import unittest


REPOSITORY = Path(__file__).resolve().parents[2]
WORKFLOWS = (
    "map-build.yml",
    "wurst-typecheck.yml",
    "world-contracts.yml",
    "automation-tests.yml",
)


class CiWorkflowTriggerTests(unittest.TestCase):
    def test_all_required_pr_checks_remain_enabled_and_push_only_on_main(self):
        for filename in WORKFLOWS:
            with self.subTest(workflow=filename):
                source = (REPOSITORY / ".github/workflows" / filename).read_text(encoding="utf-8")
                header = source.split("\njobs:\n", 1)[0]
                self.assertRegex(header, r"(?m)^on:\n  push:\n    branches: \[main\]\n    paths:")
                self.assertRegex(header, r"(?m)^  pull_request:\n    paths:")
                self.assertRegex(header, r"(?m)^  workflow_dispatch:\s*$")
                # Each event keeps the path filters used by the original workflow.
                self.assertIn(f'.github/workflows/{filename}', header)

    def test_only_obsolete_pr_runs_may_be_cancelled(self):
        for filename in WORKFLOWS:
            with self.subTest(workflow=filename):
                source = (REPOSITORY / ".github/workflows" / filename).read_text(encoding="utf-8")
                header = source.split("\njobs:\n", 1)[0]
                self.assertRegex(header, r"(?m)^concurrency:\n")
                self.assertIn("group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}", header)
                self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", header)
                self.assertNotRegex(header, r"(?m)^  cancel-in-progress:\s*true\s*$")

    def test_manual_launch_smoke_keeps_separate_policy(self):
        launch = REPOSITORY / ".github/workflows/age-of-sail-launch-smoke.yml"
        source = launch.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", source)
        self.assertIn("if: github.ref == 'refs/heads/main'", source)
        self.assertIn("NOT-RELEASE", source)


if __name__ == "__main__":
    unittest.main()

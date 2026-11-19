import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "verify_manual_head_checkout.sh"
WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/map-build.yml"


class ManualHeadCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.checkout = Path(self.temporary.name)
        self.git("init", "-q")
        self.git("config", "user.name", "CI Test")
        self.git("config", "user.email", "ci-test@example.invalid")
        (self.checkout / "source.txt").write_text("first\n")
        self.git("add", "source.txt")
        self.git("commit", "-qm", "first")
        self.head = self.git("rev-parse", "HEAD").stdout.strip()
        self.env = {
            **os.environ,
            "EXPECTED_HEAD_SHA": self.head,
            "GITHUB_SHA": self.head,
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REPOSITORY": "tommytang213/WarCraftMap",
            "GITHUB_REF": "refs/heads/fix/dot-wc3-continuation-20261118",
        }

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.checkout, text=True,
                              capture_output=True, check=True)

    def check(self, **changes):
        return subprocess.run(["bash", str(SCRIPT)], cwd=self.checkout,
                              env={**self.env, **changes}, text=True, capture_output=True)

    def test_accepts_clean_exact_repository_branch_head(self):
        result = self.check()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(self.head, result.stdout)

    def test_rejects_malformed_or_shell_syntax_input_as_data(self):
        marker = self.checkout / "injected"
        for value in ("", "a" * 39, "A" * 40,
                      self.head + f"$(touch {marker})"):
            with self.subTest(value=value):
                self.assertNotEqual(0, self.check(EXPECTED_HEAD_SHA=value).returncode)
        self.assertFalse(marker.exists())

    def test_rejects_untrusted_event_repository_or_ref(self):
        for field, value in (
            ("GITHUB_EVENT_NAME", "pull_request"),
            ("GITHUB_REPOSITORY", "someone/WarCraftMap"),
            ("GITHUB_REF", "refs/pull/601/merge"),
            ("GITHUB_REF", "refs/heads/main"),
        ):
            with self.subTest(field=field, value=value):
                self.assertNotEqual(0, self.check(**{field: value}).returncode)

    def test_rejects_event_sha_or_checkout_mismatch(self):
        self.assertNotEqual(0, self.check(GITHUB_SHA="0" * 40).returncode)
        self.assertNotEqual(0, self.check(EXPECTED_HEAD_SHA="0" * 40,
                                          GITHUB_SHA="0" * 40).returncode)

    def test_rejects_dirty_tracked_or_untracked_checkout(self):
        (self.checkout / "source.txt").write_text("changed\n")
        self.assertNotEqual(0, self.check().returncode)
        self.git("checkout", "--", "source.txt")
        (self.checkout / "extra.txt").write_text("untracked\n")
        self.assertNotEqual(0, self.check().returncode)

    def test_rejects_failed_git_status_read(self):
        actual_git = shutil.which("git")
        with tempfile.TemporaryDirectory() as temporary:
            wrapper = Path(temporary) / "git"
            wrapper.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = status ]; then exit 42; fi\n"
                f'exec "{actual_git}" "$@"\n'
            )
            wrapper.chmod(0o755)
            result = self.check(PATH=temporary + os.pathsep + self.env["PATH"])
        self.assertNotEqual(0, result.returncode)
        self.assertIn("Cannot inspect manual validation checkout status", result.stderr)

    def test_workflow_scopes_preflight_and_preserves_upload_guards(self):
        workflow = WORKFLOW.read_text()
        self.assertIn("required: false", workflow)
        self.assertIn(
            "if: github.event_name == 'workflow_dispatch' && "
            "github.ref == 'refs/heads/fix/dot-wc3-continuation-20261118'",
            workflow,
        )
        self.assertIn("run: bash automation/verify_manual_head_checkout.sh", workflow)
        self.assertIn("github.head_ref != 'fix/dot-wc3-continuation-20261118'", workflow)
        self.assertIn("github.ref != 'refs/heads/fix/dot-wc3-continuation-20261118'", workflow)


if __name__ == "__main__":
    unittest.main()

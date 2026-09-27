import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

from automation.warcraftmap_agent.self_update import update_controller


class SelfUpdateTests(unittest.TestCase):
    def git(self, cwd: Path, *args: str) -> str:
        result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=True)
        return result.stdout.strip()

    def commit(self, repo: Path, name: str, content: str) -> str:
        (repo / name).write_text(content, encoding="utf-8")
        self.git(repo, "add", name)
        self.git(repo, "commit", "-m", content)
        return self.git(repo, "rev-parse", "HEAD")

    def repositories(self, root: Path) -> tuple[Path, Path]:
        remote, seed, controller = root / "remote.git", root / "seed", root / "controller"
        self.git(root, "init", "--bare", str(remote))
        self.git(root, "init", "-b", "main", str(seed))
        self.git(seed, "config", "user.name", "Test")
        self.git(seed, "config", "user.email", "test@example.invalid")
        self.commit(seed, "base.txt", "base")
        self.git(seed, "remote", "add", "origin", str(remote))
        self.git(seed, "push", "-u", "origin", "main")
        self.git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
        self.git(root, "clone", str(remote), str(controller))
        self.git(controller, "config", "user.name", "Test")
        self.git(controller, "config", "user.email", "test@example.invalid")
        return seed, controller

    def test_clean_controller_fast_forwards(self):
        with tempfile.TemporaryDirectory() as directory:
            seed, controller = self.repositories(Path(directory))
            expected = self.commit(seed, "new.txt", "upstream")
            self.git(seed, "push")
            self.assertTrue(update_controller(controller))
            self.assertEqual(self.git(controller, "rev-parse", "HEAD"), expected)

    def test_dirty_controller_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            seed, controller = self.repositories(Path(directory))
            before = self.git(controller, "rev-parse", "HEAD")
            (controller / "local.txt").write_text("keep me", encoding="utf-8")
            self.commit(seed, "new.txt", "upstream")
            self.git(seed, "push")
            errors = StringIO()
            with redirect_stderr(errors):
                self.assertFalse(update_controller(controller))
            self.assertIn("local changes", errors.getvalue())
            self.assertEqual(self.git(controller, "rev-parse", "HEAD"), before)
            self.assertEqual((controller / "local.txt").read_text(), "keep me")

    def test_non_fast_forward_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            seed, controller = self.repositories(Path(directory))
            self.commit(seed, "upstream.txt", "upstream")
            self.git(seed, "push")
            local = self.commit(controller, "local.txt", "local")
            errors = StringIO()
            with redirect_stderr(errors):
                self.assertFalse(update_controller(controller))
            self.assertIn("cannot fast-forward", errors.getvalue())
            self.assertEqual(self.git(controller, "rev-parse", "HEAD"), local)

    def test_controller_update_does_not_touch_issue_worktree(self):
        with tempfile.TemporaryDirectory() as directory:
            seed, controller = self.repositories(Path(directory))
            issue = Path(directory) / "issue-25"
            self.git(controller, "worktree", "add", "-b", "agent/issue-25", str(issue))
            before = self.git(issue, "rev-parse", "HEAD")
            marker = issue / "marker.txt"
            marker.write_text("preserve", encoding="utf-8")
            expected = self.commit(seed, "new.txt", "upstream")
            self.git(seed, "push")
            self.assertTrue(update_controller(controller))
            self.assertEqual(self.git(controller, "rev-parse", "HEAD"), expected)
            self.assertEqual(self.git(issue, "rev-parse", "HEAD"), before)
            self.assertEqual(marker.read_text(), "preserve")
            self.assertIn("?? marker.txt", self.git(issue, "status", "--porcelain"))

    def test_updater_refuses_an_issue_worktree(self):
        with tempfile.TemporaryDirectory() as directory:
            _, controller = self.repositories(Path(directory))
            issue = Path(directory) / "issue-25"
            self.git(controller, "worktree", "add", "-b", "agent/issue-25", str(issue))
            errors = StringIO()
            with redirect_stderr(errors):
                self.assertFalse(update_controller(issue, "agent/issue-25"))
            self.assertIn("isolated Git worktree", errors.getvalue())


if __name__ == "__main__":
    unittest.main()

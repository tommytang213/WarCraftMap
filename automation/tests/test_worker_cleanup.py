import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from automation.warcraftmap_agent.worker import Config, cleanup_merged_issue, service_open_prs


class WorkerCleanupTests(unittest.TestCase):
    @staticmethod
    def completed(args, returncode=0, stdout=""):
        return CompletedProcess(args, returncode, stdout, "")

    def test_successful_cleanup_removes_worktree_then_branches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worktree = root / "state/worktrees/issue-19"
            worktree.mkdir(parents=True)
            config = Config(root, root / "state")
            with patch("automation.warcraftmap_agent.worker.run", side_effect=lambda args, **kwargs: self.completed(args)) as mocked:
                self.assertEqual(cleanup_merged_issue(config, 19), [])
            commands = [call.args[0] for call in mocked.call_args_list]
            remove = ["git", "worktree", "remove", str(worktree)]
            local = ["git", "branch", "--delete", "--force", "agent/issue-19"]
            remote = ["git", "push", "origin", "--delete", "agent/issue-19"]
            self.assertLess(commands.index(remove), commands.index(local))
            self.assertIn(remote, commands)

    def test_dirty_worktree_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "state/worktrees/issue-19").mkdir(parents=True)
            config = Config(root, root / "state")
            def fake_run(args, **kwargs):
                if args[1:3] == ["status", "--porcelain"]:
                    return self.completed(args, stdout=" M valuable.wurst\n")
                return self.completed(args, returncode=2)
            with patch("automation.warcraftmap_agent.worker.run", side_effect=fake_run) as mocked:
                errors = cleanup_merged_issue(config, 19)
            commands = [call.args[0] for call in mocked.call_args_list]
            self.assertTrue(any("preserved dirty worktree" in error for error in errors))
            self.assertNotIn(["git", "worktree", "remove", str(root / "state/worktrees/issue-19")], commands)
            self.assertFalse(any(command[1] == "branch" for command in commands))

    def test_already_missing_worktree_and_branches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(root, root / "state")
            def fake_run(args, **kwargs):
                if args[1] == "show-ref":
                    return self.completed(args, returncode=1)
                if args[1] == "ls-remote":
                    return self.completed(args, returncode=2)
                return self.completed(args)
            with patch("automation.warcraftmap_agent.worker.run", side_effect=fake_run) as mocked:
                self.assertEqual(cleanup_merged_issue(config, 19), [])
            commands = [call.args[0] for call in mocked.call_args_list]
            self.assertIn(["git", "worktree", "prune"], commands)
            self.assertFalse(any(command[1] in {"branch", "push"} for command in commands))

    def test_cleanup_failure_keeps_confirmed_merge_successful(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(root, root / "state")
            state = {"issues": {"19": {"status": "pr_open", "pr": 42}}}
            with patch("automation.warcraftmap_agent.worker.gh_json", return_value={"state": "MERGED"}), patch("automation.warcraftmap_agent.worker.run", side_effect=RuntimeError("boom")):
                self.assertTrue(service_open_prs(config, state))
            record = state["issues"]["19"]
            self.assertEqual(record["status"], "merged")
            self.assertTrue(record["cleanup_errors"])


if __name__ == "__main__":
    unittest.main()

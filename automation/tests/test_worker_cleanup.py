import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from automation.warcraftmap_agent.worker import (
    Config,
    cleanup_merged_issue,
    prepare_merge_conflict_repair,
    service_open_prs,
)


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

    def test_finish_merged_issue_explicitly_closes_github_issue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(root, root / "state")
            record = {"status": "pr_open", "pr": 42}
            with patch("automation.warcraftmap_agent.worker.run", return_value=self.completed([])) as mocked, patch(
                "automation.warcraftmap_agent.worker.cleanup_merged_issue", return_value=[]
            ):
                from automation.warcraftmap_agent.worker import finish_merged_issue
                finish_merged_issue(config, "19", record)
            commands = [call.args[0] for call in mocked.call_args_list]
            self.assertIn(["gh", "issue", "close", "19", "--reason", "completed"], commands)
            self.assertEqual(record["status"], "merged")

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

    def test_dirty_pr_transitions_to_budgeted_conflict_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(root, root / "state", max_attempts=3)
            state = {"issues": {"19": {"status": "pr_open", "pr": 42, "attempts": 1}}}
            view = {
                "state": "OPEN",
                "mergeStateStatus": "DIRTY",
                "mergeable": "CONFLICTING",
                "statusCheckRollup": [{"status": "IN_PROGRESS"}],
                "baseRefName": "main",
            }
            with patch("automation.warcraftmap_agent.worker.gh_json", return_value=view), patch(
                "automation.warcraftmap_agent.worker.remote_branch_oid", return_value="base-a"
            ):
                self.assertTrue(service_open_prs(config, state))
            record = state["issues"]["19"]
            self.assertEqual(record["status"], "repair")
            self.assertEqual(record["repair_kind"], "merge_conflict")
            self.assertIn("DIRTY", record["last_failure"])

    def test_pending_and_clean_prs_are_not_sent_to_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(root, root / "state")
            pending = {"issues": {"19": {"status": "pr_open", "pr": 42, "attempts": 1}}}
            pending_view = {
                "state": "OPEN",
                "mergeStateStatus": "BLOCKED",
                "mergeable": "UNKNOWN",
                "statusCheckRollup": [{"status": "IN_PROGRESS"}],
            }
            with patch("automation.warcraftmap_agent.worker.gh_json", return_value=pending_view):
                self.assertFalse(service_open_prs(config, pending))
            self.assertEqual(pending["issues"]["19"]["status"], "pr_open")

            clean = {"issues": {"20": {"status": "pr_open", "pr": 43, "attempts": 1}}}
            clean_view = {
                "state": "OPEN",
                "mergeStateStatus": "CLEAN",
                "mergeable": "MERGEABLE",
                "statusCheckRollup": [{"status": "COMPLETED", "conclusion": "SUCCESS"}],
            }
            with patch("automation.warcraftmap_agent.worker.gh_json", return_value=clean_view), patch(
                "automation.warcraftmap_agent.worker.run", return_value=self.completed([])
            ), patch("automation.warcraftmap_agent.worker.finish_merged_issue"):
                self.assertTrue(service_open_prs(config, clean))
            self.assertNotEqual(clean["issues"]["20"].get("status"), "repair")

    def test_dirty_pr_uses_separate_conflict_attempt_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(root, root / "state", max_attempts=3)
            state = {"issues": {"19": {"status": "pr_open", "pr": 42, "attempts": 3}}}
            view = {
                "state": "OPEN",
                "mergeStateStatus": "DIRTY",
                "mergeable": "CONFLICTING",
                "statusCheckRollup": [],
                "baseRefOid": "base-a",
            }
            with patch("automation.warcraftmap_agent.worker.gh_json", return_value=view), patch(
                "automation.warcraftmap_agent.worker.remote_branch_oid", return_value="base-a"
            ):
                self.assertTrue(service_open_prs(config, state))
            record = state["issues"]["19"]
            self.assertEqual(record["status"], "repair")
            self.assertEqual(record["repair_kind"], "merge_conflict")
            self.assertEqual(record.get("conflict_attempts", 0), 0)
            self.assertEqual(record["conflict_base_oid"], "base-a")

    def test_dirty_pr_at_conflict_attempt_limit_fails_with_clear_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(root, root / "state", max_attempts=3)
            state = {
                "issues": {
                    "19": {
                        "status": "pr_open",
                        "pr": 42,
                        "attempts": 3,
                        "conflict_attempts": 3,
                    }
                }
            }
            state["issues"]["19"]["conflict_base_oid"] = "base-a"
            view = {
                "state": "OPEN",
                "mergeStateStatus": "DIRTY",
                "mergeable": "CONFLICTING",
                "statusCheckRollup": [],
                "baseRefOid": "base-a",
            }
            with patch("automation.warcraftmap_agent.worker.gh_json", return_value=view), patch(
                "automation.warcraftmap_agent.worker.remote_branch_oid", return_value="base-a"
            ):
                self.assertTrue(service_open_prs(config, state))
            record = state["issues"]["19"]
            self.assertEqual(record["status"], "failed")
            self.assertIn("conflict-repair attempt limit (3) is exhausted", record["last_failure"])

    def test_new_base_resets_exhausted_conflict_attempt_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(root, root / "state", max_attempts=3)
            state = {
                "issues": {
                    "19": {
                        "status": "failed",
                        "pr": 42,
                        "attempts": 3,
                        "conflict_attempts": 3,
                        "conflict_base_oid": "old-base",
                        "repair_kind": "merge_conflict",
                        "last_failure": (
                            "PR #42 is unmergeable because main conflicts with the issue branch, "
                            "and the conflict-repair attempt limit (3) is exhausted."
                        ),
                    }
                }
            }
            view = {
                "state": "OPEN",
                "mergeStateStatus": "DIRTY",
                "mergeable": "CONFLICTING",
                "statusCheckRollup": [],
                "baseRefName": "main",
            }
            with patch("automation.warcraftmap_agent.worker.gh_json", return_value=view), patch(
                "automation.warcraftmap_agent.worker.remote_branch_oid", return_value="new-base"
            ):
                self.assertTrue(service_open_prs(config, state))
            record = state["issues"]["19"]
            self.assertEqual(record["status"], "repair")
            self.assertEqual(record["conflict_attempts"], 0)
            self.assertEqual(record["conflict_base_oid"], "new-base")


    def test_failed_conflict_pr_with_unknown_mergeability_blocks_planner_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(root, root / "state")
            state = {
                "issues": {
                    "19": {
                        "status": "failed",
                        "pr": 42,
                        "attempts": 3,
                        "conflict_attempts": 3,
                        "repair_kind": "merge_conflict",
                        "last_failure": (
                            "PR #42 is unmergeable because main conflicts with the issue branch, "
                            "and the conflict-repair attempt limit (3) is exhausted."
                        ),
                    }
                }
            }
            view = {
                "state": "OPEN",
                "mergeStateStatus": "UNKNOWN",
                "mergeable": "UNKNOWN",
                "statusCheckRollup": [],
                "baseRefName": "main",
            }
            with patch("automation.warcraftmap_agent.worker.gh_json", return_value=view):
                self.assertTrue(service_open_prs(config, state))
            self.assertEqual(state["issues"]["19"]["status"], "failed")

    def test_conflicting_mergeable_fallback_enters_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(root, root / "state", max_attempts=3)
            state = {
                "issues": {
                    "19": {
                        "status": "failed",
                        "pr": 42,
                        "attempts": 3,
                        "conflict_attempts": 3,
                        "repair_kind": "merge_conflict",
                        "last_failure": (
                            "PR #42 is unmergeable because main conflicts with the issue branch, "
                            "and the conflict-repair attempt limit (3) is exhausted."
                        ),
                    }
                }
            }
            view = {
                "state": "OPEN",
                "mergeStateStatus": "UNKNOWN",
                "mergeable": "CONFLICTING",
                "statusCheckRollup": [],
                "baseRefName": "main",
            }
            with patch("automation.warcraftmap_agent.worker.gh_json", return_value=view), patch(
                "automation.warcraftmap_agent.worker.remote_branch_oid", return_value="new-base"
            ):
                self.assertTrue(service_open_prs(config, state))
            record = state["issues"]["19"]
            self.assertEqual(record["status"], "repair")
            self.assertEqual(record["conflict_attempts"], 0)
            self.assertEqual(record["conflict_base_oid"], "new-base")

    def test_conflict_repair_fetches_and_merges_current_default_branch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(root, root / "state")

            def fake_run(args, **kwargs):
                if args[1:4] == ["rev-parse", "--verify", "--quiet"]:
                    return self.completed(args, returncode=1)
                if args[:2] == ["gh", "repo"]:
                    return self.completed(args, stdout="main\n")
                if args[1:3] == ["merge", "--no-edit"]:
                    return self.completed(args, returncode=1, stdout="conflict")
                if args[1:4] == ["diff", "--name-only", "--diff-filter=U"]:
                    return self.completed(args, stdout="automation/worker.py\n")
                return self.completed(args)

            with patch("automation.warcraftmap_agent.worker.run", side_effect=fake_run) as mocked:
                conflicts = prepare_merge_conflict_repair(config, root / "worktree")
            commands = [call.args[0] for call in mocked.call_args_list]
            self.assertEqual(conflicts, ["automation/worker.py"])
            self.assertIn(["git", "fetch", "origin"], commands)
            self.assertIn(["git", "merge", "--no-edit", "origin/main"], commands)


if __name__ == "__main__":
    unittest.main()

"""Exercise repair-lane transitions with real local Git merges and persisted state."""
import json
import subprocess
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from automation.warcraftmap_agent import worker


class ValidationRepairTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.upstream = self.root / "upstream"
        self.worktree = self.root / "issue"
        self.git(self.root, "init", "-b", "main", str(self.upstream))
        self.configure_git(self.upstream)
        (self.upstream / "shared.txt").write_text("base\n")
        self.commit(self.upstream)
        self.git(self.root, "clone", str(self.upstream), str(self.worktree))
        self.configure_git(self.worktree)
        self.git(self.worktree, "checkout", "-b", "agent/issue-402")
        self.config = worker.Config(self.worktree, self.root / "state")
        self.state_path = self.config.state_dir / "state.json"
        self.issue = {"number": 402, "title": "[agent-ready] Repair validation", "body": "Implement it."}
        self.original_failure = "command failed (1): ./automation/run_checks.sh\nFAILED: original validation assertion"
        self.launches = []
        self.action = lambda: {"outcome": "complete"}
        self.checks = mock.Mock(side_effect=self.assert_ready_for_validation)
        self.publish = mock.Mock(return_value=403)
        self.invoke = mock.Mock(side_effect=self.launch_codex)
        patches = self.enterContext(ExitStack())
        # Git stays real and local. All external services and publication are
        # replaced at their boundaries; each main() call reloads actual state.
        for name, value in {
            "default_branch": mock.Mock(return_value="main"),
            "make_config": mock.Mock(return_value=self.config),
            "promote_planned_issues": mock.Mock(return_value=[]),
            "list_issues": mock.Mock(return_value=[self.issue]),
            "list_needs_design_issues": mock.Mock(return_value=[]),
            "service_open_prs": mock.Mock(return_value=False),
            "queue_refill_count": mock.Mock(return_value=0),
            "worktree_for": mock.Mock(return_value=(self.worktree, "agent/issue-402")),
            "invoke_codex": self.invoke,
            "run_checks": self.checks,
            "publish": self.publish,
        }.items():
            patches.enter_context(mock.patch.object(worker, name, value))

    def git(self, cwd, *args):
        return subprocess.run(
            ["git", *args], cwd=cwd, text=True, capture_output=True, check=True,
        ).stdout.strip()

    def configure_git(self, repo):
        for key, value in {"user.name": "Test", "user.email": "test@example.invalid", "commit.gpgsign": "false"}.items():
            self.git(repo, "config", key, value)

    def commit(self, repo):
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-m", "Fixture changes")
        return self.git(repo, "rev-parse", "HEAD")

    def diverge(self, *, conflict=True, **record_overrides):
        (self.upstream / "main.txt").write_text("current main work\n")
        (self.worktree / "issue.txt").write_text("issue implementation\n")
        if conflict:
            (self.upstream / "shared.txt").write_text("main change\n")
            (self.worktree / "shared.txt").write_text("issue change\n")
        self.base_oid = self.commit(self.upstream)
        record = {
            "attempts": 3, "validation_repair_attempts": 2, "conflict_attempts": 0,
            "status": "repair", "repair_kind": "validation",
            "validation_base_oid": self.base_oid, "last_failure": self.original_failure,
            **record_overrides,
        }
        worker.save_state(self.state_path, {"version": 2, "runs": [], "issues": {"402": record}})

    def prepare_validation(self):
        return worker.prepare_validation_repair(self.config, self.worktree, 402)

    def state(self):
        return worker.load_state(self.state_path)

    def record(self):
        return self.state()["issues"]["402"]

    def launch_codex(self, config, worktree, issue, record, run_entry):
        persisted = self.state()
        self.assertEqual(record, persisted["issues"]["402"])
        self.assertEqual(run_entry, persisted["runs"][-1])
        prompt = worker.codex_prompt(issue, record["last_failure"], repair_kind=worker.repair_kind(record))
        self.launches.append((record.copy(), prompt))
        return self.action()

    def assert_ready_for_validation(self, config, worktree):
        self.assertEqual(worker.unmerged_paths(worktree), [])
        self.assertEqual(self.record()["repair_kind"], "validation")
        self.assert_work_preserved()

    def assert_work_preserved(self):
        self.assertEqual((self.worktree / "main.txt").read_text(), "current main work\n")
        self.assertEqual((self.worktree / "issue.txt").read_text(), "issue implementation\n")

    def resolve_merge(self):
        (self.worktree / "shared.txt").write_text("main change\nissue change\n")
        self.git(self.worktree, "add", "shared.txt")
        return {"outcome": "complete"}

    def tick(self, action=None):
        self.action = action or (lambda: {"outcome": "complete"})
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(worker.main([]), 0)
        return self.record()

    def test_prepare_validation_without_conflicts_preserves_both_work_streams(self):
        self.diverge(conflict=False)
        self.assertEqual(self.prepare_validation(), (self.base_oid, []))
        self.assert_work_preserved()
        self.assertEqual(self.git(self.worktree, "status", "--porcelain"), "")
        self.git(self.worktree, "merge-base", "--is-ancestor", self.base_oid, "HEAD")
        self.assertEqual(self.git(self.worktree, "show", "HEAD:issue.txt"), "issue implementation")

    def test_prepare_validation_leaves_genuine_conflicts_for_codex(self):
        self.diverge()
        self.assertEqual(self.prepare_validation(), (self.base_oid, ["shared.txt"]))
        self.assertEqual(self.git(self.worktree, "rev-parse", "MERGE_HEAD"), self.base_oid)
        self.assertEqual(self.git(self.worktree, "show", ":2:shared.txt"), "issue change")
        self.assertEqual(self.git(self.worktree, "show", ":3:shared.txt"), "main change")
        self.assert_work_preserved()

    def test_existing_conflicts_are_not_checkpointed_or_remerged(self):
        self.diverge()
        self.prepare_validation()
        head = self.git(self.worktree, "rev-parse", "HEAD")
        index = self.git(self.worktree, "ls-files", "--stage")
        contents = (self.worktree / "shared.txt").read_text()
        self.assertEqual(self.prepare_validation(), (self.base_oid, ["shared.txt"]))
        self.assertEqual(worker.prepare_merge_conflict_repair(self.config, self.worktree), ["shared.txt"])
        self.assertEqual(self.git(self.worktree, "rev-parse", "HEAD"), head)
        self.assertEqual(self.git(self.worktree, "ls-files", "--stage"), index)
        self.assertEqual((self.worktree / "shared.txt").read_text(), contents)

    def test_legacy_validation_record_with_an_unfinished_merge_enters_conflict_lane(self):
        self.diverge(repair_kind="")
        self.prepare_validation()
        head = self.git(self.worktree, "rev-parse", "HEAD")
        record = self.tick()
        self.assertEqual(record["repair_kind"], "merge_conflict")
        self.assertEqual(record["validation_failure"], self.original_failure)
        self.assertEqual(record["validation_repair_attempts"], 2)
        self.assertEqual(record["conflict_attempts"], 1)
        self.assertEqual(self.git(self.worktree, "rev-parse", "HEAD"), head)
        self.assertEqual(worker.unmerged_paths(self.worktree), ["shared.txt"])
        self.assertIn("This is an integration repair.", self.launches[0][1])

    def test_preparation_failure_does_not_consume_a_codex_attempt(self):
        self.diverge(conflict=False)
        with mock.patch.object(worker, "prepare_validation_repair", side_effect=RuntimeError("fetch failed")):
            record = self.tick()
        self.assertEqual(record["status"], "repair")
        self.assertEqual(record["repair_kind"], "validation")
        self.assertEqual(record["validation_failure"], self.original_failure)
        self.assertEqual(record["validation_repair_attempts"], 2)
        self.assertEqual(record["conflict_attempts"], 0)
        self.assertEqual(self.state()["runs"], [])
        self.invoke.assert_not_called()

    def test_validation_without_conflict_charges_only_validation_and_publishes(self):
        self.diverge(conflict=False, conflict_attempts=1)
        record = self.tick()
        launched, prompt = self.launches[0]
        self.assertEqual(launched["repair_kind"], "validation")
        self.assertEqual(record["validation_repair_attempts"], 3)
        self.assertEqual(record["conflict_attempts"], 1)
        self.assertEqual(record["attempts"], 3)
        self.assertIn(self.original_failure, prompt)
        self.assertNotIn("This is an integration repair.", prompt)
        self.checks.assert_called_once()
        self.publish.assert_called_once()
        self.assertEqual(record["status"], "pr_open")
        self.assertNotIn("repair_kind", record)
        self.assertNotIn("validation_failure", record)

    def test_validation_conflict_switches_lane_before_launch_and_does_not_validate(self):
        self.diverge()
        record = self.tick()
        launched, prompt = self.launches[0]
        self.assertEqual(launched["repair_kind"], "merge_conflict")
        self.assertEqual(record["validation_repair_attempts"], 2)
        self.assertEqual(record["conflict_attempts"], 1)
        self.assertEqual(record["attempts"], 3)
        self.assertEqual(record["validation_failure"], self.original_failure)
        self.assertEqual(record["status"], "repair")
        self.assertEqual(record["repair_kind"], "merge_conflict")
        self.assertIn("shared.txt", prompt)
        self.assertIn(self.original_failure, prompt)
        self.assertIn("This is an integration repair.", prompt)
        self.assertIn("Do not discard or broadly rewrite either work stream.", prompt)
        self.assertIn("Stage each resolved path with git add", prompt)
        self.checks.assert_not_called()
        self.publish.assert_not_called()

    def test_repeated_conflict_repairs_preserve_validation_context_and_exhaust_conflict_budget(self):
        self.diverge()

        def timeout():
            raise RuntimeError("Codex exceeded timeout")

        actions = [lambda: {"outcome": "blocked", "summary": "Merge incomplete"}, timeout, None]
        for attempt, action in enumerate(actions, 1):
            with self.subTest(attempt=attempt):
                record = self.tick(action)
                self.assertEqual(record["repair_kind"], "merge_conflict")
                self.assertEqual(record["validation_repair_attempts"], 2)
                self.assertEqual(record["conflict_attempts"], attempt)
                self.assertEqual(record["validation_failure"], self.original_failure)
                self.assertIn(self.original_failure, self.launches[-1][1])
                self.assertIn("This is an integration repair.", self.launches[-1][1])
                self.assertEqual(worker.unmerged_paths(self.worktree), ["shared.txt"])
        self.assertEqual(record["status"], "failed")
        self.assertIn("conflict-repair attempt limit (3) is exhausted", record["last_failure"])
        self.tick()
        self.assertEqual(self.invoke.call_count, 3)
        self.assertEqual(len(self.state()["runs"]), 3)
        self.checks.assert_not_called()
        self.publish.assert_not_called()

    def test_clean_merge_resumes_validation_automatically_and_uses_its_next_retry(self):
        self.diverge(conflict_attempts=2)
        validation_failure = "Repository checks still fail after the merge"
        self.checks.side_effect = RuntimeError(validation_failure)
        record = self.tick(self.resolve_merge)
        self.assertEqual(record["repair_kind"], "validation")
        self.assertEqual(record["validation_repair_attempts"], 2)
        self.assertEqual(record["conflict_attempts"], 3)
        self.assertEqual(record["status"], "repair")
        self.assertEqual(record["validation_failure"], validation_failure)
        self.checks.assert_called_once()
        self.publish.assert_not_called()
        self.checks.side_effect = self.assert_ready_for_validation
        record = self.tick()
        launched, prompt = self.launches[-1]
        self.assertEqual(launched["repair_kind"], "validation")
        self.assertEqual(record["validation_repair_attempts"], 3)
        self.assertEqual(record["conflict_attempts"], 3)
        self.assertIn(validation_failure, prompt)
        self.assertNotIn("This is an integration repair.", prompt)
        self.assertEqual(self.checks.call_count, 2)
        self.publish.assert_called_once()
        self.assertEqual(record["status"], "pr_open")
        self.assertNotIn("validation_failure", record)
        self.git(self.worktree, "merge-base", "--is-ancestor", self.base_oid, "HEAD")
        self.assertEqual((self.worktree / "shared.txt").read_text(), "main change\nissue change\n")

    def test_resolved_conflict_validates_and_publishes_in_same_run(self):
        self.diverge()
        record = self.tick(self.resolve_merge)
        self.checks.assert_called_once()
        self.publish.assert_called_once()
        self.assertEqual(record["validation_repair_attempts"], 2)
        self.assertEqual(record["conflict_attempts"], 1)
        self.assertEqual(record["status"], "pr_open")
        self.assertNotIn("validation_failure", record)
        self.assertNotIn("repair_kind", record)
        self.assertEqual((self.worktree / "shared.txt").read_text(), "main change\nissue change\n")

    def test_exhausted_conflict_budget_prevents_launch_without_charging_validation(self):
        self.diverge(conflict_attempts=3)
        record = self.tick()
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["repair_kind"], "merge_conflict")
        self.assertEqual(record["validation_repair_attempts"], 2)
        self.assertEqual(record["conflict_attempts"], 3)
        self.assertEqual(record["validation_failure"], self.original_failure)
        self.assertIn("conflict-repair attempt limit (3) is exhausted", record["last_failure"])
        self.assertEqual(worker.unmerged_paths(self.worktree), ["shared.txt"])
        self.tick()
        self.invoke.assert_not_called()
        self.checks.assert_not_called()
        self.publish.assert_not_called()
        self.assertEqual(self.state()["runs"], [])
        self.assert_work_preserved()

    def test_timeout_after_resolving_last_conflict_attempt_does_not_strand_validation(self):
        self.diverge(conflict_attempts=2)

        def resolve_then_timeout():
            self.resolve_merge()
            raise RuntimeError("Codex exceeded timeout after resolving the merge")

        record = self.tick(resolve_then_timeout)
        self.assertEqual(record["status"], "repair")
        self.assertEqual(record["repair_kind"], "validation")
        self.assertEqual(record["conflict_attempts"], 3)
        self.assertEqual(record["validation_repair_attempts"], 2)
        self.assertEqual(record["validation_failure"], self.original_failure)
        self.checks.assert_not_called()
        record = self.tick()
        self.assertEqual(record["status"], "pr_open")
        self.assertEqual(record["validation_repair_attempts"], 3)
        self.assertEqual(record["conflict_attempts"], 3)
        self.assertIn(self.original_failure, self.launches[-1][1])
        self.checks.assert_called_once()

    def test_already_resolved_merge_returns_to_validation_before_charging(self):
        self.diverge(repair_kind="merge_conflict", validation_failure=self.original_failure, conflict_attempts=1)
        self.prepare_validation()
        self.resolve_merge()
        record = self.tick()
        self.assertEqual(self.launches[0][0]["repair_kind"], "validation")
        self.assertNotIn("This is an integration repair.", self.launches[0][1])
        self.assertEqual(record["validation_repair_attempts"], 3)
        self.assertEqual(record["conflict_attempts"], 1)
        self.checks.assert_called_once()

    def test_validation_budget_is_rechecked_after_return_from_clean_conflict_lane(self):
        self.diverge(repair_kind="merge_conflict", validation_failure=self.original_failure,
                     conflict_attempts=1, validation_repair_attempts=5)
        self.prepare_validation()
        self.resolve_merge()
        record = self.tick()
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["repair_kind"], "validation")
        self.assertEqual(record["validation_repair_attempts"], 5)
        self.assertEqual(record["conflict_attempts"], 1)
        self.assertIn("validation-repair attempt limit (5) is exhausted", record["last_failure"])
        self.assertEqual(self.state()["runs"], [])
        self.invoke.assert_not_called()


class RepairPromptTests(unittest.TestCase):
    def test_explicit_lane_selects_prompt_independently_of_latest_error_text(self):
        issue = {"number": 402, "title": "[agent-ready] Repair", "body": ""}
        prompt = worker.codex_prompt(issue, "Codex exited 1", repair_kind="merge_conflict")
        self.assertIn("This is an integration repair.", prompt)
        prompt = worker.codex_prompt(issue, "Merge conflict repair required: old failure", repair_kind="validation")
        self.assertNotIn("This is an integration repair.", prompt)

    def test_codex_invocation_passes_the_persisted_conflict_lane_to_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = worker.Config(root, root)
            (root / "last-codex-result.json").write_text(json.dumps({"outcome": "complete"}))
            process = mock.Mock(returncode=0)
            process.communicate.return_value = ("", None)
            record = {"attempts": 3, "repair_kind": "merge_conflict", "last_failure": "Codex exited 1"}
            issue = {"number": 402, "title": "[agent-ready] Repair", "body": ""}
            with mock.patch.object(worker.subprocess, "Popen", return_value=process):
                worker.invoke_codex(config, root, issue, record, {})
            self.assertIn("This is an integration repair.", process.communicate.call_args.args[0])


if __name__ == "__main__":
    unittest.main()

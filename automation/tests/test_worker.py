import tempfile
import unittest
from pathlib import Path

from automation.warcraftmap_agent.worker import Config, build_codex_command, check_state, load_env, select_issue


class WorkerTests(unittest.TestCase):
    def test_load_env_does_not_execute_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config"
            path.write_text('WARCRAFTMAP_AGENT_MODEL="small model"\n# comment\n', encoding="utf-8")
            self.assertEqual(load_env(path)["WARCRAFTMAP_AGENT_MODEL"], "small model")

    def test_selects_oldest_eligible_ready_issue(self):
        issues = [
            {"number": 2, "title": "[agent-ready] second", "createdAt": "2026-01-02"},
            {"number": 1, "title": "[agent-ready] first", "createdAt": "2026-01-01"},
        ]
        state = {"issues": {"1": {"attempts": 3, "status": "failed"}}}
        self.assertEqual(select_issue(issues, state, 3)["number"], 2)

    def test_skips_open_pr(self):
        issues = [{"number": 1, "title": "[agent-ready] task", "createdAt": "2026-01-01"}]
        state = {"issues": {"1": {"attempts": 1, "status": "pr_open"}}}
        self.assertIsNone(select_issue(issues, state, 3))


    def test_codex_command_uses_approve_for_me_without_conflicting_sandbox_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = Config(repo_root=root, state_dir=root / "state")
            command = build_codex_command(
                config,
                root / "worktree",
                root / "schema.json",
                root / "result.json",
            )
        self.assertIn("--approve-for-me", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ephemeral", command)
        self.assertNotIn("--sandbox", command)

    def test_normalizes_both_github_check_shapes(self):
        self.assertEqual(check_state({"status": "COMPLETED", "conclusion": "SUCCESS"}), "passed")
        self.assertEqual(check_state({"status": "IN_PROGRESS"}), "pending")
        self.assertEqual(check_state({"state": "SUCCESS"}), "passed")
        self.assertEqual(check_state({"state": "FAILURE"}), "failed")


if __name__ == "__main__":
    unittest.main()

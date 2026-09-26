import tempfile
import unittest
from pathlib import Path

from automation.warcraftmap_agent.worker import check_state, load_env, select_issue


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

    def test_normalizes_both_github_check_shapes(self):
        self.assertEqual(check_state({"status": "COMPLETED", "conclusion": "SUCCESS"}), "passed")
        self.assertEqual(check_state({"status": "IN_PROGRESS"}), "pending")
        self.assertEqual(check_state({"state": "SUCCESS"}), "passed")
        self.assertEqual(check_state({"state": "FAILURE"}), "failed")


if __name__ == "__main__":
    unittest.main()

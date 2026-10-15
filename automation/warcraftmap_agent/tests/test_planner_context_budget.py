"""Regression tests for oversized Codex planner input."""
import json
import unittest

from automation.warcraftmap_agent.worker import (
    PLANNER_INPUT_BUDGET,
    compact_planning_history,
    planning_prompt,
)


class FakeClosure:
    def planning_view(self, requested):
        return {"active": True, "candidates": [{"key": "release:TEST-BLOCKER"}]}


class PlannerContextBudgetTests(unittest.TestCase):
    def test_preserves_all_history_identifiers_without_archived_prose(self):
        context = {
            "issues": [
                {"number": 1, "title": "[done] One", "state": "CLOSED",
                 "body": "archived " * 20000},
                {"number": 2, "title": "[agent-ready] Two", "state": "OPEN",
                 "body": "Details\nDepends on: #1\nClosure blocker: release:EXAMPLE\n" + "x" * 10000},
            ],
            "pull_requests": [
                {"number": 3, "state": "MERGED", "body": "legacy " * 20000,
                 "closingIssuesReferences": [{"number": 1}]}
            ],
        }
        result = compact_planning_history(context, body_limit=700)
        self.assertEqual([1, 2], [i["number"] for i in result["issues"]])
        self.assertEqual(result["issues"][0]["body"], "")
        self.assertIn("Depends on: #1", result["issues"][1]["planning_references"])
        self.assertIn("Closure blocker: release:EXAMPLE",
                      result["issues"][1]["planning_references"])
        self.assertEqual(result["pull_requests"][0]["closingIssuesReferences"],
                         [{"number": 1}])

    def test_large_history_keeps_prompt_below_budget(self):
        context = {
            "issues": [
                {"number": i, "title": f"Issue {i}", "state": "CLOSED",
                 "body": "huge historical prose " * 500}
                for i in range(1200)
            ],
            "pull_requests": [],
            "git_history": "",
            "git_status": "",
            "closure": FakeClosure(),
        }
        prompt = planning_prompt(context, requested=3)
        self.assertLessEqual(len(prompt), PLANNER_INPUT_BUDGET)
        self.assertIn("release:TEST-BLOCKER", prompt)
        self.assertIn('"number": 1199', prompt)

    def test_fail_closed_if_even_metadata_exceeds_budget(self):
        context = {
            "issues": [
                {"number": i, "title": "x" * 5000, "state": "CLOSED", "body": ""}
                for i in range(200)
            ],
            "pull_requests": [], "git_history": "", "git_status": "",
            "closure": FakeClosure(),
        }
        with self.assertRaisesRegex(ValueError, "exceeds safe"):
            planning_prompt(context, requested=3)


if __name__ == "__main__":
    unittest.main()

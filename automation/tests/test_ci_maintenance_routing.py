"""Regression checks for the explicitly approved #427 CI maintenance exception.

This is a narrow routing permission, not general permission to bypass release
closure or launch acceptance. GitHub PR dependencies are satisfied by MERGED
states with timestamps, never by a PR that was only closed.
"""
import unittest

from automation.warcraftmap_agent.closure import Blocker, Closure
from automation.warcraftmap_agent.worker import (
    completed_dependency_numbers,
    issue_blocker_numbers,
    select_issue,
)


MAIN = "a" * 40
_BLOCKERS = {"release:LAUNCH": Blocker("release:LAUNCH", "Real client launch", ["native crash"], ["release"])}


def issue(number, title, body="", created="2026-01-01", state="OPEN"):
    return {"number": number, "title": title, "body": body, "createdAt": created, "state": state}


def pr426(state="OPEN", merged_at=None):
    return {"number": 426, "state": state, "mergedAt": merged_at}


def closure_with(prs, fresh=True):
    return Closure(MAIN, fresh, _BLOCKERS, issues=[], prs=prs)


class MaintenanceRoutingTests(unittest.TestCase):
    def setUp(self):
        self.maintenance = issue(
            427, "[agent-ready] Stage high-overlap Codex work",
            "Depends on: #426", "2026-01-02",
        )
        self.launch = issue(
            425, "[agent-ready] Diagnose launch crash",
            "Closure blocker: release:LAUNCH", "2026-01-01",
        )

    def test_open_or_closed_unmerged_pr_does_not_release_maintenance(self):
        for state, merged_at in [
            ("OPEN", None), ("CLOSED", None),
            ("CLOSED", "2026-10-08T17:00:00Z"),
            ("MERGED", None),
        ]:
            with self.subTest(state=state, merged_at=merged_at):
                prs = [pr426(state, merged_at)]
                closure = closure_with(prs)
                completed = completed_dependency_numbers([], prs)
                self.assertNotIn(426, completed)
                self.assertFalse(closure.permits_issue(self.maintenance))
                pending = issue_blocker_numbers(self.maintenance) - completed
                self.assertIn(426, pending)
                self.assertIsNone(select_issue(
                    [self.maintenance], {"issues": {}}, 3, pending, closure=closure))

    def test_merged_pr_unlocks_only_issue_427_under_release_closure(self):
        prs = [pr426("MERGED", "2026-10-08T17:00:00Z")]
        closure = closure_with(prs)
        self.assertTrue(closure.active)
        self.assertIn(426, completed_dependency_numbers([], prs))
        self.assertTrue(closure.permits_issue(self.maintenance))
        self.assertFalse(closure.permits_issue(
            issue(428, "[agent-ready] Unrelated content", "Depends on: #426")))
        self.assertFalse(closure.permits_issue(
            issue(427, "[planned] Stage high-overlap Codex work", "Depends on: #426")))
        self.assertFalse(closure_with(prs, fresh=False).permits_issue(self.maintenance))
        self.assertEqual(select_issue([self.maintenance], {"issues": {}}, 3,
                                      closure=closure)["number"], 427)

    def test_launch_crash_retains_priority_when_both_are_ready(self):
        prs = [pr426("MERGED", "2026-10-08T17:00:00Z")]
        closure = Closure(MAIN, True, _BLOCKERS,
                          issues=[self.launch, self.maintenance], prs=prs)
        self.assertEqual(select_issue(
            [self.launch, self.maintenance], {"issues": {}}, 3,
            closure=closure)["number"], 425)
        # When launch repair already has a PR in progress, the maintenance
        # job can use the existing bounded single worker.
        state = {"issues": {"425": {"status": "pr_open", "attempts": 1}}}
        self.assertEqual(select_issue(
            [self.launch, self.maintenance], state, 3,
            closure=closure)["number"], 427)

    def test_resolved_dependency_numbers_do_not_confuse_closed_issues_with_prs(self):
        issues = [issue(12, "done", state="CLOSED"), issue(13, "open")]
        prs = [
            pr426("MERGED", "2026-10-08T17:00:00Z"),
            {"number": 450, "state": "CLOSED", "mergedAt": None},
            {"number": 451, "state": "MERGED", "mergedAt": None},
        ]
        self.assertEqual(completed_dependency_numbers(issues, prs), {12, 426})


if __name__ == "__main__":
    unittest.main()

"""Protect the narrowly authorized evidence-first native launch diagnosis.

A verified Warcraft crash cannot depend on the headless evidence it prevents.
This is a worker *selection* exception, not a native-success or release-gate
exception. Do not broaden it to arbitrary [agent-ready] tickets.
"""
import unittest

from automation.warcraftmap_agent.closure import Blocker, Closure
from automation.warcraftmap_agent.worker import select_issue


REVISION = "a" * 40
LAUNCH = "runtime:campaign_launch"
EVIDENCE = "runtime:evidence"


def issue(number, title, *, keys=(), failed=False):
    body = "\n".join(f"Closure blocker: {k}" for k in keys)
    if failed:
        body += "\nNative launch status: failed\n"
    return {"number": number, "title": title, "body": body,
            "createdAt": str(number), "state": "OPEN"}


def closure(*, fresh=True, extra_dependencies=()):
    blockers = {
        LAUNCH: Blocker(LAUNCH, "Native campaign launch", ["still crashes"],
                        ["reports/runtime-acceptance.json"],
                        {EVIDENCE, *extra_dependencies}),
        EVIDENCE: Blocker(EVIDENCE, "Headless evidence missing",
                          ["no same-revision execution"], ["reports/runtime-acceptance.json"]),
    }
    return Closure(REVISION, fresh, blockers, reports={
        "runtime": {"regenerated": fresh},
        "release": {"regenerated": fresh},
        "traceability": {"regenerated": fresh},
    })


class NativeLaunchDiagnosticRoutingTests(unittest.TestCase):
    def setUp(self):
        self.crash = issue(438, "[agent-ready] Investigate native campaign crash",
                           keys=[LAUNCH], failed=True)

    def test_crash_is_actionable_despite_missing_headless_evidence(self):
        gate = closure()
        self.assertTrue(gate.active)
        self.assertNotIn(LAUNCH, gate.actionable)
        self.assertTrue(gate.permits_issue(self.crash))
        self.assertEqual(select_issue([self.crash], {"issues": {}}, 3,
                                      closure=gate)["number"], 438)
        # Routing never marks any audit clean or supplies runtime evidence.
        self.assertIn(EVIDENCE, gate.blockers)
        self.assertTrue(gate.active)

    def test_no_exception_for_unproven_or_wrongly_routed_issues(self):
        gate = closure()
        failures = [
            issue(439, "[agent-ready] Investigate native campaign crash",
                  keys=[LAUNCH], failed=True),
            issue(438, "[agent-ready] Investigate native campaign crash",
                  keys=[LAUNCH], failed=False),
            issue(438, "[planned] Investigate native campaign crash",
                  keys=[LAUNCH], failed=True),
            issue(438, "[needs-design] Investigate native campaign crash",
                  keys=[LAUNCH], failed=True),
            issue(438, "[agent-ready] Investigate native campaign crash",
                  keys=[LAUNCH, EVIDENCE], failed=True),
            issue(438, "[agent-ready] Investigate native campaign crash",
                  keys=[EVIDENCE], failed=True),
        ]
        for bad in failures:
            with self.subTest(title=bad["title"], number=bad["number"],
                              body=bad["body"]):
                # The standard release rules may permit actual evidence repairs,
                # so only test the native-launch key cases here.
                if LAUNCH in bad["body"] and EVIDENCE not in bad["body"]:
                    self.assertFalse(gate.permits_issue(bad))

    def test_other_dependencies_and_stale_checkout_remain_blocking(self):
        self.assertFalse(closure(fresh=False).permits_issue(self.crash))
        self.assertFalse(closure(extra_dependencies=("traceability:dependent",))
                         .permits_issue(self.crash))

    def test_real_client_crash_preempts_independent_evidence_work_only_when_ready(self):
        evidence = issue(200, "[agent-ready] Rebuild headless evidence", keys=[EVIDENCE])
        gate = closure()
        # Oldest-first would pick #200; the independently confirmed native
        # crash is more important, without allowing another Codex process.
        self.assertEqual(select_issue([evidence, self.crash],
                                      {"issues": {}}, 3, closure=gate)["number"], 438)
        # An already published or exhausted crash ticket cannot starve repairs.
        for record in ({"status": "pr_open", "attempts": 1},
                       {"status": "failed", "attempts": 3}):
            with self.subTest(record=record):
                chosen = select_issue([evidence, self.crash],
                                      {"issues": {"438": record}}, 3, closure=gate)
                self.assertEqual(chosen["number"], 200)

    def test_priority_never_allows_unrelated_optional_work(self):
        gate = closure()
        optional = issue(197, "[agent-ready] New optional gameplay content")
        self.assertFalse(gate.permits_issue(optional))
        self.assertEqual(select_issue([optional, self.crash],
                                      {"issues": {}}, 3, closure=gate)["number"], 438)


if __name__ == "__main__":
    unittest.main()
